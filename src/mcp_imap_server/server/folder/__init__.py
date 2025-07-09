"""Folder module for IMAP server."""

from .management import register_folder_management_tools
from .statistics import register_folder_statistics_tools
from .pagination import register_folder_pagination_tools

__all__ = [
    "register_folder_management_tools",
    "register_folder_pagination_tools",
    "register_folder_statistics_tools",
]
