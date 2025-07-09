"""Main IMAP MCP server setup and lifecycle management."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP

from .state import ImapState
from .auth import register_auth_tools
from .folder.management import register_folder_management_tools
from .folder.statistics import register_folder_statistics_tools
from .folder.pagination import register_folder_pagination_tools
from .email.basic_operations import register_email_basic_operations_tools
from .email.bulk_operations import register_email_bulk_operations_tools
from .email.attachments import register_email_attachment_tools
from .email.search import register_email_search_tools
from .compose import register_compose_tools


@asynccontextmanager
async def imap_lifespan(server: FastMCP) -> AsyncIterator[ImapState]:
    """Manage IMAP server lifecycle."""
    state = ImapState()
    try:
        yield state
    finally:
        if state.mailbox:
            state.mailbox.logout()


def create_server() -> FastMCP:
    """Create and configure the MCP IMAP server."""
    # Create the MCP server with lifespan management
    mcp = FastMCP("IMAP Server", lifespan=imap_lifespan)

    # Register all tool modules
    register_auth_tools(mcp)
    register_folder_management_tools(mcp)
    register_folder_statistics_tools(mcp)
    register_folder_pagination_tools(mcp)
    register_email_basic_operations_tools(mcp)
    register_email_bulk_operations_tools(mcp)
    register_email_attachment_tools(mcp)
    register_email_search_tools(mcp)
    register_compose_tools(mcp)

    return mcp


def main():
    """Run the IMAP server."""
    server = create_server()
    server.run()
