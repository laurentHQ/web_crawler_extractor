# Web Crawler Extractor - Technical Design Document

## Architecture Overview

### Component Structure
1. **CrawlerManager**
   - Manages the crawling process
   - Handles URL queue
   - Enforces crawl limits
   - Coordinates between components

2. **ContentExtractor**
   - Processes HTML content
   - Removes unwanted elements
   - Preserves code formatting
   - Extracts clean text

3. **SiteMapper**
   - Builds site structure
   - Manages internal/external link classification
   - Maintains crawl depth tracking

4. **OutputFormatter**
   - Generates JSON output
   - Manages content aggregation
   - Handles file operations

### Class Diagram
```
+----------------+     +------------------+     +---------------+
| CrawlerManager |<--->| ContentExtractor |<--->| OutputManager |
+----------------+     +------------------+     +---------------+
        ^                      ^
        |                      |
        v                      v
   +----------+          +------------+
   | SiteMap  |<-------->| URLHandler |
   +----------+          +------------+
```

## Component Specifications

### 1. CrawlerManager
```python
class CrawlerManager:
    def __init__(self, start_url: str, config: CrawlerConfig):
        self.start_url = start_url
        self.config = config
        self.url_queue = Queue()
        self.visited = set()

    async def crawl(self) -> Dict:
        # Main crawling logic
        pass
```

### 2. ContentExtractor
```python
class ContentExtractor:
    def __init__(self):
        self.parser = "html.parser"
        self.excluded_tags = {"header", "footer", "nav", "aside"}

    def extract_content(self, html: str) -> Dict:
        # Content extraction logic
        pass

    def preserve_code_blocks(self, soup: BeautifulSoup) -> None:
        # Code preservation logic
        pass
```

### 3. SiteMapper
```python
class SiteMapper:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.site_map = {}
        self.depth_map = {}

    def add_page(self, url: str, links: List[str], depth: int):
        # Site map building logic
        pass
```

### 4. OutputFormatter
```python
class OutputFormatter:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.content_buffer = []

    def format_output(self, site_map: Dict, content: List) -> Dict:
        # Output formatting logic
        pass
```

## Data Structures

### Configuration Object
```python
@dataclass
class CrawlerConfig:
    max_depth: int
    max_links: int
    delay: float
    timeout: int
    output_path: str
    exclusion_patterns: List[str]
```

### Output JSON Structure
```json
{
    "metadata": {
        "start_url": "string",
        "crawl_date": "string",
        "total_pages": "integer"
    },
    "site_map": {
        "url": {
            "links": ["string"],
            "depth": "integer"
        }
    },
    "llmfulltext": "string"
}
```

## Implementation Guidelines

### 1. Error Handling
- Implement comprehensive try-except blocks
- Log all errors with context
- Provide meaningful error messages
- Handle network timeouts gracefully

### 2. Performance Optimization
- Use connection pooling
- Implement async/await for I/O operations
- Buffer content in memory efficiently
- Use generators for large data sets

### 3. Testing Strategy
- Unit tests for each component
- Integration tests for full workflow
- Mock external requests
- Test edge cases and error conditions

### 4. Code Quality
- Type hints throughout
- Docstrings for all classes and methods
- Follow PEP 8 style guide
- Modular and maintainable design