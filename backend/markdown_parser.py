"""
Markdown Parser

Parses the crew's markdown output into structured JSON resources.
"""

import re
from typing import List, Dict, Any
from backend.models import Resource


def parse_markdown_to_resources(markdown_content: str) -> List[Dict[str, Any]]:
    """
    Parse markdown report into structured resources.

    Extracts resources from markdown sections and converts them to
    a list of Resource dictionaries suitable for the frontend.

    Args:
        markdown_content: Raw markdown content from crew output

    Returns:
        List[Dict]: List of resource dictionaries with type, title, source, url, description

    Example markdown format expected:
        **1. Resource Title** (Type: Open Textbook)
        - **Link:** https://example.com/resource
        - **What it covers:** Description here
        - **Best for:** When to use this
    """
    resources = []

    # Try multiple parsing strategies
    resources = _parse_numbered_resources(markdown_content)

    # If no resources found, try alternative formats
    if not resources:
        resources = _parse_link_sections(markdown_content)

    # If still no resources, try finding all markdown links
    if not resources:
        resources = _parse_all_links(markdown_content)

    return resources


def _parse_numbered_resources(content: str) -> List[Dict[str, Any]]:
    """
    Parse numbered resource format (most common in crew output).

    Format:
        **1. Resource Title** (Type: Open Textbook)
        - **Link:** https://example.com
        - **What it covers:** Description
    """
    resources = []

    # Pattern to match numbered resources
    # Matches: **1. Title** or **Resource 1: Title** or similar
    resource_pattern = r'\*\*(?:\d+\.?|Resource \d+:?)\s+([^\*]+?)\*\*(?:\s+\((?:Type:\s*)?([^\)]+)\))?'

    # Find all numbered resources
    matches = re.finditer(resource_pattern, content)

    for match in matches:
        title = match.group(1).strip()
        resource_type = match.group(2).strip() if match.group(2) else "Resource"

        # Find the content block for this resource (until next numbered item or end)
        start_pos = match.end()
        next_match = re.search(r'\*\*(?:\d+\.?|Resource \d+)', content[start_pos:])
        end_pos = start_pos + next_match.start() if next_match else len(content)
        resource_block = content[start_pos:end_pos]

        # Extract URL from the block
        url = _extract_url(resource_block)

        # Extract source/provider
        source = _extract_source(resource_block)

        # Extract description
        description = _extract_description(resource_block)

        # Only add if we have at least a URL
        if url:
            resources.append({
                "type": _normalize_type(resource_type),
                "title": title,
                "source": source or "Unknown",
                "url": url,
                "description": description
            })

    return resources


def _parse_link_sections(content: str) -> List[Dict[str, Any]]:
    """
    Parse resources from link sections.

    Format:
        ### Topic Area
        [Resource Title](https://example.com)
        Description here
    """
    resources = []

    # Find all markdown links: [text](url)
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    matches = re.finditer(link_pattern, content)

    for match in matches:
        title = match.group(1).strip()
        url = match.group(2).strip()

        # Skip if it's just a navigation link or heading
        if url.startswith('#') or title.lower() in ['back to top', 'top', 'home']:
            continue

        # Try to find context around the link for source and description
        start = max(0, match.start() - 200)
        end = min(len(content), match.end() + 200)
        context = content[start:end]

        source = _extract_source(context)
        description = _extract_description(context)

        # Infer type from URL or context
        resource_type = _infer_type_from_url(url) or _extract_type_from_context(context)

        resources.append({
            "type": resource_type,
            "title": title,
            "source": source or "Unknown",
            "url": url,
            "description": description
        })

    return resources


def _parse_all_links(content: str) -> List[Dict[str, Any]]:
    """
    Fallback: Extract all URLs from markdown as basic resources.
    """
    resources = []

    # Find all URLs (both in markdown links and plain text)
    url_pattern = r'https?://[^\s\)\]\,\>]+'
    urls = re.findall(url_pattern, content)

    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    for url in unique_urls:
        # Try to extract title from surrounding context
        url_pos = content.find(url)
        context_start = max(0, url_pos - 100)
        context_end = min(len(content), url_pos + len(url) + 100)
        context = content[context_start:context_end]

        title = _extract_title_from_context(context, url)
        source = _extract_source(context)
        resource_type = _infer_type_from_url(url)

        resources.append({
            "type": resource_type,
            "title": title or url,
            "source": source or _extract_domain(url),
            "url": url,
            "description": None
        })

    return resources


