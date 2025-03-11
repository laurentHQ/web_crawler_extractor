import asyncio
import aiohttp
import logging
from typing import List, Dict, Set, DefaultDict
from pathlib import Path
import time
from urllib.parse import urlparse
import sys
import random
from collections import defaultdict
from datetime import datetime, timedelta

from .config import CrawlerConfig
from .content_extractor import ContentExtractor
from .url_handler import URLHandler
from .site_mapper import SiteMapper

class CircuitBreaker:
    """Circuit breaker implementation to prevent overwhelming servers with errors."""
    
    def __init__(self, threshold: int, timeout: int):
        self.threshold = threshold
        self.timeout = timeout
        self.failures: DefaultDict[str, int] = defaultdict(int)
        self.open_circuits: Dict[str, datetime] = {}
        self.logger = logging.getLogger(__name__)
    
    def record_failure(self, domain: str) -> None:
        """Record a failure for a domain and open circuit if threshold is reached."""
        self.failures[domain] += 1
        if self.failures[domain] >= self.threshold and domain not in self.open_circuits:
            self.logger.warning(f"Circuit breaker opened for domain: {domain}")
            self.open_circuits[domain] = datetime.now() + timedelta(seconds=self.timeout)
    
    def record_success(self, domain: str) -> None:
        """Record a success for a domain and reset failure count."""
        if domain in self.failures:
            self.failures[domain] = 0
    
    def is_open(self, domain: str) -> bool:
        """Check if circuit is open for a domain."""
        if domain in self.open_circuits:
            if datetime.now() > self.open_circuits[domain]:
                # Circuit timeout has expired, close the circuit
                self.logger.info(f"Circuit breaker closed for domain: {domain}")
                del self.open_circuits[domain]
                self.failures[domain] = 0
                return False
            return True
        return False

