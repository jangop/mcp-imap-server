"""IMAP server for the Model Context Protocol."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass

from imap_tools import MailBox, AND
from mcp.server.fastmcp import FastMCP

from .credentials import credential_manager


@dataclass
class ImapState:
    """State for the IMAP server."""

    mailbox: MailBox | None = None


@asynccontextmanager
async def imap_lifespan(server: FastMCP) -> AsyncIterator[ImapState]:
    """Manage IMAP server lifecycle."""
    state = ImapState()
    try:
        yield state
    finally:
        if state.mailbox:
            state.mailbox.logout()


# Create the MCP server with lifespan management
mcp = FastMCP("IMAP Server", lifespan=imap_lifespan)


@mcp.tool()
async def login(username: str, password: str, server: str):
    """
    Log in to an IMAP server.

    Args:
        username: IMAP username
        password: IMAP password
        server: IMAP server hostname
    """
    state = mcp.get_context().request_context.lifespan_context

    state.mailbox = MailBox(server)
    state.mailbox.login(username, password)
    return "Login successful."


@mcp.tool()
async def list_folders():
    """List all folders in the mailbox."""
    state = mcp.get_context().request_context.lifespan_context
    if not state.mailbox:
        return "Not logged in. Please login first."

    folders = state.mailbox.folder.list()
    return [folder.name for folder in folders]


@mcp.tool()
async def select_folder(folder: str):
    """
    Select a folder to work with.

    Args:
        folder: The name of the folder to select.
    """
    state = mcp.get_context().request_context.lifespan_context
    if not state.mailbox:
        return "Not logged in. Please login first."

    state.mailbox.folder.set(folder)
    return f"Folder '{folder}' selected."


@mcp.tool()
async def list_emails(list_unread_only: bool = False):
    """
    List emails in the current folder.

    Args:
        list_unread_only: If True, only list unread emails, otherwise list all emails.
    """
    state = mcp.get_context().request_context.lifespan_context
    if not state.mailbox:
        return "Not logged in. Please login first."

    if list_unread_only:
        # Only fetch unread emails
        messages = state.mailbox.fetch(AND("UNSEEN"))
    else:
        # Fetch all emails (don't use AND with empty criteria)
        messages = state.mailbox.fetch()

    return [
        {"uid": msg.uid, "from": msg.from_, "subject": msg.subject} for msg in messages
    ]


@mcp.tool()
async def filter_emails_by_sender(sender: str, list_unread_only: bool = False):
    """
    List emails from a specific sender.

    Args:
        sender: Email address of the sender to filter by.
        list_unread_only: If True, only show unread emails from this sender.
    """
    state = mcp.get_context().request_context.lifespan_context
    if not state.mailbox:
        return "Not logged in. Please login first."

    criteria = [f'(FROM "{sender}")']
    if list_unread_only:
        criteria.append("UNSEEN")

    messages = state.mailbox.fetch(AND(*criteria))
    return [
        {"uid": msg.uid, "from": msg.from_, "subject": msg.subject} for msg in messages
    ]


@mcp.tool()
async def filter_emails_by_subject(subject: str, list_unread_only: bool = False):
    """
    List emails containing specific text in the subject.

    Args:
        subject: Text to search for in email subjects.
        list_unread_only: If True, only show unread emails with this subject.
    """
    state = mcp.get_context().request_context.lifespan_context
    if not state.mailbox:
        return "Not logged in. Please login first."

    criteria = [f'(SUBJECT "{subject}")']
    if list_unread_only:
        criteria.append("UNSEEN")

    messages = state.mailbox.fetch(AND(*criteria))
    return [
        {"uid": msg.uid, "from": msg.from_, "subject": msg.subject} for msg in messages
    ]


@mcp.tool()
async def read_email(uid: str):
    """
    Read the content of a specific email.

    Args:
        uid: The UID of the email to read.
    """
    state = mcp.get_context().request_context.lifespan_context
    if not state.mailbox:
        return "Not logged in. Please login first."

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
    state = mcp.get_context().request_context.lifespan_context
    if not state.mailbox:
        return "Not logged in. Please login first."

    state.mailbox.flag(uid, r"\Seen", True)
    return f"Email {uid} marked as read."


@mcp.tool()
async def delete_email(uid: str):
    """
    Delete an email.

    Args:
        uid: The UID of the email to delete.
    """
    state = mcp.get_context().request_context.lifespan_context
    if not state.mailbox:
        return "Not logged in. Please login first."

    state.mailbox.delete(uid)
    return f"Email {uid} deleted."


@mcp.tool()
async def logout():
    """Log out of the IMAP server."""
    state = mcp.get_context().request_context.lifespan_context
    if not state.mailbox:
        return "Not logged in. Please login first."

    state.mailbox.logout()
    state.mailbox = None
    return "Logout successful."


@mcp.tool()
async def list_stored_accounts():
    """List all stored account names."""
    accounts = credential_manager.list_accounts()
    if not accounts:
        return "No accounts stored."
    return f"Stored accounts: {', '.join(accounts)}"


@mcp.tool()
async def login_with_stored_account(account_name: str):
    """
    Log in using stored account credentials.

    Args:
        account_name: The name of the stored account to use for login
    """
    credentials = credential_manager.get_account(account_name)
    if not credentials:
        return f"Account '{account_name}' not found. Use list_stored_accounts to see available accounts."

    state = mcp.get_context().request_context.lifespan_context

    state.mailbox = MailBox(credentials.server)
    state.mailbox.login(credentials.username, credentials.password)
    return f"Login successful using stored account '{account_name}'."


def main():
    """Run the IMAP server."""
    mcp.run()


if __name__ == "__main__":
    main()
