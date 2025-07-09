"""State management for the IMAP server."""

from dataclasses import dataclass
from imap_tools import MailBox


@dataclass
class ImapState:
    """State for the IMAP server."""

    mailbox: MailBox | None = None


def get_state_or_error(context):
    """Get the IMAP state from context or return error message."""
    state = context.request_context.lifespan_context
    if not state.mailbox:
        return None, "Not logged in. Please login first."
    return state, None
