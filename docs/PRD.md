# Web Crawler Extractor - Project Requirements Document

## Project Overview
A text-based browser application that crawls websites and extracts clean, formatted content while maintaining a site map structure.

## Core Requirements

### 1. Crawling Functionality
- Accept a starting URL as input
- Configurable crawl depth
- Configurable maximum number of links to process
- Focus on internal links only (same domain)
- Handle relative and absolute URLs
- Respect robots.txt

### 2. Content Extraction
- Remove headers, footers, advertisements, and navigation elements
- Preserve code formatting in pre/code blocks
- Extract meaningful content from main body
- Maintain text hierarchy and structure
- Handle different character encodings

### 3. Output Format
- Generate JSON output containing:
  - Site map structure
  - Concatenated full text ("llmfulltext")
  - Metadata per page (title, URL, timestamp)
- Preserve document structure in extracted text

### 4. Configuration Options
- Crawl depth limit
- Maximum links to process
- Output file location
- Custom exclusion patterns
- Request delays/timing

### 5. Error Handling
- Handle network errors gracefully
- Log failed requests
- Resume capability for interrupted crawls
- Timeout handling

## Technical Requirements

### 1. Dependencies
- Python 3.8+
- Beautiful Soup 4
- Requests
- urllib
- json

### 2. Performance Considerations
- Asynchronous requests for improved performance
- Memory efficient processing
- Configurable request delays
- Connection pooling

### 3. Code Quality
- Modular design
- Unit tests
- Documentation
- Type hints
- Error handling

## Success Criteria
1. Successfully crawls websites while respecting robots.txt
2. Accurately extracts clean content without boilerplate
3. Generates valid JSON output
4. Maintains code formatting where present
5. Completes crawls within reasonable time limits
6. Handles errors gracefully