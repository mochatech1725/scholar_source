"""
Webpage Content Fetcher Tool

Fetches full HTML content from a webpage and returns clean text.
"""
from crewai.tools import BaseTool
import requests
from bs4 import BeautifulSoup
from typing import Type
from pydantic import BaseModel, Field


class WebPageFetcherToolInput(BaseModel):
    """Input schema for WebPageFetcherTool"""
    url: str = Field(..., description="The URL of the webpage to fetch")


class WebPageFetcherTool(BaseTool):
    """
    Tool to fetch and extract full text content from a webpage.

    This tool:
    1. Fetches the HTML content from the given URL
    2. Parses the HTML using BeautifulSoup
    3. Removes script and style tags
    4. Returns clean text content

    Perfect for extracting course information, textbook details, and syllabus content
    from university course pages.
    """
    name: str = "Webpage Content Fetcher"
    description: str = (
        "Fetches and returns the full text content of a webpage given its URL. "
        "Use this to extract course information, textbook details, and syllabus content. "
        "Returns clean text with scripts and styles removed."
    )
    args_schema: Type[BaseModel] = WebPageFetcherToolInput

    def _run(self, url: str) -> str:
        """
        Fetch webpage content and return as clean text.

        Args:
            url: The URL of the webpage to fetch

        Returns:
            str: Clean text content of the webpage, or an error message
        """
        try:
            # Fetch the webpage
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Get text content
            text = soup.get_text(separator='\n', strip=True)

            # Clean up excessive whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            cleaned_text = '\n'.join(lines)

            return cleaned_text

        except requests.exceptions.Timeout:
            return f"ERROR: Request timed out while fetching {url}"
        except requests.exceptions.HTTPError as e:
            return f"ERROR: HTTP error {e.response.status_code} while fetching {url}"
        except requests.exceptions.RequestException as e:
            return f"ERROR: Could not fetch {url}: {str(e)}"
        except Exception as e:
            return f"ERROR: Unexpected error while processing {url}: {str(e)}"
