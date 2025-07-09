"""Email module for IMAP server."""

from .search import register_email_search_tools
from .attachments import register_email_attachment_tools
from .bulk_operations import register_email_bulk_operations_tools
from .basic_operations import register_email_basic_operations_tools

__all__ = [
    "register_email_attachment_tools",
    "register_email_basic_operations_tools",
    "register_email_bulk_operations_tools",
    "register_email_search_tools",
]
