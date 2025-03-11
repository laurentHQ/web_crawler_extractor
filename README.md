# Web Crawler Extractor

A powerful text-based web crawler that extracts clean content from websites while maintaining site structure and code formatting.

## Features

- Configurable crawl depth and link limits
- Focuses on internal links only
- Removes headers, footers, advertisements, and other boilerplate content
- Preserves code formatting
- Generates structured JSON output with site map and concatenated text
- Respects robots.txt
- Asynchronous crawling for better performance
- Robust error handling with retry mechanism and exponential backoff
- Circuit breaker pattern to prevent overwhelming servers with errors
- Detailed error categorization and logging
- Intelligent filtering of non-HTML content (PDFs, images, documents, etc.)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/web_crawler_extractor.git
cd web_crawler_extractor
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

Basic usage:
```bash
python -m src.main --urls https://example.com
```

Crawl multiple websites:
```bash
python -m src.main --urls https://example.com https://another-example.com
```

Crawl websites from a file:
```bash
python -m src.main --url-file urls.txt
```

The URL file should contain one URL per line. Empty lines and lines starting with # are ignored:
```
https://example.com
https://example.org

# This is a comment
https://example.net
```

You can also specify exclude keywords in the URL file by adding a section with the `[exclude_keywords]` header:
```
https://example.com
https://example.org

[exclude_keywords]
download
archive
legacy
```

URLs containing any of these keywords in their path will be skipped during crawling.

Advanced options:
```bash
python -m src.main --urls https://example.com \
    --depth 5 \
    --max-links 200 \
    --delay 2.0 \
    --timeout 30 \
    --output custom_output.json \
    --ignore-robots \
    --debug
```

### Command Line Arguments

- `--urls`: One or more URLs to crawl
- `--url-file`: Path to a text file containing URLs to crawl (one URL per line)
- `--exclude-keywords`: Keywords to exclude from URLs (URLs containing these keywords will be skipped)
- `--depth`: Maximum crawl depth (default: 3)
- `--max-links`: Maximum number of links to crawl (default: 100)
- `--delay`: Delay between requests in seconds (default: 1.0)
- `--timeout`: Request timeout in seconds (default: 30)
- `--output`: Output file path (default: output/crawl_result.json)
- `--ignore-robots`: Ignore robots.txt restrictions
- `--debug`: Enable debug logging
- `--max-retries`: Maximum number of retry attempts for failed requests (default: 3)
- `--retry-delay`: Base delay in seconds for retry exponential backoff (default: 1.0)
- `--circuit-breaker-threshold`: Number of failures before circuit breaker opens for a domain (default: 5)
- `--circuit-breaker-timeout`: Time in seconds before circuit breaker resets (default: 300)

### Output Format

The crawler generates a JSON file containing:

```json
{
    "metadata": {
        "start_urls": ["string", "string"],
        "crawl_date": "string",
        "total_pages": "integer"
    },
    "site_map": {
        "url": {
            "links": ["string"],
            "depth": "integer",
            "title": "string",
            "timestamp": "string"
        }
    },
    "llmfulltext": "string"
}
```

## Project Structure

```
web_crawler_extractor/
├── docs/
│   ├── PRD.md
│   └── technical_design.md
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── crawler.py
│   ├── content_extractor.py
│   ├── url_handler.py
│   └── site_mapper.py
├── tests/
│   └── __init__.py
├── output/
├── requirements.txt
└── README.md
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details