"""Main IMAP MCP server setup and lifecycle management."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP

from .core.state import ImapState
from .core.auth import register_auth_tools
from .core.folders import register_folder_tools
from .core.emails import register_email_tools
from .core.compose import register_compose_tools


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
    register_folder_tools(mcp)
    register_email_tools(mcp)
    register_compose_tools(mcp)

    return mcp


def main():
    """Run the IMAP server."""
    server = create_server()
    server.run()
