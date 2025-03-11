import asyncio
import argparse
import logging
from pathlib import Path
from typing import Optional
import sys

from .config import CrawlerConfig
from .crawler import Crawler

def setup_logging(debug: bool = False):
    """Configure logging settings."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('crawler.log')
        ]
    )

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Web Crawler and Content Extractor'
    )
    
    # Create a mutually exclusive group for URL input methods
    url_group = parser.add_mutually_exclusive_group(required=True)
    
    url_group.add_argument(
        '--urls',
        nargs='+',
        help='One or more URLs to crawl'
    )
    
    url_group.add_argument(
        '--url-file',
        type=Path,
        help='Path to a text file containing URLs to crawl (one URL per line)'
    )
    
    parser.add_argument(
        '--exclude-keywords',
        nargs='+',
        help='Keywords to exclude from URLs (URLs containing these keywords will be skipped)'
    )
    
    parser.add_argument(
        '--depth',
        type=int,
        default=3,
        help='Maximum crawl depth (default: 3)'
    )
    
    parser.add_argument(
        '--max-links',
        type=int,
        default=100,
        help='Maximum number of links to crawl (default: 100)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('output/crawl_result.json'),
        help='Output file path (default: output/crawl_result.json)'
    )
    
    parser.add_argument(
        '--ignore-robots',
        action='store_true',
        help='Ignore robots.txt restrictions'
    )
    
    parser.add_argument(
        '--same-path-only',
        action='store_true',
        help='Crawl only URLs with the same path prefix as the starting URL'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum number of retry attempts for failed requests (default: 3)'
    )
    
    parser.add_argument(
        '--retry-delay',
        type=float,
        default=1.0,
        help='Base delay in seconds for retry exponential backoff (default: 1.0)'
    )
    
    parser.add_argument(
        '--circuit-breaker-threshold',
        type=int,
        default=5,
        help='Number of failures before circuit breaker opens for a domain (default: 5)'
    )
    
    parser.add_argument(
        '--circuit-breaker-timeout',
        type=int,
        default=300,
        help='Time in seconds before circuit breaker resets (default: 300)'
    )
    
    return parser.parse_args()

async def main():
    """Main entry point for the crawler."""
    args = parse_arguments()
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)
    
    try:
        # Determine URLs to crawl
        urls = []
        exclude_keywords = args.exclude_keywords or []
        
        if args.url_file:
            # Read URLs from file
            try:
                with open(args.url_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                
                # Check for exclude keywords section
                if '[exclude_keywords]' in lines:
                    # Split the file into URLs and exclude keywords
                    keyword_section_index = lines.index('[exclude_keywords]')
                    urls = lines[:keyword_section_index]
                    
                    # Get keywords from the section (skip the section header)
                    file_exclude_keywords = lines[keyword_section_index + 1:]
                    exclude_keywords.extend(file_exclude_keywords)
                else:
                    # No exclude keywords section, all lines are URLs
                    urls = lines
                
                if not urls:
                    logger.error(f"No valid URLs found in {args.url_file}")
                    return 1
                
                logger.info(f"Loaded {len(urls)} URLs from {args.url_file}")
                if exclude_keywords:
                    logger.info(f"Using exclude keywords: {', '.join(exclude_keywords)}")
            except Exception as e:
                logger.error(f"Failed to read URL file {args.url_file}: {str(e)}")
                return 1
        else:
            # Use URLs from command line
            urls = args.urls
        
        # Create configuration
        config = CrawlerConfig(
            max_depth=args.depth,
            max_links=args.max_links,
            delay=args.delay,
            timeout=args.timeout,
            output_path=args.output,
            exclusion_patterns=[],
            exclude_keywords=exclude_keywords,
            respect_robots_txt=not args.ignore_robots,
            same_path_only=args.same_path_only,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            circuit_breaker_threshold=args.circuit_breaker_threshold,
            circuit_breaker_timeout=args.circuit_breaker_timeout
        )
        
        # Initialize and run crawler
        crawler = Crawler(config)
        logger.info(f"Starting crawl of {len(urls)} URLs")
        
        results = await crawler.crawl(urls)
        crawler.save_results(results)
        
        logger.info(f"Crawl completed. Results saved to {args.output}")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Crawl interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Crawl failed: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))