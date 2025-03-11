from typing import Dict, List, Set, Optional
import json
from datetime import datetime
import logging
from pathlib import Path

class SiteMapper:
    """Manages the site structure and maintains crawl state."""
    
    def __init__(self):
        self.site_map = {}
        self.depth_map = {}
        self.concatenated_text = []
        self.logger = logging.getLogger(__name__)

    def add_page(self, url: str, links: List[str], depth: int, content: Dict) -> None:
        """
        Add a page to the site map with its links and content.
        
        Args:
            url: The URL of the page
            links: List of links found on the page
            depth: Crawl depth of the page
            content: Extracted content and metadata
        """
        self.site_map[url] = {
            'links': links,
            'depth': depth,
            'title': content.get('title', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        self.depth_map[url] = depth
        
        if content.get('content'):
            self.concatenated_text.append({
                'url': url,
                'title': content.get('title', ''),
                'content': content.get('content', ''),
                'code_blocks': content.get('code_blocks', [])
            })

    def get_page_depth(self, url: str) -> Optional[int]:
        """Get the crawl depth of a page."""
        return self.depth_map.get(url)

    def is_visited(self, url: str) -> bool:
        """Check if a URL has been visited."""
        return url in self.site_map

    def get_unvisited_links(self, links: List[str]) -> List[str]:
        """Filter out already visited links."""
        return [link for link in links if not self.is_visited(link)]

    def generate_output(self, start_urls: List[str]) -> Dict:
        """
        Generate the final output structure.
        
        Args:
            start_urls: List of starting URLs for the crawl
            
        Returns:
            Dict containing site map and concatenated text
        """
        try:
            # Ensure start_urls is a list
            if isinstance(start_urls, str):
                start_urls = [start_urls]
                
            # Prepare the full text content
            full_text = "\n\n".join(
                f"# {page['title']}\nURL: {page['url']}\n\n{page['content']}"
                for page in self.concatenated_text
            )

            output = {
                'metadata': {
                    'start_urls': start_urls,
                    'crawl_date': datetime.now().isoformat(),
                    'total_pages': len(self.site_map)
                },
                'site_map': self.site_map,
                'llmfulltext': full_text
            }

            return output

        except Exception as e:
            self.logger.error(f"Error generating output: {str(e)}")
            return {
                'metadata': {
                    'start_urls': start_urls,
                    'crawl_date': datetime.now().isoformat(),
                    'total_pages': 0,
                    'error': str(e)
                },
                'site_map': {},
                'llmfulltext': ''
            }

    def save_output(self, output: Dict, output_path: Path) -> None:
        """Save the crawler output to a JSON file."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Output saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving output to {output_path}: {str(e)}")
            raise