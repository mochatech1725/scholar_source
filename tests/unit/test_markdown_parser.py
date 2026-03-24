"""
Unit tests for markdown_parser.py

Tests the parsing of CrewAI markdown output into structured resources.
"""

import pytest
from backend.markdown_parser import (
    parse_markdown_to_resources,
    _filter_excluded_domains,
    _contains_error
)


class TestParseMarkdownToResources:
    """Test markdown parsing functionality."""

    def test_parse_numbered_resources(self):
        """Should parse numbered resource format correctly."""
        markdown = """
**1. OpenStax Textbook** (Type: Open Textbook)
- **Link:** https://openstax.org/books/calculus
- **What it covers:** Calculus fundamentals
- **Best for:** Self-study

**2. MIT OCW Lectures** (Type: Lecture Videos)
- **Link:** https://ocw.mit.edu/courses/mathematics/
- **What it covers:** Complete lecture series
"""
        result = parse_markdown_to_resources(markdown)
        resources = result['resources']

        assert len(resources) == 2
        assert resources[0]['title'] == 'OpenStax Textbook'
        assert resources[0]['type'] == 'Textbook'
        assert 'openstax.org' in resources[0]['url']
        assert resources[1]['title'] == 'MIT OCW Lectures'
        assert resources[1]['type'] == 'Video'

    def test_parse_with_textbook_info(self):
        """Should extract textbook information from markdown."""
        markdown = """
**Textbook:** Calculus, 9th ed., by Stewart

**1. Some Resource**
- **Link:** https://example.com
- **What it covers:** Something
"""
        result = parse_markdown_to_resources(markdown)
        textbook = result['textbook_info']

        assert textbook is not None
        assert 'Calculus' in textbook.get('title', '')
        assert 'Stewart' in textbook.get('author', '')

    def test_filter_error_resources(self):
        """Should exclude resources with ERROR in description."""
        markdown = """
**1. Valid Resource**
- **Link:** https://example.com/valid
- **What it covers:** Good content

**2. Error Resource**
- **Link:** https://broken.com/error
- **What it covers:** ERROR: Could not fetch https://broken.com/error

**3. Failed Resource**
- **Link:** ERROR
- **What it covers:** Failed to connect
"""
        result = parse_markdown_to_resources(markdown)
        resources = result['resources']

        # Should only have 1 valid resource (error ones filtered out)
        assert len(resources) == 1
        assert resources[0]['url'] == 'https://example.com/valid'

    def test_exclude_specific_domains(self):
        """Should filter out excluded domains."""
        markdown = """
**1. MIT Resource**
- **Link:** https://ocw.mit.edu/courses/
- **What it covers:** MIT course

**2. Khan Academy**
- **Link:** https://www.khanacademy.org/math
- **What it covers:** Khan Academy lessons

**3. OpenStax**
- **Link:** https://openstax.org/books
- **What it covers:** Free textbooks
"""
        result = parse_markdown_to_resources(
            markdown,
            excluded_sites="mit.edu, khanacademy.org"
        )
        resources = result['resources']

        # Should only have OpenStax (MIT and Khan excluded)
        assert len(resources) == 1
        assert 'openstax.org' in resources[0]['url']

    def test_parse_link_sections_fallback(self):
        """Should fall back to link section parsing if numbered format not found."""
        markdown = """
### Recommended Textbooks

[Introduction to Algorithms](https://mitpress.mit.edu/books/introduction-algorithms)
- Great comprehensive textbook

[Algorithms by Sedgewick](https://algs4.cs.princeton.edu/home/)
- Excellent practical approach
"""
        result = parse_markdown_to_resources(markdown)
        resources = result['resources']

        # Should extract at least one resource
        assert len(resources) > 0

    def test_parse_all_links_fallback(self):
        """Should extract all markdown links as last resort."""
        markdown = """
Check out these resources:
- [Resource A](https://example.com/a)
- [Resource B](https://example.com/b)
"""
        result = parse_markdown_to_resources(markdown)
        resources = result['resources']

        # Should extract links
        assert len(resources) >= 2

    def test_empty_markdown_returns_empty_list(self):
        """Should return empty list for empty markdown."""
        result = parse_markdown_to_resources("")
        resources = result['resources']

        assert resources == []
        assert result['textbook_info'] is None

    def test_no_textbook_info_returns_none(self):
        """Should return None for textbook_info if not present."""
        markdown = """
**1. Some Resource**
- **Link:** https://example.com
- **What it covers:** Something
"""
        result = parse_markdown_to_resources(markdown)

        assert result['textbook_info'] is None