def _extract_url(text: str) -> str:
    """Extract URL from text block"""
    # Try markdown link format first
    link_match = re.search(r'\[.*?\]\((https?://[^\)]+)\)', text)
    if link_match:
        return link_match.group(1).strip()

    # Try "Link:" or "URL:" prefix
    url_match = re.search(r'(?:Link|URL|Website):\s*(https?://[^\s\n]+)', text, re.IGNORECASE)
    if url_match:
        return url_match.group(1).strip()

    # Try plain URL
    plain_url_match = re.search(r'https?://[^\s\)\]\,\>]+', text)
    if plain_url_match:
        return plain_url_match.group(0).strip()

    return ""


def _extract_source(text: str) -> str:
    """Extract source/provider from text"""
    source_patterns = [
        r'(?:Source|Provider|From):\s*([^\n\-\*]+)',
        r'\(([^)]*(?:MIT|Stanford|OpenStax|Khan|Coursera|edX|LibreTexts)[^)]*)\)',
        r'(?:MIT|Stanford|OpenStax|Khan Academy|Coursera|edX|LibreTexts)[^\n\-]*'
    ]

    for pattern in source_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            source = match.group(1) if match.lastindex else match.group(0)
            return source.strip()

    return ""


def _extract_description(text: str) -> str:
    """Extract description from text block"""
    desc_patterns = [
        r'(?:What it covers|Description|Best for):\s*([^\n]+)',
        r'[-•]\s*([^\n]{30,200})'  # Bullet points with substantial text
    ]

    for pattern in desc_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    return None


def _extract_title_from_context(context: str, url: str) -> str:
    """Extract title from context around URL"""
    # Try to find text before the URL that looks like a title
    before_url = context[:context.find(url)]
    title_match = re.search(r'(?:\*\*|##)\s*([^\*\#\n]+?)(?:\*\*|##|\n|$)', before_url)
    if title_match:
        return title_match.group(1).strip()

    # Try markdown link format
    link_match = re.search(r'\[([^\]]+)\]', before_url)
    if link_match:
        return link_match.group(1).strip()

    return None


def _extract_type_from_context(context: str) -> str:
    """Extract resource type from context"""
    type_match = re.search(r'(?:Type|Format):\s*([^\n\)\-]+)', context, re.IGNORECASE)
    if type_match:
        return _normalize_type(type_match.group(1).strip())

    return "Resource"


def _infer_type_from_url(url: str) -> str:
    """Infer resource type from URL"""
    url_lower = url.lower()

    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return "Video"
    elif '.pdf' in url_lower or 'pdf' in url_lower:
        return "PDF"
    elif any(x in url_lower for x in ['openstax', 'textbook', 'book']):
        return "Textbook"
    elif any(x in url_lower for x in ['course', 'lecture', 'ocw', 'coursera', 'edx']):
        return "Course"
    elif any(x in url_lower for x in ['notes', 'tutorial', 'guide']):
        return "Tutorial"
    else:
        return "Website"


def _normalize_type(type_str: str) -> str:
    """Normalize resource type to standard categories"""
    type_lower = type_str.lower()

    type_map = {
        'open textbook': 'Textbook',
        'textbook': 'Textbook',
        'video lecture': 'Video',
        'lecture series': 'Video',
        'video': 'Video',
        'youtube': 'Video',
        'course notes': 'Course',
        'lecture notes': 'Notes',
        'notes': 'Notes',
        'tutorial': 'Tutorial',
        'interactive tutorial': 'Tutorial',
        'course': 'Course',
        'pdf': 'PDF',
        'website': 'Website',
        'web page': 'Website'
    }

    for key, value in type_map.items():
        if key in type_lower:
            return value

    # Capitalize first letter of each word as fallback
    return type_str.title()


def _extract_domain(url: str) -> str:
    """Extract domain name from URL for source"""
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if domain_match:
        domain = domain_match.group(1)
        # Remove common TLDs for cleaner display
        domain = re.sub(r'\.(com|org|edu|net|io)$', '', domain)
        return domain.title()
    return "Unknown"
