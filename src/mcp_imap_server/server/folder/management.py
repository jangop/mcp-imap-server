"""Folder management tools for IMAP server."""

import imaplib
from mcp.server.fastmcp import FastMCP
from ..state import get_mailbox


def register_folder_management_tools(mcp: FastMCP):
    """Register folder management tools with the MCP server."""

    @mcp.tool()
    async def list_folders():
        """
        List all available folders/mailboxes.
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Get list of folders
            folder_list = []
            try:
                # Use the folder manager to get folder information
                folder_manager = mailbox.folder
                # Get all folder information - this should return folder objects
                folders = folder_manager.list()
                for folder_info in folders:
                    folder_data = {
                        "name": folder_info.name,
                        "delimiter": folder_info.delim,
                        "flags": folder_info.flags,
                    }
                    folder_list.append(folder_data)
            except (
                imaplib.IMAP4.error,
                imaplib.IMAP4.abort,
                AttributeError,
                TypeError,
            ):
                # Fallback: just return the current folder
                folder_list = [
                    {
                        "name": str(mailbox.folder.get()),
                        "delimiter": "/",
                        "flags": [],
                    }
                ]

            return {
                "message": f"Found {len(folder_list)} folders",
                "current_folder": mailbox.folder.get() or "INBOX",
                "total_folders": len(folder_list),
                "folders": folder_list,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to list folders: {e!s}"

    @mcp.tool()
    async def select_folder(folder_name: str):
        """
        Select/switch to a specific folder.

        Args:
            folder_name: Name of the folder to select
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Select the folder
            mailbox.folder.set(folder_name)
            status = mailbox.folder.status(folder_name)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to select folder: {e!s}"
        else:
            return {
                "message": f"Successfully selected folder '{folder_name}'",
                "folder": folder_name,
                "status": status,
            }

    @mcp.tool()
    async def create_folder(folder_name: str):
        """
        Create a new folder/mailbox.

        Args:
            folder_name: Name of the folder to create
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Create the folder
            mailbox.folder.create(folder_name)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to create folder: {e!s}"
        else:
            return {
                "message": f"Successfully created folder '{folder_name}'",
                "folder": folder_name,
                "operation": "create",
            }

    @mcp.tool()
    async def delete_folder(folder_name: str):
        """
        Delete a folder/mailbox.

        Args:
            folder_name: Name of the folder to delete
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Delete the folder
            mailbox.folder.delete(folder_name)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to delete folder: {e!s}"
        else:
            return {
                "message": f"Successfully deleted folder '{folder_name}'",
                "folder": folder_name,
                "operation": "delete",
            }

    @mcp.tool()
    async def rename_folder(old_name: str, new_name: str):
        """
        Rename a folder/mailbox.

        Args:
            old_name: Current name of the folder
            new_name: New name for the folder
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Rename the folder
            mailbox.folder.rename(old_name, new_name)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to rename folder: {e!s}"
        else:
            return {
                "message": f"Successfully renamed folder '{old_name}' to '{new_name}'",
                "old_name": old_name,
                "new_name": new_name,
                "operation": "rename",
            }

    @mcp.tool()
    async def subscribe_to_folder(folder_name: str):
        """
        Subscribe to a folder.

        Args:
            folder_name: Name of the folder to subscribe to
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Subscribe to the folder
            mailbox.folder.subscribe(folder_name, True)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to subscribe to folder: {e!s}"
        else:
            return {
                "message": f"Successfully subscribed to folder '{folder_name}'",
                "folder": folder_name,
                "operation": "subscribe",
            }

    @mcp.tool()
    async def unsubscribe_from_folder(folder_name: str):
        """
        Unsubscribe from a folder.

        Args:
            folder_name: Name of the folder to unsubscribe from
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Unsubscribe from the folder
            mailbox.folder.subscribe(folder_name, False)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to unsubscribe from folder: {e!s}"
        else:
            return {
                "message": f"Successfully unsubscribed from folder '{folder_name}'",
                "folder": folder_name,
                "operation": "unsubscribe",
            }

    @mcp.tool()
    async def get_folder_status(folder_name: str = ""):
        """
        Get status information for a folder.

        Args:
            folder_name: Name of the folder (empty for current folder)
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Use current folder if none specified
            if not folder_name:
                folder_name = mailbox.folder.get() or "INBOX"

            # Get folder status
            status = mailbox.folder.status(folder_name)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get folder status: {e!s}"
        else:
            return {
                "message": f"Status for folder '{folder_name}'",
                "folder": folder_name,
                "status": status,
            }
