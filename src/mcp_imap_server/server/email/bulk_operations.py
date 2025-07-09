"""Email bulk operations tools for IMAP server."""

import imaplib
from mcp.server.fastmcp import FastMCP
from ..state import get_state_or_error


def register_email_bulk_operations_tools(mcp: FastMCP):
    """Register email bulk operations tools with the MCP server."""

    @mcp.tool()
    async def bulk_mark_as_read(uids: list[int]):
        """
        Mark multiple emails as read using their UIDs.

        Args:
            uids: List of email UIDs to mark as read
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Mark as read using IMAP command
            state.mailbox.mail.store(uid_str, "+FLAGS", r"(\Seen)")

            return {
                "message": f"Successfully marked {len(uids)} emails as read",
                "uids": uids,
                "operation": "mark_as_read",
                "success_count": len(uids),
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to mark emails as read: {e!s}"

    @mcp.tool()
    async def bulk_mark_as_unread(uids: list[int]):
        """
        Mark multiple emails as unread using their UIDs.

        Args:
            uids: List of email UIDs to mark as unread
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Mark as unread using IMAP command
            state.mailbox.mail.store(uid_str, "-FLAGS", r"(\Seen)")
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to mark emails as unread: {e!s}"
        else:
            return {
                "message": f"Successfully marked {len(uids)} emails as unread",
                "uids": uids,
                "operation": "mark_as_unread",
                "success_count": len(uids),
            }

    @mcp.tool()
    async def bulk_delete_emails(uids: list[int], expunge: bool = False):
        """
        Delete multiple emails using their UIDs.

        Args:
            uids: List of email UIDs to delete
            expunge: If True, permanently remove emails; if False, just mark as deleted
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Mark as deleted using IMAP command
            state.mailbox.mail.store(uid_str, "+FLAGS", r"(\Deleted)")

            result = {
                "message": f"Successfully marked {len(uids)} emails for deletion",
                "uids": uids,
                "operation": "delete",
                "success_count": len(uids),
                "expunged": False,
            }

            # Expunge if requested
            if expunge:
                state.mailbox.mail.expunge()
                result["message"] = (
                    f"Successfully deleted {len(uids)} emails permanently"
                )
                result["expunged"] = True
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to delete emails: {e!s}"
        else:
            return result

    @mcp.tool()
    async def bulk_move_emails(uids: list[int], destination_folder: str):
        """
        Move multiple emails to another folder using their UIDs.

        Args:
            uids: List of email UIDs to move
            destination_folder: Name of the destination folder
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Copy to destination folder
            state.mailbox.mail.copy(uid_str, destination_folder)

            # Mark original messages as deleted
            state.mailbox.mail.store(uid_str, "+FLAGS", r"(\Deleted)")

            # Expunge to complete the move
            state.mailbox.mail.expunge()
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to move emails: {e!s}"
        else:
            return {
                "message": f"Successfully moved {len(uids)} emails to '{destination_folder}'",
                "uids": uids,
                "operation": "move",
                "destination_folder": destination_folder,
                "success_count": len(uids),
            }

    @mcp.tool()
    async def bulk_copy_emails(uids: list[int], destination_folder: str):
        """
        Copy multiple emails to another folder using their UIDs.

        Args:
            uids: List of email UIDs to copy
            destination_folder: Name of the destination folder
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if not uids:
            return "No UIDs provided."

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            # Copy to destination folder
            state.mailbox.mail.copy(uid_str, destination_folder)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to copy emails: {e!s}"
        else:
            return {
                "message": f"Successfully copied {len(uids)} emails to '{destination_folder}'",
                "uids": uids,
                "operation": "copy",
                "destination_folder": destination_folder,
                "success_count": len(uids),
            }

    @mcp.tool()
    async def bulk_flag_emails(
        uids: list[int],
        add_flags: list[str] | None = None,
        remove_flags: list[str] | None = None,
    ):
        """
        Add or remove flags from multiple emails using their UIDs.

        Args:
            uids: List of email UIDs to modify
            add_flags: List of flags to add (e.g., ['\\Flagged', '\\Important'])
            remove_flags: List of flags to remove (e.g., ['\\Seen', '\\Flagged'])
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if not uids:
            return "No UIDs provided."

        if not add_flags and not remove_flags:
            return "Please specify flags to add or remove."

        add_flags = add_flags or []
        remove_flags = remove_flags or []

        try:
            # Convert UIDs to comma-separated string
            uid_str = ",".join(str(uid) for uid in uids)

            operations = []

            # Add flags
            if add_flags:
                flags_str = " ".join(add_flags)
                state.mailbox.mail.store(uid_str, "+FLAGS", f"({flags_str})")
                operations.append(f"added flags: {', '.join(add_flags)}")

            # Remove flags
            if remove_flags:
                flags_str = " ".join(remove_flags)
                state.mailbox.mail.store(uid_str, "-FLAGS", f"({flags_str})")
                operations.append(f"removed flags: {', '.join(remove_flags)}")
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to modify email flags: {e!s}"
        else:
            return {
                "message": f"Successfully modified flags for {len(uids)} emails",
                "uids": uids,
                "operation": "flag_modification",
                "operations": operations,
                "success_count": len(uids),
                "added_flags": add_flags,
                "removed_flags": remove_flags,
            }
