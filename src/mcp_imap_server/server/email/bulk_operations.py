"""Email bulk operations tools for IMAP server."""

import imaplib
from typing import Any
from mcp.server.fastmcp import FastMCP
from ..state import get_mailbox


def register_email_bulk_operations_tools(mcp: FastMCP):
    """Register email bulk operations tools with the MCP server."""

    @mcp.tool()
    async def bulk_mark_as_read(uids: list[int]) -> dict[str, Any] | str:
        """
        Mark multiple emails as read using their UIDs.

        Args:
            uids: List of email UIDs to mark as read
        """
        mailbox = get_mailbox(mcp.get_context())

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Mark as read using the flag method
            mailbox.flag(uid_str, r"\Seen", True)

            return {
                "message": f"Successfully marked {len(uids)} emails as read",
                "uids": uids,
                "operation": "mark_as_read",
                "success_count": len(uids),
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to mark emails as read: {e!s}"

    @mcp.tool()
    async def bulk_mark_as_unread(uids: list[int]) -> dict[str, Any] | str:
        """
        Mark multiple emails as unread using their UIDs.

        Args:
            uids: List of email UIDs to mark as unread
        """
        mailbox = get_mailbox(mcp.get_context())

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Mark as unread using the flag method
            mailbox.flag(uid_str, r"\Seen", False)

            return {
                "message": f"Successfully marked {len(uids)} emails as unread",
                "uids": uids,
                "operation": "mark_as_unread",
                "success_count": len(uids),
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to mark emails as unread: {e!s}"

    @mcp.tool()
    async def bulk_delete_emails(uids: list[int]) -> dict[str, Any] | str:
        """
        Delete multiple emails using their UIDs.

        Args:
            uids: List of email UIDs to delete
        """
        mailbox = get_mailbox(mcp.get_context())

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Mark as deleted using the underlying IMAP client
            mailbox.client.uid("STORE", uid_str, "+FLAGS", r"(\Deleted)")
            mailbox.expunge()

            return {
                "message": f"Successfully deleted {len(uids)} emails",
                "uids": uids,
                "operation": "delete",
                "success_count": len(uids),
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to delete emails: {e!s}"

    @mcp.tool()
    async def bulk_copy_emails(
        uids: list[int], destination_folder: str
    ) -> dict[str, Any] | str:
        """
        Copy multiple emails to another folder using their UIDs.

        Args:
            uids: List of email UIDs to copy
            destination_folder: Destination folder name
        """
        mailbox = get_mailbox(mcp.get_context())

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Copy emails to destination folder
            mailbox.copy(uid_str, destination_folder)

            return {
                "message": f"Successfully copied {len(uids)} emails to '{destination_folder}'",
                "uids": uids,
                "destination_folder": destination_folder,
                "operation": "copy",
                "success_count": len(uids),
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to copy emails: {e!s}"

    @mcp.tool()
    async def bulk_move_emails(
        uids: list[int], destination_folder: str
    ) -> dict[str, Any] | str:
        """
        Move multiple emails to another folder using their UIDs.

        Args:
            uids: List of email UIDs to move
            destination_folder: Destination folder name
        """
        mailbox = get_mailbox(mcp.get_context())

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Move emails to destination folder
            mailbox.move(uid_str, destination_folder)

            return {
                "message": f"Successfully moved {len(uids)} emails to '{destination_folder}'",
                "uids": uids,
                "destination_folder": destination_folder,
                "operation": "move",
                "success_count": len(uids),
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to move emails: {e!s}"

    @mcp.tool()
    async def bulk_flag_emails(
        uids: list[int], flag: str, value: bool = True
    ) -> dict[str, Any] | str:
        """
        Set or unset flags for multiple emails using their UIDs.

        Args:
            uids: List of email UIDs to flag
            flag: Flag to set/unset (e.g., "\\Seen", "\\Flagged", "\\Deleted")
            value: True to set flag, False to unset flag
        """
        mailbox = get_mailbox(mcp.get_context())

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Set or unset flag
            mailbox.flag(uid_str, flag, value)

            action = "set" if value else "unset"
            return {
                "message": f"Successfully {action} flag '{flag}' for {len(uids)} emails",
                "uids": uids,
                "flag": flag,
                "value": value,
                "operation": f"flag_{action}",
                "success_count": len(uids),
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to flag emails: {e!s}"
