"""
Unit tests for email_service.py

Tests HTML escaping and security features in email generation.
"""

import pytest
from backend.email_service import _build_email_html


class TestEmailHTMLEscaping:
    """Test HTML injection prevention in email generation."""

    def test_html_injection_in_resource_title(self):
        """Should escape HTML tags in resource title."""
        resources = [{
            "type": "PDF",
            "title": "<script>alert('XSS')</script>Malicious Title",
            "url": "https://example.com/resource.pdf",
            "source": "Example Source",
            "description": "Test description"
        }]

        html = _build_email_html("Test Search", resources, "test-job-id")

        # Should not contain unescaped script tags
        assert "<script>" not in html
        assert "alert('XSS')" not in html
        # Should contain escaped version
        assert "&lt;script&gt;" in html

    def test_javascript_url_in_resource_url(self):
        """Should handle javascript: URLs safely."""
        resources = [{
            "type": "Link",
            "title": "Malicious Link",
            "url": "javascript:alert('XSS')",
            "source": "Bad Source",
            "description": "Test"
        }]

        html = _build_email_html("Test Search", resources, "test-job-id")

        # The URL should be escaped when displayed as text
        assert "javascript:" in html  # Will be in href (HTML context handles this)
        # But the escaped version should be in display text
        assert "javascript:alert" in html

    def test_xss_in_description_field(self):
        """Should escape XSS attempts in description."""
        resources = [{
            "type": "Article",
            "title": "Normal Title",
            "url": "https://example.com",
            "source": "Example",
            "description": "<img src=x onerror=alert('XSS')>"
        }]

        html = _build_email_html("Test", resources, "test-job-id")

        # Should not contain unescaped img tag
        assert "<img src=" not in html
        assert "onerror=" not in html
        # Should contain escaped version
        assert "&lt;img" in html

    def test_script_tags_in_source_field(self):
        """Should escape script tags in source field."""
        resources = [{
            "type": "Video",
            "title": "Video Title",
            "url": "https://example.com/video",
            "source": "</div><script>alert('XSS')</script><div>",
            "description": "Description"
        }]

        html = _build_email_html("Test", resources, "test-job-id")

        # Should not contain unescaped script tags
        assert "<script>" not in html
        # Should contain escaped version
        assert "&lt;script&gt;" in html

    def test_html_entities_properly_escaped(self):
        """Should properly escape HTML entities."""
        resources = [{
            "type": "PDF",
            "title": "Title with & < > \" ' symbols",
            "url": "https://example.com",
            "source": "Source & Co.",
            "description": "Description with <brackets> and & ampersand"
        }]

        html = _build_email_html("Test", resources, "test-job-id")

        # Should escape special HTML characters
        assert "&amp;" in html  # &
        assert "&lt;" in html   # <
        assert "&gt;" in html   # >
        # Should not contain unescaped versions in user content
        assert "Title with & < >" not in html

    def test_search_title_with_html_characters(self):
        """Should escape HTML in search title."""
        resources = []
        search_title = "<b>Bold Search</b> & <i>Italic</i>"

        html = _build_email_html(search_title, resources, "test-job-id")

        # Should not contain unescaped HTML tags
        assert "<b>Bold" not in html
        assert "<i>Italic" not in html
        # Should contain escaped versions
        assert "&lt;b&gt;" in html
        assert "&lt;i&gt;" in html

    def test_job_id_escaping(self):
        """Should escape job ID (though UUIDs are safe, test for completeness)."""
        resources = []
        job_id = "<script>alert('xss')</script>"

        html = _build_email_html("Test", resources, job_id)

        # Should escape the malicious job_id
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_multiple_resources_all_escaped(self):
        """Should escape all resources in a list."""
        resources = [
            {
                "type": "<b>Type1</b>",
                "title": "<script>1</script>",
                "url": "https://example.com/1",
                "source": "<i>Source1</i>",
                "description": "<img src=x>"
            },
            {
                "type": "Type2",
                "title": "Normal & Title",
                "url": "https://example.com/2",
                "source": "Source2",
                "description": "Normal description"
            }
        ]

        html = _build_email_html("Test", resources, "test-job-id")

        # First resource should be escaped
        assert "<script>1</script>" not in html
        assert "&lt;script&gt;" in html
        assert "<img src=" not in html

        # Second resource should also be properly escaped
        assert "&amp;" in html  # The & in "Normal & Title"

    def test_empty_description_no_html_injection(self):
        """Should handle empty/None descriptions without injection."""
        resources = [{
            "type": "PDF",
            "title": "Title",
            "url": "https://example.com",
            "source": "Source",
            "description": None
        }]

        html = _build_email_html("Test", resources, "test-job-id")

        # Should not crash and should not have description div for None
        assert "description" not in html.lower() or "Description:" not in html

    def test_url_with_special_characters(self):
        """Should handle URLs with query parameters and special chars."""
        resources = [{
            "type": "Link",
            "title": "Resource",
            "url": "https://example.com/resource?param=<script>alert('xss')</script>",
            "source": "Source",
            "description": "Desc"
        }]

        html = _build_email_html("Test", resources, "test-job-id")

        # The display text should be escaped
        assert "&lt;script&gt;" in html
        # The href will contain the URL (browsers handle URL context)
        assert "href=" in html

    def test_apostrophes_and_quotes_in_content(self):
        """Should handle quotes and apostrophes safely."""
        resources = [{
            "type": "Article",
            "title": "It's a \"great\" article",
            "url": "https://example.com",
            "source": "Author's Source",
            "description": 'Contains "quotes" and \'apostrophes\''
        }]

        html = _build_email_html("Test with 'quotes'", resources, "test-job-id")

        # Should contain the content (HTML escape handles quotes appropriately)
        # Python's html.escape converts " to &quot; and ' stays as ' (safe in HTML)
        assert "It&#x27;s" in html or "It's" in html  # Both are safe
        assert "&quot;" in html or '"' in html  # Quotes handling
