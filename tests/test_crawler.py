import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from src.config import CrawlerConfig
from src.crawler import Crawler
from src.content_extractor import ContentExtractor
from src.url_handler import URLHandler
from src.site_mapper import SiteMapper
from unittest.mock import AsyncMock, MagicMock, ANY

@pytest.fixture
def config():
    return CrawlerConfig(
        max_depth=2,
        max_links=10,
        delay=0.1,
        timeout=5,
        output_path=Path('output/test_result.json'),
        exclusion_patterns=["*/ads/*"],
        respect_robots_txt=True
    )

@pytest.fixture
def url_handler():
    return URLHandler('https://example.com')

@pytest.fixture
def content_extractor():
    return ContentExtractor()

@pytest.fixture
def site_mapper():
    return SiteMapper()

def test_url_handler_normalize_url(url_handler):
    """Test URL normalization."""
    test_urls = [
        ('https://example.com/', 'https://example.com'),
        ('https://example.com/page#fragment', 'https://example.com/page'),
        ('https://example.com/page/', 'https://example.com/page'),
    ]
    
    for input_url, expected in test_urls:
        assert url_handler._normalize_url(input_url) == expected

def test_url_handler_internal_url(url_handler):
    """Test internal URL detection."""
    internal_urls = [
        'https://example.com/page',
        'https://example.com/blog',
        '/relative/path',
    ]
    
    external_urls = [
        'https://other-domain.com',
        'http://subdomain.other-domain.com',
        'https://example.org',
    ]
    
    for url in internal_urls:
        assert url_handler.is_internal_url(url) is True
        
    for url in external_urls:
        assert url_handler.is_internal_url(url) is False

def test_content_extractor_clean_text(content_extractor):
    """Test text cleaning functionality."""
    dirty_text = """
    This is some    text with
    
    extra whitespace
    
    and newlines.
    """
    
    clean_text = content_extractor._clean_text(dirty_text)
    expected = "This is some text with extra whitespace and newlines."
    
    assert clean_text == expected

def test_site_mapper_basic_functionality(site_mapper):
    """Test basic site mapper functionality."""
    url = 'https://example.com'
    links = ['https://example.com/page1', 'https://example.com/page2']
    depth = 0
    content = {
        'title': 'Test Page',
        'content': 'Test content',
        'code_blocks': []
    }
    
    site_mapper.add_page(url, links, depth, content)
    
    assert site_mapper.is_visited(url) is True
    assert site_mapper.get_page_depth(url) == 0
    assert len(site_mapper.site_map) == 1

@pytest.mark.asyncio
async def test_crawler_initialization(config):
    """Test crawler initialization."""
    crawler = Crawler(config)
    assert crawler.config == config
    assert crawler.total_links == 0
    assert len(crawler.visited_urls) == 0

def test_config_validation():
    """Test configuration validation."""
    # Test valid config
    valid_config = CrawlerConfig(
        max_depth=3,
        max_links=100,
        delay=1.0,
        timeout=30,
        output_path=Path('output/result.json'),
        exclusion_patterns=[]
    )
    assert valid_config.max_depth > 0
    assert valid_config.max_links > 0
    assert valid_config.delay >= 0
    assert valid_config.timeout > 0

def test_content_extractor_code_preservation(content_extractor):
    """Test code block preservation."""
    html = """
    <html>
        <body>
            <p>Regular text</p>
            <pre><code>def example():
    return True</code></pre>
            <p>More text</p>
        </body>
    </html>
    """
    
    result = content_extractor.extract_content(html, 'https://example.com')
    assert 'def example():' in result['content']
    assert len(result['code_blocks']) > 0

def test_url_handler_exclusion_patterns(url_handler):
    """Test URL exclusion patterns."""
    excluded_urls = [
        'https://example.com/ads/banner.jpg',
        'https://example.com/page.jpg',
        'https://example.com/script.js',
        'https://example.com/style.css',
        'mailto:test@example.com',
    ]
    
    for url in excluded_urls:
        assert url_handler.is_valid_url(url) is False

@pytest.mark.asyncio
async def test_multiple_urls_crawling():
    """Test that the crawler can handle multiple starting URLs."""
    # Create a mock config
    config = CrawlerConfig(
        max_depth=1,
        max_links=10,
        delay=0.01,
        timeout=1,
        output_path=Path("test_output.json"),
        exclusion_patterns=[]
    )
    
    # Create a crawler with the mock config
    crawler = Crawler(config)
    
    # Mock the _crawl_url method to avoid actual network requests
    crawler._crawl_url = AsyncMock()
    
    # Mock the site_mapper.generate_output method
    crawler.site_mapper.generate_output = MagicMock(return_value={"test": "data"})
    
    # Test URLs
    urls = ["https://example.com", "https://example.org"]
    
    # Call the crawl method with multiple URLs
    result = await crawler.crawl(urls)
    
    # Verify that _crawl_url was called for each URL with the correct parameters
    assert crawler._crawl_url.call_count == 2
    # Check that each call included the URL as both the URL to crawl and the origin URL
    for url in urls:
        crawler._crawl_url.assert_any_call(ANY, url, 0, url)
    
    # Verify that generate_output was called with the list of URLs
    crawler.site_mapper.generate_output.assert_called_once_with(urls)
    
    # Verify the result
    assert result == {"test": "data"}

def test_read_urls_from_file():
    """Test reading URLs from a file."""
    # Create a temporary file with URLs
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        temp_file.write("https://example.com\n")
        temp_file.write("# This is a comment\n")
        temp_file.write("\n")  # Empty line
        temp_file.write("https://example.org\n")
        temp_file.write("https://example.net\n")
        temp_file_path = temp_file.name
    
    try:
        # Read URLs from the file
        with open(temp_file_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        # Verify the URLs were read correctly
        assert len(urls) == 3
        assert urls[0] == "https://example.com"
        assert urls[1] == "https://example.org"
        assert urls[2] == "https://example.net"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

if __name__ == '__main__':
    pytest.main([__file__])