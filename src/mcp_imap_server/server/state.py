"""State management for the IMAP server."""

from dataclasses import dataclass
from typing import cast
from imap_tools.mailbox import MailBox
from mcp.server.fastmcp.server import Context
from mcp.server.session import ServerSession
from starlette.requests import Request


class NotLoggedInError(RuntimeError):
    """Raised when trying to access mailbox without being logged in."""

    def __init__(self):
        super().__init__("Not logged in. Please login first.")


@dataclass
class ImapState:
    """State for the IMAP server."""

    mailbox: MailBox | None = None


def get_mailbox(context: Context[ServerSession, object, Request]) -> MailBox:
    """Get the mailbox from context or raise NotLoggedInError if not logged in."""
    state = cast("ImapState", context.request_context.lifespan_context)
    if not state.mailbox:
        raise NotLoggedInError()
    return state.mailbox
