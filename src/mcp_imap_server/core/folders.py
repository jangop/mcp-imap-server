"""Folder management tools for IMAP server."""

from mcp.server.fastmcp import FastMCP
from .state import get_state_or_error


def register_folder_tools(mcp: FastMCP):
    """Register folder-related tools with the MCP server."""

    @mcp.tool()
    async def list_folders():
        """List all folders in the mailbox."""
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        folders = state.mailbox.folder.list()
        return [folder.name for folder in folders]

    @mcp.tool()
    async def select_folder(folder: str):
        """
        Select a folder to work with.

        Args:
            folder: The name of the folder to select.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        state.mailbox.folder.set(folder)
        return f"Folder '{folder}' selected."

    @mcp.tool()
    async def move_email(uid: str, destination_folder: str):
        """
        Move an email to a specified folder.

        Args:
            uid: The UID of the email to move.
            destination_folder: The name of the destination folder to move the email to.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Check if destination folder exists, create it if it doesn't
            if not state.mailbox.folder.exists(destination_folder):
                state.mailbox.folder.create(destination_folder)

            # Move the email to the destination folder
            state.mailbox.move(uid, destination_folder)
            return f"Email {uid} moved to folder '{destination_folder}'."
        except Exception as e:
            return f"Failed to move email {uid}: {str(e)}"
