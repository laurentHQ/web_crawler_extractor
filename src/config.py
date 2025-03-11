from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

@dataclass
class CrawlerConfig:
    max_depth: int
    max_links: int
    delay: float
    timeout: int
    output_path: Path
    exclusion_patterns: List[str]
    exclude_keywords: List[str]  # Keywords to exclude from URLs
    user_agent: str = "WebCrawlerExtractor/1.0"
    respect_robots_txt: bool = True
    same_path_only: bool = False
    # Retry mechanism parameters
    max_retries: int = 3
    retry_delay: float = 1.0  # Base delay for exponential backoff
    # Circuit breaker pattern parameters
    circuit_breaker_threshold: int = 5  # Number of failures before circuit opens
    circuit_breaker_timeout: int = 300  # Time in seconds before circuit resets
    
    @classmethod
    def default_config(cls):
        return cls(
            max_depth=3,
            max_links=100,
            delay=1.0,
            timeout=30,
            output_path=Path("output/crawl_result.json"),
            exclusion_patterns=[
                "*/ads/*",
                "*/advertisement/*",
                "*/analytics/*",
                "*/tracking/*"
            ],
            exclude_keywords=[]
        )