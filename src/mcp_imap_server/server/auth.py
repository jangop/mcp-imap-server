"""Authentication tools for IMAP server."""

import imaplib
import ssl
from imap_tools import MailBox
from mcp.server.fastmcp import FastMCP

from ..shared.credentials import credential_manager


def register_auth_tools(mcp: FastMCP):
    """Register authentication-related tools with the MCP server."""

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

        try:
            state.mailbox = MailBox(server)
            state.mailbox.login(username, password)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Login failed: {e!s}"
        except (OSError, ssl.SSLError) as e:
            return f"Connection failed: {e!s}"
        else:
            return "Login successful."

    @mcp.tool()
    async def logout():
        """Log out of the IMAP server."""
        state = mcp.get_context().request_context.lifespan_context

        if not state.mailbox:
            return "Not logged in. Please login first."

        try:
            state.mailbox.logout()
            state.mailbox = None
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            # Still set mailbox to None even if logout fails
            state.mailbox = None
            return f"Logout completed with warning: {e!s}"
        else:
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
        try:
            credentials = credential_manager.get_account(account_name)

            if not credentials:
                return f"Account '{account_name}' not found. Use list_stored_accounts to see available accounts."

            state = mcp.get_context().request_context.lifespan_context

            state.mailbox = MailBox(credentials.server)
            state.mailbox.login(credentials.username, credentials.password)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Login failed for account '{account_name}': {e!s}"
        except (OSError, ssl.SSLError) as e:
            return f"Connection failed for account '{account_name}': {e!s}"
        else:
            return f"Login successful using stored account '{account_name}'."
