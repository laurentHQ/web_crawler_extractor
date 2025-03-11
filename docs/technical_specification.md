# Web Crawler Extractor - Technical Specification

## Architecture Overview

### Core Components
1. **URLManager**
   - Handles URL normalization
   - Maintains URL queue
   - Tracks visited URLs
   - Validates internal links

2. **Crawler**
   - Manages crawling process
   - Implements depth control
   - Handles rate limiting
   - Respects robots.txt

3. **ContentExtractor**
   - Removes unwanted elements
   - Preserves code blocks
   - Cleans text content
   - Maintains document structure

4. **SiteMapper**
   - Builds site hierarchy
   - Tracks relationships
   - Generates site map

5. **OutputManager**
   - Creates JSON output
   - Handles file operations
   - Manages content aggregation

## Technical Implementation

### Dependencies
- `requests`: HTTP requests
- `beautifulsoup4`: HTML parsing
- `urllib`: URL handling
- `json`: Output formatting
- `logging`: Error tracking
- `robotexclusionrulesparser`: robots.txt parsing

### Class Specifications

```python
class URLManager:
    def __init__(self, base_url: str)
    def is_internal_link(self, url: str) -> bool
    def normalize_url(self, url: str) -> str
    def add_url(self, url: str) -> None
    def get_next_url(self) -> str

class Crawler:
    def __init__(self, config: Dict)
    def crawl(self, url: str) -> None
    def respect_robots_txt(self, domain: str) -> None
    def handle_rate_limiting(self) -> None

class ContentExtractor:
    def __init__(self)
    def extract_content(self, html: str) -> Dict
    def clean_text(self, text: str) -> str
    def preserve_code_blocks(self, html: str) -> str
    def remove_unwanted_elements(self, soup: BeautifulSoup) -> None

class SiteMapper:
    def __init__(self)
    def add_page(self, url: str, links: List[str]) -> None
    def generate_sitemap(self) -> Dict
    def export_json(self) -> str

class OutputManager:
    def __init__(self, output_file: str)
    def add_content(self, url: str, content: Dict) -> None
    def save_output(self) -> None
```

## Data Structures

### Configuration Object
```python
config = {
    'start_url': str,
    'max_depth': int,
    'max_links': int,
    'rate_limit': float,
    'output_file': str
}
```

### Output JSON Structure
```json
{
    "sitemap": {
        "urls": [...],
        "hierarchy": {...}
    },
    "llmfulltext": "concatenated text content",
    "metadata": {
        "crawl_date": "",
        "total_pages": 0,
        "depth_reached": 0
    }
}
```

## Error Handling
1. Network errors
2. Parser errors
3. Rate limiting
4. Memory management
5. File operations

## Performance Considerations
1. Async crawling for efficiency
2. Memory-efficient text processing
3. Incremental JSON writing
4. URL deduplication
5. Proper cleanup of resources