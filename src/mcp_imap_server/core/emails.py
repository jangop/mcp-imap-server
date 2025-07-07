"""Email management tools for IMAP server."""

from imap_tools import AND
from mcp.server.fastmcp import FastMCP
from .state import get_state_or_error


def register_email_tools(mcp: FastMCP):
    """Register email-related tools with the MCP server."""

    @mcp.tool()
    async def list_emails(list_unread_only: bool = False):
        """
        List emails in the current folder.

        Args:
            list_unread_only: If True, only list unread emails, otherwise list all emails.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if list_unread_only:
            # Only fetch unread emails
            messages = state.mailbox.fetch(AND("UNSEEN"))
        else:
            # Fetch all emails (don't use AND with empty criteria)
            messages = state.mailbox.fetch()

        return [
            {"uid": msg.uid, "from": msg.from_, "subject": msg.subject}
            for msg in messages
        ]

    @mcp.tool()
    async def filter_emails_by_sender(sender: str, list_unread_only: bool = False):
        """
        List emails from a specific sender.

        Args:
            sender: Email address of the sender to filter by.
            list_unread_only: If True, only show unread emails from this sender.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        criteria = [f'(FROM "{sender}")']
        if list_unread_only:
            criteria.append("UNSEEN")

        messages = state.mailbox.fetch(AND(*criteria))
        return [
            {"uid": msg.uid, "from": msg.from_, "subject": msg.subject}
            for msg in messages
        ]

    @mcp.tool()
    async def filter_emails_by_subject(subject: str, list_unread_only: bool = False):
        """
        List emails containing specific text in the subject.

        Args:
            subject: Text to search for in email subjects.
            list_unread_only: If True, only show unread emails with this subject.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        criteria = [f'(SUBJECT "{subject}")']
        if list_unread_only:
            criteria.append("UNSEEN")

        messages = state.mailbox.fetch(AND(*criteria))
        return [
            {"uid": msg.uid, "from": msg.from_, "subject": msg.subject}
            for msg in messages
        ]

    @mcp.tool()
    async def read_email(uid: str):
        """
        Read the content of a specific email.

        Args:
            uid: The UID of the email to read.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        for msg in state.mailbox.fetch(AND(uid=uid)):
            return {
                "from": msg.from_,
                "subject": msg.subject,
                "date": msg.date_str,
                "text": msg.text,
                "html": msg.html,
            }
        return "Email not found."

    @mcp.tool()
    async def mark_as_read(uid: str):
        """
        Mark an email as read.

        Args:
            uid: The UID of the email to mark as read.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        state.mailbox.flag(uid, r"\Seen", True)
        return f"Email {uid} marked as read."

    @mcp.tool()
    async def delete_email(uid: str):
        """
        Delete an email.

        Args:
            uid: The UID of the email to delete.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        state.mailbox.delete(uid)
        return f"Email {uid} deleted."
