"""
Table of Contents Extractor Tool

Specifically extracts only the Table of Contents section from book pages.
This is much faster than fetching entire page content.
"""
from crewai.tools import BaseTool
import requests
from bs4 import BeautifulSoup
from typing import Type, Optional
from pydantic import BaseModel, Field


class TOCExtractorToolInput(BaseModel):
    """Input schema for TOCExtractorTool"""
    url: str = Field(..., description="The URL of the book page to extract TOC from")


class TOCExtractorTool(BaseTool):
    """
    Tool to extract ONLY the Table of Contents from a book webpage.
    
    This tool is optimized for speed - it:
    1. Fetches HTML from the URL
    2. Looks for TOC-specific HTML structures (nav tags, TOC sections, chapter lists)
    3. Extracts ONLY the TOC section
    4. Returns a clean list of chapters/sections
    
    Use this instead of full page fetcher when you only need the table of contents.
    """
    name: str = "Table of Contents Extractor"
    description: str = (
        "Extracts ONLY the Table of Contents from a book webpage. "
        "Much faster than fetching full page content. Use this when book_url is provided "
        "and you only need chapter/section titles as topics. "
        "Do NOT use this for course pages - use Webpage Content Fetcher instead."
    )
    args_schema: Type[BaseModel] = TOCExtractorToolInput

    def _extract_toc_section(self, soup: BeautifulSoup) -> Optional[str]:
        """Try to find and extract the TOC section using common patterns"""
        
        # Pattern 1: Look for nav elements with TOC-related classes/ids
        toc_selectors = [
            'nav[class*="toc" i]',
            'nav[id*="toc" i]',
            'div[class*="table-of-contents" i]',
            'div[id*="table-of-contents" i]',
            'div[class*="contents" i]',
            'aside[class*="toc" i]',
            'section[class*="toc" i]',
        ]
        
        for selector in toc_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(separator='\n', strip=True)
            except Exception:
                continue
        
        # Pattern 2: Look for ordered/unordered lists that might be TOC
        # Usually TOC has links to chapters
        toc_lists = soup.find_all(['ol', 'ul'], limit=10)
        for toc_list in toc_lists:
            links = toc_list.find_all('a')
            # If list has multiple links, likely a TOC
            if len(links) >= 3:
                parent_text = toc_list.get_text(separator='\n', strip=True)
                # Check if it looks like a TOC (has chapter numbers/names)
                text_lower = parent_text.lower()
                if any(word in text_lower for word in ['chapter', 'section', 'part', 'unit', 'preface', 'introduction', 'appendix']):
                    return parent_text
        
        # Pattern 3: Look for headings followed by lists (common TOC pattern)
        headings = soup.find_all(['h1', 'h2', 'h3'], limit=20)
        for heading in headings:
            heading_text = heading.get_text().lower()
            if any(word in heading_text for word in ['contents', 'chapters', 'table of contents', 'table contents']):
                # Get the next list or div
                next_sibling = heading.find_next_sibling(['ol', 'ul', 'div', 'nav'])
                if next_sibling:
                    return next_sibling.get_text(separator='\n', strip=True)
        
        return None

    def _run(self, url: str) -> str:
        """
        Extract table of contents from book URL.
        
        Args:
            url: The URL of the book page
            
        Returns:
            str: Table of contents as clean text, or error message
        """
        try:
            # Fetch with timeout
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style
            for tag in soup(["script", "style"]):
                tag.decompose()

            # Try to extract TOC section
            toc_content = self._extract_toc_section(soup)
            
            if toc_content:
                # Clean up
                lines = [line.strip() for line in toc_content.split('\n') if line.strip()]
                # Limit to first 300 lines to avoid excessive content
                lines = lines[:300]
                return '\n'.join(lines)
            else:
                # Fallback: Return first 3000 chars (likely to contain TOC if near top)
                text = soup.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                # Return first 200 lines as TOC is usually near the top
                return '\n'.join(lines[:200]) + "\n\n[Note: TOC section not automatically detected. Above is the beginning of the page content.]"

        except requests.exceptions.Timeout:
            return f"ERROR: Request timed out while fetching {url}"
        except requests.exceptions.HTTPError as e:
            return f"ERROR: HTTP error {e.response.status_code} while fetching {url}"
        except requests.exceptions.RequestException as e:
            return f"ERROR: Could not fetch {url}: {str(e)}"
        except Exception as e:
            return f"ERROR: Unexpected error while processing {url}: {str(e)}"
