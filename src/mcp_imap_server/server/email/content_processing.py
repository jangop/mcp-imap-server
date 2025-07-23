"""Email content processing and response formatting utilities."""

import re
from dataclasses import dataclass, asdict
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


@dataclass(frozen=True)
class AttachmentInfo:
    """Email attachment information."""

    filename: str
    content_type: str
    size: int


@dataclass(frozen=True)
class EmailObject:
    """Basic email object with headers and optional content."""

    uid: int
    from_: str
    subject: str
    date: str
    size: int
    flags: list[str]

    # Content fields (only present if headers_only=False)
    original_plaintext: str | None = None
    original_html: str | None = None
    markdown_from_html: str | None = None
    attachment_count: int | None = None


@dataclass(frozen=True)
class DetailedEmail:
    """Detailed email object with full metadata and content."""

    uid: int
    from_: str
    to: tuple[str, ...]
    cc: tuple[str, ...]
    bcc: tuple[str, ...]
    subject: str
    date: str
    size: int
    flags: list[str]
    attachment_count: int
    attachments: list[AttachmentInfo]

    # Content fields
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


# Global processor instance for backward compatibility
content_processor = EmailContentProcessor()


# Response formatting functions with dataclass support


def build_email_list(
    messages: list,
    headers_only: bool,
    content_format: ContentFormat,
) -> list[dict[str, Any]]:
    """
    Build a standardized list of email objects with optional content processing.

    Args:
        messages: List of email message objects from imap-tools
        headers_only: Whether to include content or just headers
        content_format: Content format preference

    Returns:
        List of formatted email dictionaries (for MCP compatibility)
    """
    email_objects = []

    for msg in messages:
        email_obj = _build_email_dataclass(msg, headers_only, content_format)
        email_objects.append(email_obj)

    # Convert dataclasses to dicts for MCP compatibility
    return [asdict(obj) for obj in email_objects]


def build_single_email(
    message, content_format: ContentFormat, include_attachments: bool = True
) -> dict[str, Any]:
    """
    Build a detailed single email response with full metadata.

    Args:
        message: Email message object from imap-tools
        content_format: Content format preference
        include_attachments: Whether to include attachment details

    Returns:
        Formatted email dictionary (for MCP compatibility)
    """
    # Process content
    content_fields = content_processor.process_email_content(
        text_content=message.text,
        html_content=message.html,
        content_format=content_format,
    )

    # Build attachment info
    attachments = []
    if include_attachments:
        for att in message.attachments:
            attachment_info = AttachmentInfo(
                filename=att.filename or "unnamed",
                content_type=att.content_type,
                size=len(att.payload) if att.payload else 0,
            )
            attachments.append(attachment_info)

    # Create detailed email dataclass
    detailed_email = DetailedEmail(
        uid=message.uid,
        from_=message.from_,
        to=message.to,
        cc=message.cc,
        bcc=message.bcc,
        subject=message.subject,
        date=message.date_str,
        size=message.size,
        flags=list(message.flags),
        attachment_count=len(message.attachments),
        attachments=attachments,
        **content_fields,  # Unpack content fields
    )

    # Convert to dict for MCP compatibility
    return asdict(detailed_email)


def build_search_results(
    messages: list,
    headers_only: bool,
    content_format: ContentFormat,
    truncate_content: bool = True,
) -> list[dict[str, Any]]:
    """
    Build search results with optional content truncation for better performance.

    Args:
        messages: List of email message objects
        headers_only: Whether to include content
        content_format: Content format preference
        truncate_content: Whether to truncate long content (default: True)

    Returns:
        List of formatted email dictionaries optimized for search results
    """
    email_objects = []

    for msg in messages:
        email_obj = _build_email_dataclass(msg, headers_only, content_format)
        email_objects.append(email_obj)

    # Convert to dicts and optionally truncate content
    results = [asdict(obj) for obj in email_objects]

    if not headers_only and truncate_content:
        for result in results:
            truncate_content_fields(result)

    return results


def build_email_object(
    msg, headers_only: bool, content_format: ContentFormat
) -> dict[str, Any]:
    """Build a basic email object with optional content processing."""
    email_obj = _build_email_dataclass(msg, headers_only, content_format)
    return asdict(email_obj)


def _build_email_dataclass(
    msg, headers_only: bool, content_format: ContentFormat
) -> EmailObject:
    """Build an EmailObject dataclass from message data."""
    # Start with basic fields
    email_data = {
        "uid": msg.uid,
        "from_": msg.from_,
        "subject": msg.subject,
        "date": msg.date_str,
        "size": msg.size,
        "flags": list(msg.flags),
    }

    if not headers_only:
        # Process content and add to email data
        content_fields = content_processor.process_email_content(
            text_content=msg.text,
            html_content=msg.html,
            content_format=content_format,
        )
        email_data.update(content_fields)
        email_data["attachment_count"] = len(msg.attachments)

    return EmailObject(**email_data)


def truncate_content_fields(email_obj: dict[str, Any], max_length: int = 200) -> None:
    """Truncate content fields in-place for search results."""
    content_fields = ["original_plaintext", "original_html", "markdown_from_html"]

    for field_name in content_fields:
        if email_obj.get(field_name):
            content = email_obj[field_name]
            if len(content) > max_length:
                email_obj[field_name] = content[:max_length] + "..."
