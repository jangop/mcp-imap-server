"""Folder pagination tools for IMAP server."""

import imaplib
from imap_tools import AND
from mcp.server.fastmcp import FastMCP
from ..state import get_state_or_error


def register_folder_pagination_tools(mcp: FastMCP):
    """Register folder pagination tools with the MCP server."""

    @mcp.tool()
    async def get_emails_paginated(
        page: int = 1,
        page_size: int = 20,
        folder_name: str = "",
        headers_only: bool = True,
    ):
        """
        Get emails with pagination support.

        Args:
            page: Page number (1-based)
            page_size: Number of emails per page
            folder_name: Name of the folder (empty for current folder)
            headers_only: If True, only fetch headers for faster loading
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if page < 1:
            return "Page number must be 1 or greater."

        if page_size < 1 or page_size > 100:
            return "Page size must be between 1 and 100."

        try:
            # Use current folder if none specified
            original_folder = state.mailbox.folder
            if folder_name and folder_name != original_folder:
                state.mailbox.folder.set(folder_name)
            else:
                folder_name = original_folder

            # Get total count first
            all_uids = list(state.mailbox.uids())
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

            # Fetch messages for this page
            page_messages = list(
                state.mailbox.fetch(page_uids, headers_only=headers_only)
            )

            # Format results
            results = []
            for msg in page_messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "flags": list(msg.flags),
                }
                if not headers_only:
                    result.update(
                        {
                            "text": msg.text,
                            "html": msg.html,
                            "attachment_count": len(msg.attachments),
                        }
                    )
                results.append(result)

            # Restore original folder if we changed it
            if folder_name != original_folder:
                state.mailbox.folder.set(original_folder)

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
    ):
        """
        Search emails with pagination support.

        Args:
            search_criteria: Search text (searches in subject and from fields)
            page: Page number (1-based)
            page_size: Number of emails per page
            folder_name: Name of the folder (empty for current folder)
            headers_only: If True, only fetch headers for faster loading
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if page < 1:
            return "Page number must be 1 or greater."

        if page_size < 1 or page_size > 100:
            return "Page size must be between 1 and 100."

        try:
            # Use current folder if none specified
            original_folder = state.mailbox.folder
            if folder_name and folder_name != original_folder:
                state.mailbox.folder.set(folder_name)
            else:
                folder_name = original_folder

            # Create search criteria - search in both subject and from fields
            from imap_tools import OR

            criteria = OR(subject=search_criteria, from_=search_criteria)

            # Get all matching UIDs
            matching_messages = list(state.mailbox.fetch(criteria, headers_only=True))
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

            # Format results
            results = []
            for msg in page_messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "flags": list(msg.flags),
                }
                if not headers_only:
                    result.update(
                        {
                            "text": msg.text,
                            "html": msg.html,
                            "attachment_count": len(msg.attachments),
                        }
                    )
                results.append(result)

            # Restore original folder if we changed it
            if folder_name != original_folder:
                state.mailbox.folder.set(original_folder)

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
    ):
        """
        Get emails filtered by flag with pagination support.

        Args:
            flag: Email flag to filter by (SEEN, UNSEEN, FLAGGED, UNFLAGGED, etc.)
            page: Page number (1-based)
            page_size: Number of emails per page
            folder_name: Name of the folder (empty for current folder)
            headers_only: If True, only fetch headers for faster loading
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if page < 1:
            return "Page number must be 1 or greater."

        if page_size < 1 or page_size > 100:
            return "Page size must be between 1 and 100."

        # Map flag names to search criteria
        flag_mapping = {
            "SEEN": {"seen": True},
            "UNSEEN": {"seen": False},
            "FLAGGED": {"flagged": True},
            "UNFLAGGED": {"flagged": False},
            "DELETED": {"deleted": True},
            "UNDELETED": {"deleted": False},
            "ANSWERED": {"answered": True},
            "UNANSWERED": {"answered": False},
            "DRAFT": {"draft": True},
            "UNDRAFT": {"draft": False},
        }

        flag_upper = flag.upper()
        if flag_upper not in flag_mapping:
            return f"Unknown flag '{flag}'. Supported flags: {', '.join(flag_mapping.keys())}"

        try:
            # Use current folder if none specified
            original_folder = state.mailbox.folder
            if folder_name and folder_name != original_folder:
                state.mailbox.folder.set(folder_name)
            else:
                folder_name = original_folder

            # Create search criteria
            criteria = AND(**flag_mapping[flag_upper])

            # Get all matching messages
            matching_messages = list(state.mailbox.fetch(criteria, headers_only=True))
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

            # Format results
            results = []
            for msg in page_messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "flags": list(msg.flags),
                }
                if not headers_only:
                    result.update(
                        {
                            "text": msg.text,
                            "html": msg.html,
                            "attachment_count": len(msg.attachments),
                        }
                    )
                results.append(result)

            # Restore original folder if we changed it
            if folder_name != original_folder:
                state.mailbox.folder.set(original_folder)

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
                "emails": results,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get emails by flag with pagination: {e!s}"
