"""Folder pagination tools for IMAP server."""

import imaplib
from imap_tools.query import OR
from mcp.server.fastmcp import FastMCP
from ..state import get_mailbox
from ..email.content_processing import ContentFormat, build_email_list


def register_folder_pagination_tools(mcp: FastMCP):
    """Register folder pagination tools with the MCP server."""

    @mcp.tool()
    async def get_emails_paginated(
        page: int = 1,
        page_size: int = 20,
        folder_name: str = "",
        headers_only: bool = True,
        content_format: ContentFormat = ContentFormat.DEFAULT,
    ):
        """
        Get emails with pagination support.

        Args:
            page: Page number (1-based)
            page_size: Number of emails per page
            folder_name: Name of the folder (empty for current folder)
            headers_only: If True, only fetch headers for faster loading
            content_format: How to format email content - "default" (smart: meaningful plaintext or HTML→markdown),
                          "original_plaintext" (raw text), "original_html" (raw HTML),
                          "markdown_from_html" (clean markdown from HTML), "all" (all formats)
        """
        mailbox = get_mailbox(mcp.get_context())

        if page < 1:
            return "Page number must be 1 or greater."

        if page_size < 1 or page_size > 100:
            return "Page size must be between 1 and 100."

        try:
            # Use current folder if none specified
            original_folder = mailbox.folder.get() or "INBOX"
            if folder_name and folder_name != str(original_folder):
                mailbox.folder.set(folder_name)
            else:
                folder_name = str(original_folder)

            # Get total count first - use uids() to get all UIDs
            all_uids = mailbox.uids()
            total_emails = len(all_uids)

            # Calculate pagination
            total_pages = (
                (total_emails + page_size - 1) // page_size if total_emails > 0 else 1
            )
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_emails)

            if start_idx >= total_emails:
                return {
                    "message": f"Page {page} is beyond available data",
                    "folder": folder_name,
                    "page": page,
                    "page_size": page_size,
                    "total_emails": total_emails,
                    "total_pages": total_pages,
                    "emails": [],
                }

            # Get UIDs for this page
            page_uids = all_uids[start_idx:end_idx]

            # Handle case where no UIDs are available for this page
            if not page_uids:
                return {
                    "message": f"Page {page} is beyond available data",
                    "folder": folder_name,
                    "page": page,
                    "page_size": page_size,
                    "total_emails": total_emails,
                    "total_pages": total_pages,
                    "emails": [],
                }

            # Fetch messages for this page using UID criteria
            # Convert UIDs to comma-separated format for UID search
            uid_list = ",".join(str(uid) for uid in page_uids)
            uid_criteria = f"UID {uid_list}"
            page_messages = list(mailbox.fetch(uid_criteria, headers_only=headers_only))

            # Format results using centralized formatting functions
            results = build_email_list(page_messages, headers_only, content_format)

            # Restore original folder if we changed it
            if folder_name != original_folder:
                mailbox.folder.set(original_folder)

            return {
                "message": f"Page {page} of {total_pages} from folder '{folder_name}'",
                "folder": folder_name,
                "page": page,
                "page_size": page_size,
                "total_emails": total_emails,
                "total_pages": total_pages,
                "has_previous": page > 1,
                "has_next": page < total_pages,
                "start_index": start_idx + 1,
                "end_index": end_idx,
                "content_format": content_format,
                "emails": results,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get paginated emails: {e!s}"

    @mcp.tool()
    async def search_emails_paginated(
        search_criteria: str,
        page: int = 1,
        page_size: int = 20,
        folder_name: str = "",
        headers_only: bool = True,
        content_format: ContentFormat = ContentFormat.DEFAULT,
    ):
        """
        Search emails with pagination support.

        Args:
            search_criteria: Search text (searches in subject and from fields)
            page: Page number (1-based)
            page_size: Number of emails per page
            folder_name: Name of the folder (empty for current folder)
            headers_only: If True, only fetch headers for faster loading
            content_format: How to format email content - "default" (smart: meaningful plaintext or HTML→markdown),
                          "original_plaintext" (raw text), "original_html" (raw HTML),
                          "markdown_from_html" (clean markdown from HTML), "all" (all formats)
        """
        mailbox = get_mailbox(mcp.get_context())

        if page < 1:
            return "Page number must be 1 or greater."

        if page_size < 1 or page_size > 100:
            return "Page size must be between 1 and 100."

        try:
            # Use current folder if none specified
            original_folder = mailbox.folder.get() or "INBOX"
            if folder_name and folder_name != str(original_folder):
                mailbox.folder.set(folder_name)
            else:
                folder_name = str(original_folder)

            # Create search criteria - search in both subject and from fields
            criteria = OR(subject=search_criteria, from_=search_criteria)

            # Get all matching UIDs
            matching_messages = list(mailbox.fetch(criteria, headers_only=True))
            total_matches = len(matching_messages)

            # Calculate pagination
            total_pages = (
                (total_matches + page_size - 1) // page_size if total_matches > 0 else 1
            )
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_matches)

            if start_idx >= total_matches:
                return {
                    "message": f"Page {page} is beyond available search results",
                    "folder": folder_name,
                    "search_criteria": search_criteria,
                    "page": page,
                    "page_size": page_size,
                    "total_matches": total_matches,
                    "total_pages": total_pages,
                    "emails": [],
                }

            # Get messages for this page
            page_messages = matching_messages[start_idx:end_idx]

            # Format results using centralized formatting functions
            results = build_email_list(page_messages, headers_only, content_format)

            # Restore original folder if we changed it
            if folder_name != original_folder:
                mailbox.folder.set(original_folder)

            return {
                "message": f"Search results page {page} of {total_pages} for '{search_criteria}'",
                "folder": folder_name,
                "search_criteria": search_criteria,
                "page": page,
                "page_size": page_size,
                "total_matches": total_matches,
                "total_pages": total_pages,
                "has_previous": page > 1,
                "has_next": page < total_pages,
                "start_index": start_idx + 1,
                "end_index": end_idx,
                "content_format": content_format,
                "emails": results,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to search emails with pagination: {e!s}"

    @mcp.tool()
    async def get_emails_by_flag_paginated(
        flag: str,
        page: int = 1,
        page_size: int = 20,
        folder_name: str = "",
        headers_only: bool = True,
        content_format: ContentFormat = ContentFormat.DEFAULT,
    ):
        """
        Get emails filtered by flag with pagination support.

        Args:
            flag: Email flag to filter by (SEEN, UNSEEN, FLAGGED, UNFLAGGED, etc.)
            page: Page number (1-based)
            page_size: Number of emails per page
            folder_name: Name of the folder (empty for current folder)
            headers_only: If True, only fetch headers for faster loading
            content_format: How to format email content - "default" (smart: meaningful plaintext or HTML→markdown),
                          "original_plaintext" (raw text), "original_html" (raw HTML),
                          "markdown_from_html" (clean markdown from HTML), "all" (all formats)
        """
        mailbox = get_mailbox(mcp.get_context())

        if page < 1:
            return "Page number must be 1 or greater."

        if page_size < 1 or page_size > 100:
            return "Page size must be between 1 and 100."

        # Map flag names to search criteria
        flag_mapping = {
            "SEEN": "SEEN",
            "UNSEEN": "UNSEEN",
            "FLAGGED": "FLAGGED",
            "UNFLAGGED": "UNFLAGGED",
            "DELETED": "DELETED",
            "UNDELETED": "UNDELETED",
            "ANSWERED": "ANSWERED",
            "UNANSWERED": "UNANSWERED",
            "DRAFT": "DRAFT",
            "UNDRAFT": "UNDRAFT",
        }

        flag_upper = flag.upper()
        if flag_upper not in flag_mapping:
            return f"Unknown flag '{flag}'. Supported flags: {', '.join(flag_mapping.keys())}"

        try:
            # Use current folder if none specified
            original_folder = mailbox.folder.get() or "INBOX"
            if folder_name and folder_name != str(original_folder):
                mailbox.folder.set(folder_name)
            else:
                folder_name = str(original_folder)

            # Create search criteria using the flag string directly
            criteria = flag_mapping[flag_upper]

            # Get all matching messages
            matching_messages = list(mailbox.fetch(criteria, headers_only=True))
            total_matches = len(matching_messages)

            # Calculate pagination
            total_pages = (
                (total_matches + page_size - 1) // page_size if total_matches > 0 else 1
            )
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_matches)

            if start_idx >= total_matches:
                return {
                    "message": f"Page {page} is beyond available results for flag '{flag}'",
                    "folder": folder_name,
                    "flag": flag,
                    "page": page,
                    "page_size": page_size,
                    "total_matches": total_matches,
                    "total_pages": total_pages,
                    "emails": [],
                }

            # Get messages for this page
            page_messages = matching_messages[start_idx:end_idx]

            # Format results using centralized formatting functions
            results = build_email_list(page_messages, headers_only, content_format)

            # Restore original folder if we changed it
            if folder_name != original_folder:
                mailbox.folder.set(original_folder)

            return {
                "message": f"Page {page} of {total_pages} for emails with flag '{flag}'",
                "folder": folder_name,
                "flag": flag,
                "page": page,
                "page_size": page_size,
                "total_matches": total_matches,
                "total_pages": total_pages,
                "has_previous": page > 1,
                "has_next": page < total_pages,
                "start_index": start_idx + 1,
                "end_index": end_idx,
                "content_format": content_format,
                "emails": results,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get emails by flag with pagination: {e!s}"
