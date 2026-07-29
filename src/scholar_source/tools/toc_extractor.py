"""
Table of Contents Extractor Tool

Specifically extracts only the Table of Contents section from book pages.
This is much faster than fetching entire page content.
Supports both HTML web pages and PDF files.
"""

import io

import requests
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class TOCExtractorToolInput(BaseModel):
    """Input schema for TOCExtractorTool"""

    url: str = Field(..., description="The URL of the book page to extract TOC from")


class TOCExtractorTool(BaseTool):
    """
    Tool to extract ONLY the Table of Contents from a book webpage or PDF.

    This tool is optimized for speed - it:
    1. Detects if URL is PDF or HTML
    2. For PDFs: Extracts bookmarks/outline or first few pages
    3. For HTML: Looks for TOC-specific HTML structures (nav tags, TOC sections, chapter lists)
    4. Extracts ONLY the TOC section
    5. Returns a clean list of chapters/sections

    Use this instead of full page fetcher when you only need the table of contents.
    Supports both HTML web pages and PDF files.
    """

    name: str = "Table of Contents Extractor"
    description: str = (
        "Extracts ONLY the Table of Contents from a book webpage or PDF file. "
        "Much faster than fetching full page content. Supports both HTML pages and PDF files. "
        "Use this when book_url is provided and you only need chapter/section titles as topics. "
        "Do NOT use this for course pages - use Webpage Content Fetcher instead."
    )
    args_schema: type[BaseModel] = TOCExtractorToolInput

    def _extract_toc_section(self, soup: BeautifulSoup) -> str | None:
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
                    return element.get_text(separator="\n", strip=True)
            except Exception:
                continue

        # Pattern 2: Look for ordered/unordered lists that might be TOC
        # Usually TOC has links to chapters
        toc_lists = soup.find_all(["ol", "ul"], limit=10)
        for toc_list in toc_lists:
            links = toc_list.find_all("a")
            # If list has multiple links, likely a TOC
            if len(links) >= 3:
                parent_text = toc_list.get_text(separator="\n", strip=True)
                # Check if it looks like a TOC (has chapter numbers/names)
                text_lower = parent_text.lower()
                if any(
                    word in text_lower
                    for word in ["chapter", "section", "part", "unit", "preface", "introduction", "appendix"]
                ):
                    return parent_text

        # Pattern 3: Look for headings followed by lists (common TOC pattern)
        headings = soup.find_all(["h1", "h2", "h3"], limit=20)
        for heading in headings:
            heading_text = heading.get_text().lower()
            if any(word in heading_text for word in ["contents", "chapters", "table of contents", "table contents"]):
                # Get the next list or div
                next_sibling = heading.find_next_sibling(["ol", "ul", "div", "nav"])
                if next_sibling:
                    return next_sibling.get_text(separator="\n", strip=True)

        return None

    def _extract_toc_from_pdf(self, pdf_content: bytes) -> str | None:
        """Extract table of contents from PDF using bookmarks/outline"""
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                # Fallback: try older PyPDF2 if pypdf not available
                try:
                    from PyPDF2 import PdfReader
                except ImportError:
                    return None

            pdf_file = io.BytesIO(pdf_content)
            reader = PdfReader(pdf_file)

            # Extract bookmarks/outline (TOC is usually stored as bookmarks)
            if reader.outline:
                toc_lines = []

                def extract_outline_items(items, level=0):
                    for item in items:
                        if isinstance(item, list):
                            extract_outline_items(item, level + 1)
                        else:
                            title = item.title if hasattr(item, "title") else str(item)
                            if title:
                                toc_lines.append(("  " * level) + title)

                extract_outline_items(reader.outline)
                if toc_lines:
                    return "\n".join(toc_lines)

            # Fallback: Extract first few pages (TOC is usually at the beginning)
            # Limit to first 5 pages to avoid processing too much
            text_content = []
            for _i, page in enumerate(reader.pages[:5]):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(page_text)
                except Exception:
                    continue

            if text_content:
                # Combine first few pages and look for TOC-like patterns
                combined_text = "\n".join(text_content)
                lines = combined_text.split("\n")
                # Look for lines that might be TOC entries (have numbers, dots, or chapter keywords)
                toc_candidates = []
                toc_keywords = ["contents", "chapter", "section", "part", "preface", "introduction"]

                for line in lines[:300]:  # First 300 lines should cover TOC
                    line_lower = line.lower().strip()
                    if any(keyword in line_lower for keyword in toc_keywords) or (
                        len(line) > 3 and (line[0].isdigit() or "..." in line or "...." in line)
                    ):
                        toc_candidates.append(line.strip())

                if toc_candidates:
                    return "\n".join(toc_candidates[:200])  # Limit to 200 TOC lines

            return None
        except Exception:
            return None

    def _run(self, url: str) -> str:
        """
        Extract table of contents from book URL or local file path (supports both HTML and PDF).

        Args:
            url: The URL of the book page (HTML or PDF), or a local file path starting with /

        Returns:
            str: Table of contents as clean text, or error message
        """
        try:
            # Handle local file paths (uploaded PDFs)
            if url.startswith("/") or url.startswith("file://"):
                local_path = url.replace("file://", "")
                try:
                    with open(local_path, "rb") as f:
                        pdf_content = f.read()
                except FileNotFoundError:
                    return f"ERROR: Local file not found: {local_path}"
                pdf_toc = self._extract_toc_from_pdf(pdf_content)
                if pdf_toc:
                    lines = [line.strip() for line in pdf_toc.split("\n") if line.strip()]
                    return "\n".join(lines[:300])
                return "[Note: Local PDF TOC extraction failed. PDF may not have bookmarks/outline structure.]"

            # Fetch with timeout
            response = requests.get(
                url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            response.raise_for_status()

            # Check if it's a PDF
            content_type = response.headers.get("content-type", "").lower()
            if url.lower().endswith(".pdf") or "application/pdf" in content_type:
                # Try to extract TOC from PDF
                pdf_toc = self._extract_toc_from_pdf(response.content)
                if pdf_toc:
                    lines = [line.strip() for line in pdf_toc.split("\n") if line.strip()]
                    return "\n".join(lines[:300])
                else:
                    return (
                        "[Note: PDF detected but TOC extraction failed. PDF may not have bookmarks/outline structure.]"
                    )

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style
            for tag in soup(["script", "style"]):
                tag.decompose()

            # Try to extract TOC section
            toc_content = self._extract_toc_section(soup)

            if toc_content:
                # Clean up
                lines = [line.strip() for line in toc_content.split("\n") if line.strip()]
                # Limit to first 300 lines to avoid excessive content
                lines = lines[:300]
                return "\n".join(lines)
            else:
                # Fallback: Return first 3000 chars (likely to contain TOC if near top)
                text = soup.get_text(separator="\n", strip=True)
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                # Return first 200 lines as TOC is usually near the top
                return (
                    "\n".join(lines[:200])
                    + "\n\n[Note: TOC section not automatically detected. Above is the beginning of the page content.]"
                )

        except requests.exceptions.Timeout:
            return f"ERROR: Request timed out while fetching {url}"
        except requests.exceptions.HTTPError as e:
            return f"ERROR: HTTP error {e.response.status_code} while fetching {url}"
        except requests.exceptions.RequestException as e:
            return f"ERROR: Could not fetch {url}: {str(e)}"
        except Exception as e:
            return f"ERROR: Unexpected error while processing {url}: {str(e)}"
