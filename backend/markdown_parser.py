"""
Markdown Parser

Parses the crew's markdown output into structured JSON resources.
"""

import re
from typing import List, Dict, Any, Optional
from backend.models import Resource


def parse_markdown_to_resources(markdown_content: str, excluded_sites: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse markdown report into structured resources and metadata.

    Extracts resources from markdown sections and converts them to
    a list of Resource dictionaries suitable for the frontend, along
    with textbook information if available.

    Args:
        markdown_content: Raw markdown content from crew output
        excluded_sites: Comma-separated list of domains to exclude (e.g., "mit.edu, khanacademy.org")

    Returns:
        Dict with 'resources' (list) and 'textbook_info' (dict or None)

    Example markdown format expected:
        **1. Resource Title** (Type: Open Textbook)
        - **Link:** https://example.com/resource
        - **What it covers:** Description here
        - **Best for:** When to use this
    """
    resources = []

    # Extract textbook information from the full content before stripping sections
    textbook_info = _extract_textbook_info(markdown_content)

    # Strip non-resource sections so their URLs don't get picked up as resources.
    # These sections (Textbook Information, NotebookLM instructions, Study Tips, etc.)
    # contain links that are metadata/UI, not discovered resources.
    content_for_resources = _strip_non_resource_sections(markdown_content)

    # Try multiple parsing strategies
    resources = _parse_numbered_resources(content_for_resources)

    # If no resources found, try alternative formats
    if not resources:
        resources = _parse_link_sections(content_for_resources)

    # If still no resources, try finding all markdown links
    if not resources:
        resources = _parse_all_links(content_for_resources)

    # Filter out excluded domains if provided
    if excluded_sites and excluded_sites.strip():
        resources = _filter_excluded_domains(resources, excluded_sites)

    # Detect section-grouped output (chapter-aware mode)
    section_groups = _parse_section_groups(content_for_resources)

    return {
        "resources": resources,
        "textbook_info": textbook_info,
        "section_groups": section_groups
    }


def _filter_excluded_domains(resources: List[Dict[str, Any]], excluded_sites: str) -> List[Dict[str, Any]]:
    """
    Filter out resources whose URLs contain any of the excluded domains.

    Args:
        resources: List of resource dictionaries
        excluded_sites: Comma-separated string of domains to exclude (e.g., "mit.edu, khanacademy.org")

    Returns:
        Filtered list of resources with excluded domains removed
    """
    # Parse excluded domains - split by comma and clean up whitespace
    excluded_domains = [domain.strip().lower() for domain in excluded_sites.split(',') if domain.strip()]
    
    if not excluded_domains:
        return resources

    filtered = []
    for resource in resources:
        url = resource.get('url', '').lower()
        
        # Check if URL contains any excluded domain
        should_exclude = False
        for excluded_domain in excluded_domains:
            # Check if the excluded domain appears in the URL
            # This handles cases like "mit" matching "ocw.mit.edu"
            if excluded_domain in url:
                should_exclude = True
                break
        
        if not should_exclude:
            filtered.append(resource)
    
    return filtered


def _parse_section_groups(content: str) -> Optional[List[Dict[str, Any]]]:
    """
    Detect and parse section-grouped output from chapter-aware mode.

    Looks for ### headers that introduce sections (e.g., "### Surface Integrals"
    or "### Section: Surface Integrals"), then collects the numbered resources
    under each header.

    Returns:
        List of {"section": str, "resources": List[dict]} if section headers found,
        None otherwise (standard flat output).
    """
    # Match ### headers, optionally prefixed with "Section:"
    section_pattern = re.compile(r'^###\s+(?:Section:\s*)?(.+)$', re.MULTILINE)
    matches = list(section_pattern.finditer(content))

    if not matches:
        return None

    groups = []
    for i, match in enumerate(matches):
        section_name = match.group(1).strip()
        section_start = match.end()
        section_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[section_start:section_end]

        section_resources = _parse_numbered_resources(section_content)
        if not section_resources:
            section_resources = _parse_link_sections(section_content)

        for r in section_resources:
            r["section"] = section_name

        if section_resources:
            groups.append({"section": section_name, "resources": section_resources})

    return groups if groups else None


def _strip_non_resource_sections(content: str) -> str:
    """
    Remove sections that contain metadata/UI links (not discovered resources).

    Strips:
    - Textbook Information / Course Textbook sections
    - NotebookLM instructions (How to Add These...)
    - Study Tips sections
    - Course Overview sections

    This prevents URLs in those sections from being misidentified as resources.
    """
    section_headers = [
        r'#+\s*(?:Textbook Information|Course Textbook|Official Textbook)',
        r'#+\s*(?:How to Add|NotebookLM Instructions?|Adding.*NotebookLM)',
        r'#+\s*(?:Study Tips?|Tips? for|Using Multiple)',
        r'#+\s*(?:Course Overview|About This Course)',
        r'#+\s*(?:Need More Help)',
    ]

    pattern = r'(' + '|'.join(section_headers) + r').*?(?=\n#+\s|\Z)'
    return re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)


def _contains_error(url: str, title: str, description: str) -> bool:
    """
    Check if any of the resource fields contain error messages.

    Args:
        url: Resource URL
        title: Resource title
        description: Resource description

    Returns:
        bool: True if any field contains an error indicator
    """
    error_indicators = ['ERROR:', 'Could not fetch', 'failed to', 'HTTP error', 'timed out']

    fields_to_check = [url, title, description or '']

    for field in fields_to_check:
        field_lower = field.lower()
        for indicator in error_indicators:
            if indicator.lower() in field_lower:
                return True

    return False


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

        # Only add if we have at least a URL and it's not an error
        # Skip resources that contain ERROR in the URL, title, or description
        if url and not _contains_error(url, title, description):
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

        # Skip resources that contain error messages
        if not _contains_error(url, title, description):
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

        # Skip resources that contain error messages
        if not _contains_error(url, title or '', ''):
            resources.append({
                "type": resource_type,
                "title": title or url,
                "source": source or _extract_domain(url),
                "url": url,
                "description": None
            })

    return resources


def _extract_url(text: str) -> str:
    """
    Extract URL from text block using multiple patterns.

    Args:
        text: Text block to search for URLs

    Returns:
        URL string if found, empty string otherwise
    """
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
    """
    Extract source/provider information from text.

    Args:
        text: Text block to search for source information

    Returns:
        Source name if found, empty string otherwise
    """
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
    """
    Extract description from text block.

    Args:
        text: Text block to search for descriptions

    Returns:
        Description string if found, None otherwise
    """
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
    """
    Extract title from context surrounding a URL.

    Args:
        context: Text context around the URL
        url: The URL to extract title for

    Returns:
        Title string if found, None otherwise
    """
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
    """
    Extract resource type from surrounding context.

    Args:
        context: Text context to search

    Returns:
        Normalized resource type string
    """
    type_match = re.search(r'(?:Type|Format):\s*([^\n\)\-]+)', context, re.IGNORECASE)
    if type_match:
        return _normalize_type(type_match.group(1).strip())

    return "Resource"


def _infer_type_from_url(url: str) -> str:
    """
    Infer resource type by analyzing URL patterns.

    Args:
        url: URL to analyze

    Returns:
        Inferred resource type (Video, PDF, Textbook, Course, etc.)
    """
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
    """
    Normalize resource type to standard categories.

    Args:
        type_str: Raw type string from parsing

    Returns:
        Normalized type (Textbook, Video, Course, Notes, etc.)
    """
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
    """
    Extract and clean domain name from URL for use as source.

    Args:
        url: Full URL

    Returns:
        Cleaned domain name (e.g., "mit.edu" becomes "Mit")
    """
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if domain_match:
        domain = domain_match.group(1)
        # Remove common TLDs for cleaner display
        domain = re.sub(r'\.(com|org|edu|net|io)$', '', domain)
        return domain.title()
    return "Unknown"


def _extract_textbook_info(content: str) -> Dict[str, str]:
    """
    Extract textbook information from markdown content.

    Looks for sections like "Textbook Information" or similar headings
    and extracts title, author(s), and source information.

    Returns:
        Dict with 'title', 'author', and 'source' keys, or None if not found
    """

    # First, try to find a structured "Textbook Information" section with separate fields
    # Format: ## Textbook Information
    #         **Textbook:** Title
    #         **Author:** Author Name
    section_match = re.search(
        r'#+\s*(?:Textbook Information|Course Textbook|Official Textbook)[:\s]*\n(.*?)(?=\n#|\n---|\Z)',
        content,
        re.IGNORECASE | re.DOTALL
    )
    
    if section_match:
        section = section_match.group(1)
        
        # Look for **Textbook:** or **Title:** pattern
        title_match = re.search(r'\*\*(?:Textbook|Title|Book):\*\*\s*([^\n]+)', section, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else None
        
        # Look for **Author:** pattern
        author_match = re.search(r'\*\*Authors?:\*\*\s*([^\n]+)', section, re.IGNORECASE)
        author = author_match.group(1).strip() if author_match else None
        
        # Look for **Source:** pattern
        source_match = re.search(r'\*\*Source:\*\*\s*([^\n]+)', section, re.IGNORECASE)
        source = source_match.group(1).strip() if source_match else None
        
        if title or author:
            return {"title": title, "author": author, "source": source}
    
    # Fallback: Try individual line patterns
    textbook_patterns = [
        r'\*\*Textbook:\*\*\s*([^\n]+)',
        r'\*\*Text:\*\*\s*([^\n]+)',
        r'\*\*Official Textbook:\*\*\s*([^\n]+)',
        r'(?:Textbook|Text):\s*([^\n]+)',  # Plain "Textbook:" or "Text:" format (same line)
        r'(?:Textbook|Text):\s*\n\s*([^\n]+)',  # Textbook/Text on one line, value on next line
        r'(?:\*\*Textbook:\*\*|\*\*Text:\*\*)\s*\n\s*([^\n]+)'  # Bold version with value on next line
    ]

    for pattern in textbook_patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            section_text = match.group(1).strip()

            # For simple "Textbook: Author, Title" or "Text: Title by Author" formats
            if ',' in section_text and not re.search(r'(?:Title|Author|Source):', section_text, re.IGNORECASE):
                # Check for "by [author]" pattern: "Title, edition, by Author"
                by_match = re.search(r'by\s+([^.\n]+)', section_text, re.IGNORECASE)
                if by_match:
                    # Extract author from "by xxx"
                    author = by_match.group(1).strip()
                    # Extract title (everything before "by")
                    title_part = section_text[:by_match.start()].strip()
                    # Remove edition info like "14th ed.," from title
                    title = re.sub(r',\s*\d+(?:st|nd|rd|th)\s+ed\.?,?\s*$', '', title_part).strip()
                    # Remove trailing commas
                    title = title.rstrip(',').rstrip('.')
                    return {
                        "title": title,
                        "author": author,
                        "source": None
                    }
                else:
                    # Try format: "Title, Author1, Author2" (e.g., "Engineering Mechanics: Statics, Bedford, Fowler")
                    # Split by comma and check if first part looks like a title (contains colon or is long)
                    parts = section_text.split(',')
                    if len(parts) >= 2:
                        first_part = parts[0].strip()
                        # If first part has a colon or is longer than typical author name, it's likely the title
                        if ':' in first_part or len(first_part) > 30:
                            title = first_part
                            # Everything after first comma is the author(s)
                            author = ', '.join([p.strip() for p in parts[1:]]).rstrip('.')
                            return {
                                "title": title,
                                "author": author,
                                "source": None
                            }
                        else:
                            # Original format: "Author, Title"
                            author = first_part
                            title = ', '.join([p.strip() for p in parts[1:]]).rstrip('.')
                            return {
                                "title": title,
                                "author": author,
                                "source": None
                            }

            # Extract title (matches Title:, Book:, or Textbook:)
            title_match = re.search(r'(?:\*\*)?(?:Title|Book|Textbook)[:\s]+\*?\*?([^\n\*]+)', section_text, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else None

            # Extract author(s)
            author_match = re.search(r'(?:\*\*)?Author(?:s)?[:\s]+\*?\*?([^\n\*]+)', section_text, re.IGNORECASE)
            author = author_match.group(1).strip() if author_match else None

            # Extract source
            source_match = re.search(r'(?:\*\*)?Source[:\s]+\*?\*?([^\n\*]+)', section_text, re.IGNORECASE)
            source = source_match.group(1).strip() if source_match else None

            # If we found at least title or author, return the info
            if title or author:
                return {
                    "title": title,
                    "author": author,
                    "source": source
                }

    return None
