from urllib.parse import urljoin, urlparse
from collections import deque
from typing import Set, Optional

class URLManager:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.url_queue = deque([base_url])
        self.visited_urls: Set[str] = set()
        
    def is_internal_link(self, url: str) -> bool:
        """Check if URL belongs to the same domain."""
        try:
            return urlparse(url).netloc == self.base_domain
        except:
            return False
            
    def normalize_url(self, url: str) -> str:
        """Normalize URL to absolute form without fragments."""
        url = urljoin(self.base_url, url)
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
    def add_url(self, url: str) -> None:
        """Add URL to queue if it's internal and not visited."""
        normalized_url = self.normalize_url(url)
        if (self.is_internal_link(normalized_url) and 
            normalized_url not in self.visited_urls and 
            normalized_url not in self.url_queue):
            self.url_queue.append(normalized_url)
            
    def get_next_url(self) -> Optional[str]:
        """Get next URL from queue."""
        try:
            url = self.url_queue.popleft()
            self.visited_urls.add(url)
            return url
        except IndexError:
            return None
            
    def has_urls(self) -> bool:
        """Check if there are URLs left to process."""
        return len(self.url_queue) > 0
        
    def get_visited_count(self) -> int:
        """Get count of visited URLs."""
        return len(self.visited_urls)