class TestFilterExcludedDomains:
    """Test domain filtering functionality."""

    def test_filter_single_domain(self):
        """Should filter out single excluded domain."""
        resources = [
            {"url": "https://mit.edu/course", "title": "MIT"},
            {"url": "https://stanford.edu/course", "title": "Stanford"}
        ]

        filtered = _filter_excluded_domains(resources, "mit.edu")

        assert len(filtered) == 1
        assert "stanford.edu" in filtered[0]['url']

    def test_filter_multiple_domains(self):
        """Should filter out multiple excluded domains."""
        resources = [
            {"url": "https://mit.edu/course", "title": "MIT"},
            {"url": "https://stanford.edu/course", "title": "Stanford"},
            {"url": "https://berkeley.edu/course", "title": "Berkeley"}
        ]

        filtered = _filter_excluded_domains(resources, "mit.edu, stanford.edu")

        assert len(filtered) == 1
        assert "berkeley.edu" in filtered[0]['url']

    def test_filter_with_whitespace(self):
        """Should handle whitespace in excluded_sites string."""
        resources = [
            {"url": "https://mit.edu/course", "title": "MIT"},
            {"url": "https://stanford.edu/course", "title": "Stanford"}
        ]

        filtered = _filter_excluded_domains(resources, "  mit.edu  ,  stanford.edu  ")

        assert len(filtered) == 0

    def test_filter_case_insensitive(self):
        """Should filter case-insensitively."""
        resources = [
            {"url": "https://MIT.EDU/course", "title": "MIT"},
            {"url": "https://stanford.edu/course", "title": "Stanford"}
        ]

        filtered = _filter_excluded_domains(resources, "mit.edu")

        assert len(filtered) == 1

    def test_filter_partial_domain_match(self):
        """Should match partial domain strings."""
        resources = [
            {"url": "https://ocw.mit.edu/course", "title": "MIT OCW"},
            {"url": "https://stanford.edu/course", "title": "Stanford"}
        ]

        filtered = _filter_excluded_domains(resources, "mit")

        assert len(filtered) == 1
        assert "stanford.edu" in filtered[0]['url']

    def test_empty_excluded_sites_returns_all(self):
        """Should return all resources if excluded_sites is empty."""
        resources = [
            {"url": "https://example1.com", "title": "R1"},
            {"url": "https://example2.com", "title": "R2"}
        ]

        filtered = _filter_excluded_domains(resources, "")

        assert len(filtered) == 2

    def test_whitespace_only_excluded_sites_returns_all(self):
        """Should return all resources if excluded_sites is whitespace only."""
        resources = [
            {"url": "https://example1.com", "title": "R1"},
            {"url": "https://example2.com", "title": "R2"}
        ]

        filtered = _filter_excluded_domains(resources, "   ")

        assert len(filtered) == 2


class TestContainsError:
    """Test error detection in resource fields."""

    @pytest.mark.parametrize("url,title,description,should_contain_error", [
        # No errors
        ("https://example.com", "Valid Title", "Valid description", False),

        # ERROR: prefix (case-insensitive) — indicator is 'ERROR:'
        ("https://ERROR.com", "Title", "Description", False),        # no colon after ERROR
        ("https://example.com", "ERROR: Failed", "Description", True),
        ("https://example.com", "Title", "ERROR: Could not fetch", True),

        # 'error' alone without colon does not match 'ERROR:'
        ("https://error.com/page", "Title", "Description", False),
        ("https://example.com", "error in title", "Description", False),
        ("https://example.com", "Title", "error in description", False),

        # 'failed to' pattern (case-insensitive)
        ("https://example.com", "Title", "Failed to connect", True),
        ("https://example.com", "Failed request", "Description", False),   # 'failed to' not present
        ("https://example.com", "Title", "Request failure detected", False),  # 'failed to' not present

        # 'Could not fetch' pattern — only exact phrase matches
        ("https://example.com", "Title", "Could not fetch resource", True),
        ("https://example.com", "Could not load", "Description", False),   # 'could not fetch' not present
        ("https://example.com", "Title", "Cannot access page", False),     # no indicator matches

        # Edge cases
        ("", "", "", False),
        ("https://example.com", "", "", False),
        ("https://example.com", "Normal Title", "", False),
    ])
    def test_contains_error_patterns(self, url, title, description, should_contain_error):
        """Should detect error indicators in resource fields."""
        result = _contains_error(url, title, description)
        assert result == should_contain_error


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_malformed_markdown_does_not_crash(self):
        """Should handle malformed markdown gracefully."""
        malformed = """
        **1. Incomplete resource
        - Missing closing
        **2. Another** incomplete
        Random text without structure
        """

        # Should not raise exception
        result = parse_markdown_to_resources(malformed)
        assert isinstance(result, dict)
        assert 'resources' in result
        assert isinstance(result['resources'], list)

    def test_none_excluded_sites(self):
        """Should handle None excluded_sites parameter."""
        markdown = """
**1. Resource**
- **Link:** https://example.com
- **What it covers:** Something
"""
        result = parse_markdown_to_resources(markdown, excluded_sites=None)
        resources = result['resources']

        assert len(resources) == 1

    def test_very_long_markdown(self):
        """Should handle very long markdown content."""
        # Generate 100 resources
        markdown = "\n".join([
            f"""
**{i}. Resource {i}**
- **Link:** https://example{i}.com
- **What it covers:** Topic {i}
"""
            for i in range(1, 101)
        ])

        result = parse_markdown_to_resources(markdown)
        resources = result['resources']

        # Should parse all resources
        assert len(resources) >= 90  # Allow some tolerance for parsing

    def test_unicode_characters(self):
        """Should handle unicode characters in markdown."""
        markdown = """
**1. 数学教材** (Type: Textbook)
- **Link:** https://example.com/chinese
- **What it covers:** Mathématiques avancées

**2. Física Resource** (Type: Notes)
- **Link:** https://example.com/spanish
- **What it covers:** Tópicos de física
"""
        result = parse_markdown_to_resources(markdown)
        resources = result['resources']

        assert len(resources) == 2
        assert '数学' in resources[0]['title']

    def test_special_characters_in_urls(self):
        """Should handle special characters in URLs."""
        markdown = """
**1. Resource with Query**
- **Link:** https://example.com/page?param=value&other=123
- **What it covers:** Something

**2. Resource with Fragment**
- **Link:** https://example.com/page#section-2
- **What it covers:** Something else
"""
        result = parse_markdown_to_resources(markdown)
        resources = result['resources']

        assert len(resources) == 2
        assert 'param=value' in resources[0]['url']
        assert '#section-2' in resources[1]['url']
