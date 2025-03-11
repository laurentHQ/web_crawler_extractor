from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import re
import logging

class ContentExtractor:
    """Handles the extraction and cleaning of web content."""
    
    def __init__(self):
        self.excluded_tags = {
            'header', 'footer', 'nav', 'aside', 'script', 'style',
            'noscript', 'iframe', 'ad', 'advertisement'
        }
        self.preserved_tags = {'pre', 'code'}
        self.logger = logging.getLogger(__name__)

    def extract_content(self, html: str, url: str) -> Dict:
        """
        Extract clean content from HTML while preserving code blocks.
        
        Args:
            html: Raw HTML content
            url: Source URL of the content
            
        Returns:
            Dict containing extracted content and metadata
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Store code blocks before cleaning
            code_blocks = self._preserve_code_blocks(soup)
            
            # Remove unwanted elements
            self._remove_unwanted_elements(soup)
            
            # Extract title
            title = self._extract_title(soup)
            
            # Extract main content
            main_content = self._extract_main_content(soup)
            
            # Reinsert code blocks
            final_content = self._reinsert_code_blocks(main_content, code_blocks)
            
            return {
                'title': title,
                'url': url,
                'content': final_content,
                'code_blocks': code_blocks
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting content from {url}: {str(e)}")
            return {
                'title': '',
                'url': url,
                'content': '',
                'code_blocks': []
            }

    def _preserve_code_blocks(self, soup: BeautifulSoup) -> List[str]:
        """Extract and preserve code blocks."""
        code_blocks = []
        for tag in soup.find_all(self.preserved_tags):
            code_blocks.append({
                'content': tag.get_text(),
                'language': tag.get('class', [''])[0] if tag.get('class') else ''
            })
            tag.replace_with(f'[CODE_BLOCK_{len(code_blocks)-1}]')
        return code_blocks

    def _remove_unwanted_elements(self, soup: BeautifulSoup) -> None:
        """Remove unwanted HTML elements."""
        for tag in self.excluded_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove hidden elements
        for element in soup.find_all(style=re.compile(r'display:\s*none')):
            element.decompose()

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()
        return ''

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from the page."""
        # Try to find main content container
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|article'))
        
        if main_content:
            return self._clean_text(main_content.get_text())
        return self._clean_text(soup.get_text())

    def _reinsert_code_blocks(self, content: str, code_blocks: List[Dict]) -> str:
        """Reinsert preserved code blocks into content."""
        for i, block in enumerate(code_blocks):
            placeholder = f'[CODE_BLOCK_{i}]'
            replacement = f"\n```{block['language']}\n{block['content']}\n```\n"
            content = content.replace(placeholder, replacement)
        return content

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove empty lines
        text = re.sub(r'\n\s*\n', '\n', text)
        return text.strip()