class Crawler:
    """Main crawler class that orchestrates the web crawling process."""
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.extractor = ContentExtractor()
        self.site_mapper = SiteMapper()
        self.logger = logging.getLogger(__name__)
        
        # Dictionary to store URL handlers for each starting URL
        self.url_handlers = {}
        
        # Crawling state
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.current_depth = 0
        self.total_links = 0
        self.links_lock = asyncio.Lock()  # Lock for synchronizing access to total_links
        
        # Create a semaphore to limit the number of URLs crawled
        # We use a higher value for the semaphore to allow parallel crawling
        # but we'll still stop when total_links reaches max_links
        self.links_semaphore = asyncio.Semaphore(min(100, self.config.max_links * 2))
        self.stop_crawling = False  # Flag to signal when to stop crawling
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            self.config.circuit_breaker_threshold,
            self.config.circuit_breaker_timeout
        )
        
        # Error tracking
        self.error_counts: DefaultDict[str, int] = defaultdict(int)

    async def crawl(self, start_urls: List[str]) -> Dict:
        """
        Start the crawling process from the given URLs.
        
        Args:
            start_urls: List of URLs to start crawling from
            
        Returns:
            Dict containing the crawl results
        """
        # Ensure start_urls is a list
        if isinstance(start_urls, str):
            start_urls = [start_urls]
            
        # Initialize URL handlers for each starting URL
        for url in start_urls:
            url_handler = URLHandler(url, self.config.respect_robots_txt, self.config.exclude_keywords)
            url_handler.same_path_only = self.config.same_path_only
            self.url_handlers[url] = url_handler
        
        # Configure client session with proper headers and timeouts
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        headers = {"User-Agent": self.config.user_agent}
        
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            # Create tasks for each starting URL
            tasks = []
            for url in start_urls:
                tasks.append(self._crawl_url(session, url, 0, url))  # Pass the starting URL as the origin
                
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
            
        # Log error statistics
        if self.error_counts:
            self.logger.info("Error statistics:")
            for error_type, count in self.error_counts.items():
                self.logger.info(f"  {error_type}: {count}")
            
        return self.site_mapper.generate_output(start_urls)

    async def _crawl_url(self, session: aiohttp.ClientSession, url: str, depth: int, origin_url: str) -> None:
        """
        Crawl a single URL and its links up to the specified depth.
        
        Args:
            session: The aiohttp client session
            url: The URL to crawl
            depth: The current crawl depth
            origin_url: The starting URL that initiated this crawl path
        """
        # Check if we should stop crawling
        if self.stop_crawling:
            return
            
        # Try to acquire a semaphore permit
        # If we can't acquire it, it means we've reached the max_links limit
        if not self.links_semaphore.locked():
            try:
                # Use a non-blocking acquire to check if we can get a permit
                if not await asyncio.wait_for(self.links_semaphore.acquire(), 0.1):
                    return
            except asyncio.TimeoutError:
                # If we time out waiting for the semaphore, it means we've reached the limit
                return
        else:
            # Semaphore is already locked, which means we've reached the limit
            return
            
        try:
            # Check if URL should be crawled (this includes checking for excluded URLs)
            url_handler = self.url_handlers[origin_url]
            
            # First check if the URL is excluded by keywords or patterns
            # This way we don't count excluded URLs toward the max-links limit
            parsed_url = urlparse(url)
            path = parsed_url.path.lower()
            
            # Check if URL is excluded by keywords
            if url_handler._is_excluded_url(url):
                # Release the semaphore since we're not actually crawling this URL
                self.links_semaphore.release()
                return
                
            if not self._should_crawl(url, depth, origin_url):
                # Release the semaphore if we decide not to crawl this URL
                self.links_semaphore.release()
                return

            # Check if circuit breaker is open for this domain
            domain = urlparse(url).netloc
            if self.circuit_breaker.is_open(domain):
                self.logger.info(f"Skipping {url}: Circuit breaker is open for domain {domain}")
                # Release the semaphore if we decide not to crawl this URL
                self.links_semaphore.release()
                return

            # Initialize retry counter
            retry_count = 0
            
            while retry_count <= self.config.max_retries:
                try:
                    # Respect crawl delay
                    await asyncio.sleep(self.config.delay)
                    
                    # Fetch and process the page
                    try:
                        async with session.get(url) as response:
                            status = response.status
                            
                            # Handle different HTTP status codes
                            if status == 200:
                                # Check content type before processing
                                content_type = response.headers.get('Content-Type', '').lower()
                                if not ('text/html' in content_type or 'application/xhtml+xml' in content_type):
                                    self.logger.info(f"Skipping non-HTML content: {url} (Content-Type: {content_type})")
                                    self.visited_urls.add(url)  # Mark as visited to avoid retrying
                                    break
                                    
                                try:
                                    html = await response.text()
                                except UnicodeDecodeError as e:
                                    self.logger.warning(f"Failed to decode content from {url}: {str(e)}")
                                    self.visited_urls.add(url)  # Mark as visited to avoid retrying
                                    break
                                
                                # Record success for circuit breaker
                                self.circuit_breaker.record_success(domain)
                                
                                # Extract content
                                content = self.extractor.extract_content(html, url)
                                
                                # Extract links using the appropriate URL handler
                                url_handler = self.url_handlers[origin_url]
                                links = url_handler.extract_links(html, url)
                                internal_links = [link for link in links if url_handler.is_internal_url(link)]
                                
                                # Update site map
                                self.site_mapper.add_page(url, internal_links, depth, content)
                                self.visited_urls.add(url)
                                
                                # Increment total_links with lock - only count successfully crawled pages
                                async with self.links_lock:
                                    self.total_links += 1
                                    # Check if we've reached the max_links limit
                                    if self.total_links >= self.config.max_links:
                                        self.logger.info(f"Reached maximum number of links ({self.config.max_links}), stopping crawl")
                                        self.stop_crawling = True
                                
                                # Crawl links if within limits and not stopping
                                if depth < self.config.max_depth and not self.stop_crawling:
                                    tasks = []
                                    for link in internal_links:
                                        if self._should_crawl(link, depth + 1, origin_url):
                                            tasks.append(self._crawl_url(session, link, depth + 1, origin_url))
                                            
                                    if tasks:
                                        await asyncio.gather(*tasks)
                                
                                # Successfully processed, break the retry loop
                                break
                                
                            elif 500 <= status < 600:
                                # Server error, retry with backoff
                                error_type = f"HTTP {status}"
                                self.error_counts[error_type] += 1
                                self.logger.warning(f"Server error for {url}: Status {status}, attempt {retry_count + 1}/{self.config.max_retries + 1}")
                                
                                # Record failure for circuit breaker
                                self.circuit_breaker.record_failure(domain)
                                
                                # If we've reached max retries, mark as failed
                                if retry_count == self.config.max_retries:
                                    self.logger.error(f"Failed to fetch {url} after {self.config.max_retries + 1} attempts: Status {status}")
                                    self.failed_urls.add(url)
                                    break
                                    
                                # Exponential backoff with jitter
                                backoff_time = self.config.retry_delay * (2 ** retry_count) + random.uniform(0, 1)
                                self.logger.debug(f"Retrying {url} in {backoff_time:.2f} seconds")
                                await asyncio.sleep(backoff_time)
                                retry_count += 1
                                continue
                                
                            elif 400 <= status < 500:
                                # Client error, don't retry
                                error_type = f"HTTP {status}"
                                self.error_counts[error_type] += 1
                                self.logger.warning(f"Client error for {url}: Status {status}")
                                self.failed_urls.add(url)
                                break
                                
                            else:
                                # Other status codes, don't retry
                                error_type = f"HTTP {status}"
                                self.error_counts[error_type] += 1
                                self.logger.warning(f"Unexpected status for {url}: Status {status}")
                                self.failed_urls.add(url)
                                break
                    
                    except asyncio.TimeoutError:
                        error_type = "Timeout"
                        self.error_counts[error_type] += 1
                        self.logger.warning(f"Timeout for {url}, attempt {retry_count + 1}/{self.config.max_retries + 1}")
                        
                        # Record failure for circuit breaker
                        self.circuit_breaker.record_failure(domain)
                        
                        # If we've reached max retries, mark as failed
                        if retry_count == self.config.max_retries:
                            self.logger.error(f"Failed to fetch {url} after {self.config.max_retries + 1} attempts: Timeout")
                            self.failed_urls.add(url)
                            break
                            
                        # Exponential backoff with jitter
                        backoff_time = self.config.retry_delay * (2 ** retry_count) + random.uniform(0, 1)
                        self.logger.debug(f"Retrying {url} in {backoff_time:.2f} seconds")
                        await asyncio.sleep(backoff_time)
                        retry_count += 1
                        continue
                        
                except asyncio.TimeoutError:
                    error_type = "Timeout"
                    self.error_counts[error_type] += 1
                    self.logger.warning(f"Timeout for {url}, attempt {retry_count + 1}/{self.config.max_retries + 1}")
                    
                    # Record failure for circuit breaker
                    self.circuit_breaker.record_failure(domain)
                    
                    # If we've reached max retries, mark as failed
                    if retry_count == self.config.max_retries:
                        self.logger.error(f"Failed to fetch {url} after {self.config.max_retries + 1} attempts: Timeout")
                        self.failed_urls.add(url)
                        break
                        
                    # Exponential backoff with jitter
                    backoff_time = self.config.retry_delay * (2 ** retry_count) + random.uniform(0, 1)
                    self.logger.debug(f"Retrying {url} in {backoff_time:.2f} seconds")
                    await asyncio.sleep(backoff_time)
                    retry_count += 1
                    
                except aiohttp.ClientError as e:
                    error_type = type(e).__name__
                    self.error_counts[error_type] += 1
                    self.logger.warning(f"Client error for {url}: {error_type}: {str(e)}, attempt {retry_count + 1}/{self.config.max_retries + 1}")
                    
                    # Record failure for circuit breaker
                    self.circuit_breaker.record_failure(domain)
                    
                    # If we've reached max retries, mark as failed
                    if retry_count == self.config.max_retries:
                        self.logger.error(f"Failed to fetch {url} after {self.config.max_retries + 1} attempts: {error_type}: {str(e)}")
                        self.failed_urls.add(url)
                        break
                        
                    # Exponential backoff with jitter
                    backoff_time = self.config.retry_delay * (2 ** retry_count) + random.uniform(0, 1)
                    self.logger.debug(f"Retrying {url} in {backoff_time:.2f} seconds")
                    await asyncio.sleep(backoff_time)
                    retry_count += 1
                    
                except Exception as e:
                    # Special case for test scenarios where session.get() raises a TimeoutError directly
                    if isinstance(e, asyncio.TimeoutError):
                        error_type = "Timeout"
                        self.error_counts[error_type] += 1
                        self.logger.warning(f"Timeout for {url}, attempt {retry_count + 1}/{self.config.max_retries + 1}")
                        
                        # Record failure for circuit breaker
                        self.circuit_breaker.record_failure(domain)
                        
                        # If we've reached max retries, mark as failed
                        if retry_count == self.config.max_retries:
                            self.logger.error(f"Failed to fetch {url} after {self.config.max_retries + 1} attempts: Timeout")
                            self.failed_urls.add(url)
                            break
                            
                        # Exponential backoff with jitter
                        backoff_time = self.config.retry_delay * (2 ** retry_count) + random.uniform(0, 1)
                        self.logger.debug(f"Retrying {url} in {backoff_time:.2f} seconds")
                        await asyncio.sleep(backoff_time)
                        retry_count += 1
                    else:
                        error_type = type(e).__name__
                        self.error_counts[error_type] += 1
                        self.logger.error(f"Error crawling {url}: {error_type}: {str(e)}", exc_info=True)
                        self.failed_urls.add(url)
                        break
        finally:
            # Always release the semaphore when we're done with this URL
            # Note: For error URLs, we release the semaphore without incrementing total_links
            # This ensures that error URLs don't count toward the max_links limit
            self.links_semaphore.release()

    def _should_crawl(self, url: str, depth: int, origin_url: str) -> bool:
        """
        Determine if a URL should be crawled based on various criteria.
        
        Args:
            url: The URL to check
            depth: The current crawl depth
            origin_url: The starting URL that initiated this crawl path
        """
        # Check if we should stop crawling
        if self.stop_crawling:
            return False
            
        # Get the appropriate URL handler for this origin
        url_handler = self.url_handlers[origin_url]
        
        # Get domain for circuit breaker check
        domain = urlparse(url).netloc
        
        # Check file extension to avoid non-HTML files
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        non_html_extensions = [
            '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
            '.zip', '.rar', '.tar', '.gz', '.jpg', '.jpeg', '.png', '.gif',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.csv', '.xml'
        ]
        if any(path.endswith(ext) for ext in non_html_extensions):
            self.logger.debug(f"Skipping non-HTML file: {url}")
            return False
        
        # Note: We don't check for excluded URLs here as that's done separately
        # before this method is called, to avoid counting them toward max_links
        return all([
            url not in self.visited_urls,
            url not in self.failed_urls,
            depth <= self.config.max_depth,
            url_handler.is_valid_url(url),
            url_handler.can_fetch(url, self.config.user_agent),
            not self.circuit_breaker.is_open(domain)
        ])

    def save_results(self, results: Dict) -> None:
        """Save the crawl results to a file."""
        try:
            self.site_mapper.save_output(results, self.config.output_path)
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}", exc_info=True)
            raise