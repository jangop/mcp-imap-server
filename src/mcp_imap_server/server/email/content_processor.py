"""Email content processing utilities for intelligent format selection."""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from html_to_markdown import convert_to_markdown


class ContentFormat(StrEnum):
    """Content format options for email processing."""

    DEFAULT = "default"
    ORIGINAL_PLAINTEXT = "original_plaintext"
    ORIGINAL_HTML = "original_html"
    MARKDOWN_FROM_HTML = "markdown_from_html"
    ALL = "all"


@dataclass
class ProcessedEmailContent:
    """Container for processed email content with explicit field names."""

    original_plaintext: str | None = None
    original_html: str | None = None
    markdown_from_html: str | None = None


class EmailContentProcessor:
    """Processes email content with intelligent format selection."""

    def __init__(self):
        """Initialize with optimized HTML-to-markdown settings for emails."""
        self.markdown_options = {
            "heading_style": "atx",
            "extract_metadata": False,
            "convert_as_inline": False,
            "escape_asterisks": True,
            "escape_underscores": True,
            "wrap": True,
            "wrap_width": 80,
            "strip_newlines": True,
            "autolinks": True,
        }

    def process_email_content(
        self,
        text_content: str | None,
        html_content: str | None,
        content_format: ContentFormat = ContentFormat.DEFAULT,
    ) -> dict[str, Any]:
        """
        Process email content based on format preference.

        Args:
            text_content: Original plaintext content from email
            html_content: Original HTML content from email
            content_format: Desired format from ContentFormat enum

        Returns:
            Dict containing only the requested content fields with explicit names
        """
        result = {}

        if content_format == ContentFormat.DEFAULT:
            # Default: prefer plaintext, fallback to converted HTML
            if text_content and self._is_meaningful_content(text_content):
                result["original_plaintext"] = text_content
            elif html_content:
                result["markdown_from_html"] = self._convert_html_to_markdown(
                    html_content
                )
            else:
                result["original_plaintext"] = text_content or ""

        elif content_format == ContentFormat.ORIGINAL_PLAINTEXT:
            result["original_plaintext"] = text_content or ""

        elif content_format == ContentFormat.ORIGINAL_HTML:
            result["original_html"] = html_content or ""

        elif content_format == ContentFormat.MARKDOWN_FROM_HTML:
            if html_content:
                result["markdown_from_html"] = self._convert_html_to_markdown(
                    html_content
                )
            else:
                result["markdown_from_html"] = ""

        elif content_format == ContentFormat.ALL:
            result["original_plaintext"] = text_content or ""
            result["original_html"] = html_content or ""
            if html_content:
                result["markdown_from_html"] = self._convert_html_to_markdown(
                    html_content
                )

        return result

    def _convert_html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to clean markdown using html-to-markdown library."""
        try:
            if not html_content or not html_content.strip():
                return ""

            markdown = convert_to_markdown(html_content, **self.markdown_options)
            return markdown.strip()

        except Exception:
            # Fallback: return cleaned HTML if conversion fails
            return self._strip_html_tags(html_content)

    def _is_meaningful_content(self, text_content: str) -> bool:
        """
        Check if plaintext content is meaningful (not just a stub).

        Returns False if content appears to be a stub that directs users to HTML version.
        """
        if not text_content:
            return False

        cleaned = text_content.strip().lower()

        # Check for common stub phrases
        stub_indicators = [
            "view this email in your browser",
            "click here to view",
            "html version",
            "view online",
            "display problems",
            "view in browser",
            "view web version",
            "view email online",
            "click to view online",
        ]

        # If content is very short and contains stub indicators
        if len(cleaned) < 200:
            for indicator in stub_indicators:
                if indicator in cleaned:
                    return False

        # If content is extremely short (likely just headers/footers)
        if len(cleaned) < 50:
            return False

        return True

    def _strip_html_tags(self, html_content: str) -> str:
        """Strip HTML tags and return clean text as fallback."""
        if not html_content:
            return ""

        # Remove HTML tags
        clean_text = re.sub(r"<[^>]+>", "", html_content)

        # Normalize whitespace
        clean_text = re.sub(r"\s+", " ", clean_text)

        return clean_text.strip()


# Global processor instance
content_processor = EmailContentProcessor()
