import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import aiohttp
from datetime import datetime, timedelta

from src.config import CrawlerConfig
from src.crawler import Crawler, CircuitBreaker

@pytest.fixture
def config():
    """Create a test configuration."""
    return CrawlerConfig(
        max_depth=2,
        max_links=10,
        delay=0.01,  # Small delay for faster tests
        timeout=1,
        output_path=Path("test_output.json"),
        exclusion_patterns=["*/ads/*"],
        max_retries=2,
        retry_delay=0.01,  # Small delay for faster tests
        circuit_breaker_threshold=2,
        circuit_breaker_timeout=1
    )

class TestCircuitBreaker:
    """Test the CircuitBreaker class."""
    
    def test_record_failure(self):
        """Test recording failures and opening the circuit."""
        cb = CircuitBreaker(threshold=2, timeout=60)
        
        # First failure shouldn't open the circuit
        cb.record_failure("example.com")
        assert not cb.is_open("example.com")
        assert cb.failures["example.com"] == 1
        
        # Second failure should open the circuit
        cb.record_failure("example.com")
        assert cb.is_open("example.com")
        assert cb.failures["example.com"] == 2
        
        # Different domain should be unaffected
        assert not cb.is_open("other.com")
    
    def test_record_success(self):
        """Test recording success resets failure count."""
        cb = CircuitBreaker(threshold=2, timeout=60)
        
        # Record a failure
        cb.record_failure("example.com")
        assert cb.failures["example.com"] == 1
        
        # Record a success
        cb.record_success("example.com")
        assert cb.failures["example.com"] == 0
    
    def test_circuit_timeout(self):
        """Test circuit closes after timeout."""
        cb = CircuitBreaker(threshold=1, timeout=1)
        
        # Open the circuit
        cb.record_failure("example.com")
        assert cb.is_open("example.com")
        
        # Set the timeout to have expired
        cb.open_circuits["example.com"] = datetime.now() - timedelta(seconds=2)
        
        # Circuit should be closed now
        assert not cb.is_open("example.com")
        assert "example.com" not in cb.open_circuits
        assert cb.failures["example.com"] == 0

@pytest.mark.asyncio
class TestCrawlerErrorHandling:
    """Test the crawler's error handling capabilities."""
    
    async def test_retry_mechanism(self, config):
        """Test that the crawler retries failed requests."""
        crawler = Crawler(config)
        # Initialize URL handlers
        test_url = "https://example.com"
        url_handler = MagicMock()
        url_handler.is_valid_url.return_value = True
        url_handler.can_fetch.return_value = True
        url_handler.is_internal_url.return_value = True
        url_handler.extract_links.return_value = []
        crawler.url_handlers = {test_url: url_handler}
        
        # Mock session with a side effect that fails twice then succeeds
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html><body>Test</body></html>")
        mock_response.headers = {'Content-Type': 'text/html'}
        
        mock_session = MagicMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.side_effect = [
            aiohttp.ClientError("Test error"),  # First attempt fails
            aiohttp.ClientError("Test error"),  # Second attempt fails
            mock_response  # Third attempt succeeds
        ]
        mock_session.get.return_value = mock_context_manager
        
        # Call the method
        await crawler._crawl_url(mock_session, test_url, 0, test_url)
        
        # Verify the crawler made 3 attempts (initial + 2 retries)
        assert mock_session.get.call_count == 3
        assert test_url not in crawler.failed_urls
        assert test_url in crawler.visited_urls
    
    async def test_circuit_breaker(self, config):
        """Test that the circuit breaker prevents requests to failing domains."""
        crawler = Crawler(config)
        
        # Initialize URL handlers
        url1 = "https://example.com/page1"
        url2 = "https://example.com/page2"
        url_handler = MagicMock()
        url_handler.is_valid_url.return_value = True
        url_handler.can_fetch.return_value = True
        url_handler.is_internal_url.return_value = True
        url_handler.extract_links.return_value = []
        crawler.url_handlers = {url1: url_handler, url2: url_handler}
        
        # Mock session that always fails with server error
        mock_error_response = AsyncMock()
        mock_error_response.status = 500
        mock_error_response.headers = {'Content-Type': 'text/html'}
        
        mock_session = MagicMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_error_response
        mock_session.get.return_value = mock_context_manager
        
        # First URL should be attempted and fail after retries
        await crawler._crawl_url(mock_session, url1, 0, url1)
        
        # Circuit breaker should be open now
        assert crawler.circuit_breaker.is_open("example.com")
        
        # Reset the mock to verify second URL is skipped
        mock_session.get.reset_mock()
        
        # Second URL should be skipped without attempts due to open circuit breaker
        await crawler._crawl_url(mock_session, url2, 0, url2)
        
        # Verify the second URL was skipped
        assert mock_session.get.call_count == 0  # No attempts for the second URL
        assert url1 in crawler.failed_urls
        assert url2 not in crawler.failed_urls  # Not even marked as failed, just skipped
    
    async def test_error_categorization(self, config):
        """Test that the crawler correctly categorizes different types of errors."""
        crawler = Crawler(config)
        
        # Initialize URL handlers
        url1 = "https://example.com/not-found"  # Will return 404
        url2 = "https://example.com/server-error"  # Will return 500
        
        url_handler = MagicMock()
        url_handler.is_valid_url.return_value = True
        url_handler.can_fetch.return_value = True
        url_handler.is_internal_url.return_value = True
        url_handler.extract_links.return_value = []
        
        crawler.url_handlers = {url1: url_handler, url2: url_handler}
        
        # Mock responses
        mock_404_response = AsyncMock()
        mock_404_response.status = 404
        mock_404_response.headers = {'Content-Type': 'text/html'}
        
        mock_500_response = AsyncMock()
        mock_500_response.status = 500
        mock_500_response.headers = {'Content-Type': 'text/html'}
        
        # Configure the mock session's get method
        def mock_get(url, **kwargs):
            mock_context = AsyncMock()
            if url == url1:
                mock_context.__aenter__.return_value = mock_404_response
            elif url == url2:
                mock_context.__aenter__.return_value = mock_500_response
            return mock_context
        
        mock_session = MagicMock()
        mock_session.get.side_effect = mock_get
        
        # Process each URL
        await crawler._crawl_url(mock_session, url1, 0, url1)
        await crawler._crawl_url(mock_session, url2, 0, url2)
        
        # Verify error categorization
        assert crawler.error_counts["HTTP 404"] == 1
        assert crawler.error_counts["HTTP 500"] > 0  # Could be multiple due to retries
        
        # Verify URLs are marked as failed
        assert url1 in crawler.failed_urls
        assert url2 in crawler.failed_urls 