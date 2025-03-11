from urllib.parse import urljoin, urlparse
from typing import List, Set, Optional
import re
import logging
from pathlib import Path
import requests
from urllib.robotparser import RobotFileParser

class URLHandler:
    """Handles URL processing, validation, and robots.txt compliance."""
    
    def __init__(self, base_url: str, respect_robots: bool = True, exclude_keywords: List[str] = None):
        self.base_url = self._normalize_url(base_url)
        self.base_domain = urlparse(self.base_url).netloc
        self.base_path_prefix = urlparse(self.base_url).path
        self.respect_robots = respect_robots
        self.robot_parser = RobotFileParser()
        self.logger = logging.getLogger(__name__)
        self.same_path_only = False
        self.exclude_keywords = exclude_keywords or []
        
        if self.respect_robots:
            self._setup_robots_txt()

    def _setup_robots_txt(self):
        """Initialize robots.txt parser."""
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            self.robot_parser.set_url(robots_url)
            self.robot_parser.read()
        except Exception as e:
            self.logger.warning(f"Could not fetch robots.txt: {str(e)}")

    def _normalize_url(self, url: str) -> str:
        """Normalize URL format."""
        # Remove fragments
        url = re.sub(r'#.*$', '', url)
        # Remove trailing slash
        url = re.sub(r'/$', '', url)
        return url

    def is_internal_url(self, url: str) -> bool:
        """Check if URL belongs to the same domain."""
        try:
            parsed_url = urlparse(url)
            is_same_domain = parsed_url.netloc == self.base_domain or not parsed_url.netloc
            
            # If same_path_only is enabled, also check the path prefix
            if self.same_path_only:
                return is_same_domain and self.has_same_path_prefix(url)
            
            return is_same_domain
        except Exception:
            return False

    def has_same_path_prefix(self, url: str) -> bool:
        """Check if URL has the same path prefix as the base URL."""
        try:
            parsed_url = urlparse(url)
            url_path = parsed_url.path
            
            # If base path is empty or just '/', any path is valid
            if not self.base_path_prefix or self.base_path_prefix == '/':
                return True
                
            # Check if the URL path starts with the base path prefix
            return url_path.startswith(self.base_path_prefix)
        except Exception as e:
            self.logger.debug(f"Error checking path prefix for {url}: {str(e)}")
            return False

    def can_fetch(self, url: str, user_agent: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if not self.respect_robots:
            return True
        try:
            return self.robot_parser.can_fetch(user_agent, url)
        except Exception:
            return True

    def extract_links(self, html: str, current_url: str) -> List[str]:
        """Extract and normalize all links from HTML content."""
        from bs4 import BeautifulSoup
        
        links = set()
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for anchor in soup.find_all('a', href=True):
                href = anchor['href']
                absolute_url = urljoin(current_url, href)
                normalized_url = self._normalize_url(absolute_url)
                
                if self.is_valid_url(normalized_url):
                    links.add(normalized_url)
                    
        except Exception as e:
            self.logger.error(f"Error extracting links from {current_url}: {str(e)}")
            
        return list(links)

    def is_valid_url(self, url: str) -> bool:
        """Validate URL format and check against exclusion patterns."""
        try:
            parsed = urlparse(url)
            return all([
                parsed.scheme in ('http', 'https'),
                parsed.netloc,
                not self._is_excluded_url(url)
            ])
        except Exception:
            return False

    def _is_excluded_url(self, url: str) -> bool:
        """Check if URL matches common exclusion patterns or contains exclude keywords."""
        excluded_patterns = [
            r'\.(jpg|jpeg|png|gif|ico|css|js|xml|json)$',
            r'(mailto:|tel:)',
            r'(login|logout|signin|signout|admin)',
            r'(\?|&)utm_',
        ]
        
        # Check standard exclusion patterns
        if any(re.search(pattern, url, re.IGNORECASE) for pattern in excluded_patterns):
            return True
            
        # Check for exclude keywords in the URL path
        if self.exclude_keywords:
            parsed_url = urlparse(url)
            path = parsed_url.path.lower()
            
            # Check if any exclude keyword is in the path
            for keyword in self.exclude_keywords:
                if keyword.lower() in path:
                    self.logger.debug(f"Excluding URL due to keyword match: {url}")
                    return True
                
        return False

    def normalize_links(self, links: List[str], base_url: str) -> List[str]:
        """Normalize a list of URLs relative to a base URL."""
        normalized = set()
        for link in links:
            try:
                absolute_url = urljoin(base_url, link)
                normalized_url = self._normalize_url(absolute_url)
                if self.is_valid_url(normalized_url):
                    normalized.add(normalized_url)
            except Exception as e:
                self.logger.debug(f"Error normalizing URL {link}: {str(e)}")
                
        return list(normalized)