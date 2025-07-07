"""Folder management tools for IMAP server."""

from imap_tools import AND, MailMessageFlags
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
        return f"Selected folder: {folder}"

    @mcp.tool()
    async def move_email(uid: str, destination_folder: str):
        """
        Move an email to a different folder.

        Args:
            uid: The UID of the email to move.
            destination_folder: The name of the destination folder.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        state.mailbox.move(uid, destination_folder)
        return f"Email {uid} moved to {destination_folder}."

    # ENHANCED FOLDER MANAGEMENT
    @mcp.tool()
    async def list_folders_detailed():
        """List all folders with detailed information including hierarchy and attributes."""
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            folders = state.mailbox.folder.list()

            detailed_folders = []
            for folder in folders:
                folder_info = {
                    "name": folder.name,
                    "delimiter": folder.delimiter,
                    "flags": list(folder.flags) if hasattr(folder, "flags") else [],
                }

                # Add hierarchy information
                parts = (
                    folder.name.split(folder.delimiter)
                    if folder.delimiter
                    else [folder.name]
                )
                folder_info.update(
                    {
                        "level": len(parts) - 1,
                        "parent": folder.delimiter.join(parts[:-1])
                        if len(parts) > 1
                        else None,
                        "display_name": parts[-1],
                    }
                )

                detailed_folders.append(folder_info)

            return {
                "message": f"Found {len(detailed_folders)} folders",
                "count": len(detailed_folders),
                "folders": detailed_folders,
            }

        except Exception as e:
            return f"Failed to list folders: {str(e)}"

    @mcp.tool()
    async def get_folder_info(folder_name: str):
        """
        Get detailed information about a specific folder.

        Args:
            folder_name: The name of the folder to get information about.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Check if folder exists
            if not state.mailbox.folder.exists(folder_name):
                return f"Folder '{folder_name}' does not exist."

            # Get folder status
            current_folder = state.mailbox.folder.get()
            state.mailbox.folder.set(folder_name)

            # Get folder statistics
            folder_status = state.mailbox.folder.status()

            # Get some sample messages for additional info
            total_messages = len(list(state.mailbox.fetch(headers_only=True)))
            unread_messages = len(
                list(state.mailbox.fetch(AND(seen=False), headers_only=True))
            )

            # Get folder from list to get attributes
            folder_obj = None
            for folder in state.mailbox.folder.list():
                if folder.name == folder_name:
                    folder_obj = folder
                    break

            result = {
                "name": folder_name,
                "exists": True,
                "total_messages": total_messages,
                "unread_messages": unread_messages,
                "read_messages": total_messages - unread_messages,
                "status": folder_status if folder_status else {},
            }

            if folder_obj:
                result.update(
                    {
                        "delimiter": folder_obj.delimiter,
                        "flags": list(folder_obj.flags)
                        if hasattr(folder_obj, "flags")
                        else [],
                    }
                )

                # Add hierarchy info
                parts = (
                    folder_name.split(folder_obj.delimiter)
                    if folder_obj.delimiter
                    else [folder_name]
                )
                result.update(
                    {
                        "level": len(parts) - 1,
                        "parent": folder_obj.delimiter.join(parts[:-1])
                        if len(parts) > 1
                        else None,
                        "display_name": parts[-1],
                    }
                )

            # Restore original folder
            state.mailbox.folder.set(current_folder)

            return result

        except Exception as e:
            return f"Failed to get folder info: {str(e)}"

    @mcp.tool()
    async def create_folder(folder_name: str):
        """
        Create a new folder.

        Args:
            folder_name: The name of the folder to create.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            if state.mailbox.folder.exists(folder_name):
                return f"Folder '{folder_name}' already exists."

            state.mailbox.folder.create(folder_name)
            return f"Successfully created folder '{folder_name}'."

        except Exception as e:
            return f"Failed to create folder '{folder_name}': {str(e)}"

    @mcp.tool()
    async def delete_folder(folder_name: str, force: bool = False):
        """
        Delete a folder.

        Args:
            folder_name: The name of the folder to delete.
            force: If True, delete even if folder contains messages (default: False).
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            if not state.mailbox.folder.exists(folder_name):
                return f"Folder '{folder_name}' does not exist."

            # Check if folder has messages (unless force is True)
            if not force:
                current_folder = state.mailbox.folder.get()
                state.mailbox.folder.set(folder_name)
                message_count = len(list(state.mailbox.fetch(headers_only=True)))
                state.mailbox.folder.set(current_folder)

                if message_count > 0:
                    return f"Folder '{folder_name}' contains {message_count} messages. Use force=True to delete anyway."

            state.mailbox.folder.delete(folder_name)
            return f"Successfully deleted folder '{folder_name}'."

        except Exception as e:
            return f"Failed to delete folder '{folder_name}': {str(e)}"

    @mcp.tool()
    async def rename_folder(old_name: str, new_name: str):
        """
        Rename a folder.

        Args:
            old_name: The current name of the folder.
            new_name: The new name for the folder.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            if not state.mailbox.folder.exists(old_name):
                return f"Folder '{old_name}' does not exist."

            if state.mailbox.folder.exists(new_name):
                return f"Folder '{new_name}' already exists."

            state.mailbox.folder.rename(old_name, new_name)
            return f"Successfully renamed folder '{old_name}' to '{new_name}'."

        except Exception as e:
            return f"Failed to rename folder '{old_name}' to '{new_name}': {str(e)}"

    @mcp.tool()
    async def subscribe_folder(folder_name: str):
        """
        Subscribe to a folder.

        Args:
            folder_name: The name of the folder to subscribe to.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            if not state.mailbox.folder.exists(folder_name):
                return f"Folder '{folder_name}' does not exist."

            state.mailbox.folder.subscribe(folder_name)
            return f"Successfully subscribed to folder '{folder_name}'."

        except Exception as e:
            return f"Failed to subscribe to folder '{folder_name}': {str(e)}"

    @mcp.tool()
    async def unsubscribe_folder(folder_name: str):
        """
        Unsubscribe from a folder.

        Args:
            folder_name: The name of the folder to unsubscribe from.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            state.mailbox.folder.unsubscribe(folder_name)
            return f"Successfully unsubscribed from folder '{folder_name}'."

        except Exception as e:
            return f"Failed to unsubscribe from folder '{folder_name}': {str(e)}"

    @mcp.tool()
    async def list_subscribed_folders():
        """List all subscribed folders."""
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            subscribed_folders = state.mailbox.folder.list(subscribed=True)
            folder_names = [folder.name for folder in subscribed_folders]

            return {
                "message": f"Found {len(folder_names)} subscribed folders",
                "count": len(folder_names),
                "folders": folder_names,
            }

        except Exception as e:
            return f"Failed to list subscribed folders: {str(e)}"

    # PAGINATION SUPPORT
    @mcp.tool()
    async def list_emails_paginated(
        page: int = 1,
        page_size: int = 20,
        headers_only: bool = True,
        unread_only: bool = False,
        reverse: bool = True,
    ):
        """
        List emails with pagination support.

        Args:
            page: Page number starting from 1 (default: 1).
            page_size: Number of emails per page (default: 20).
            headers_only: If True, only fetch headers for faster loading (default: True).
            unread_only: If True, only show unread emails (default: False).
            reverse: If True, show newest emails first (default: True).
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            if page < 1:
                return "Page number must be 1 or greater."

            if page_size < 1 or page_size > 1000:
                return "Page size must be between 1 and 1000."

            # Build search criteria
            criteria = AND(seen=False) if unread_only else None

            # Calculate offset and limit
            offset = (page - 1) * page_size

            # Fetch emails with pagination
            if criteria:
                messages = state.mailbox.fetch(
                    criteria,
                    headers_only=headers_only,
                    reverse=reverse,
                    limit=page_size + offset,  # Fetch more to handle offset
                )
            else:
                messages = state.mailbox.fetch(
                    headers_only=headers_only,
                    reverse=reverse,
                    limit=page_size + offset,
                )

            # Convert to list and apply pagination
            all_messages = list(messages)
            total_count = len(all_messages)

            # Apply offset and limit
            paginated_messages = all_messages[offset : offset + page_size]

            results = []
            for msg in paginated_messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "flags": list(msg.flags),
                    "attachment_count": len(msg.attachments),
                }
                if not headers_only:
                    result.update(
                        {
                            "text": msg.text,
                            "html": msg.html,
                        }
                    )
                results.append(result)

            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "message": f"Page {page} of {total_pages} ({len(results)} emails)",
                "pagination": {
                    "current_page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "has_next": has_next,
                    "has_prev": has_prev,
                    "showing_from": offset + 1 if results else 0,
                    "showing_to": offset + len(results),
                },
                "filters": {
                    "headers_only": headers_only,
                    "unread_only": unread_only,
                    "reverse": reverse,
                },
                "emails": results,
            }

        except Exception as e:
            return f"Failed to list emails with pagination: {str(e)}"

    # FOLDER STATISTICS
    @mcp.tool()
    async def get_folder_statistics(folder_name: str = ""):
        """
        Get comprehensive statistics for a folder.

        Args:
            folder_name: Name of the folder to analyze (empty for current folder).
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            current_folder = state.mailbox.folder.get()
            target_folder = folder_name or current_folder

            # Switch to target folder if needed
            if folder_name and folder_name != current_folder:
                if not state.mailbox.folder.exists(folder_name):
                    return f"Folder '{folder_name}' does not exist."
                state.mailbox.folder.set(folder_name)

            # Get all emails with headers only for performance
            all_messages = list(state.mailbox.fetch(headers_only=True))

            # Initialize counters
            stats = {
                "folder_name": target_folder,
                "total_messages": len(all_messages),
                "unread_count": 0,
                "read_count": 0,
                "flagged_count": 0,
                "draft_count": 0,
                "answered_count": 0,
                "deleted_count": 0,
                "with_attachments": 0,
                "total_size": 0,
                "size_by_range": {
                    "small": 0,  # < 100KB
                    "medium": 0,  # 100KB - 1MB
                    "large": 0,  # 1MB - 10MB
                    "very_large": 0,  # > 10MB
                },
                "recent_activity": {
                    "today": 0,
                    "this_week": 0,
                    "this_month": 0,
                },
                "top_senders": {},
            }

            from datetime import datetime, timedelta

            now = datetime.now()
            today = now.date()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            # Analyze each message
            for msg in all_messages:
                # Count by flags
                flags = set(msg.flags)
                if MailMessageFlags.SEEN not in flags:
                    stats["unread_count"] += 1
                else:
                    stats["read_count"] += 1

                if MailMessageFlags.FLAGGED in flags:
                    stats["flagged_count"] += 1
                if MailMessageFlags.DRAFT in flags:
                    stats["draft_count"] += 1
                if MailMessageFlags.ANSWERED in flags:
                    stats["answered_count"] += 1
                if MailMessageFlags.DELETED in flags:
                    stats["deleted_count"] += 1

                # Count attachments
                if len(msg.attachments) > 0:
                    stats["with_attachments"] += 1

                # Size analysis
                size = msg.size
                stats["total_size"] += size

                if size < 100 * 1024:  # 100KB
                    stats["size_by_range"]["small"] += 1
                elif size < 1024 * 1024:  # 1MB
                    stats["size_by_range"]["medium"] += 1
                elif size < 10 * 1024 * 1024:  # 10MB
                    stats["size_by_range"]["large"] += 1
                else:
                    stats["size_by_range"]["very_large"] += 1

                # Recent activity
                msg_date = msg.date
                if msg_date:
                    if msg_date.date() == today:
                        stats["recent_activity"]["today"] += 1
                    if msg_date >= week_ago:
                        stats["recent_activity"]["this_week"] += 1
                    if msg_date >= month_ago:
                        stats["recent_activity"]["this_month"] += 1

                # Top senders
                sender = msg.from_
                if sender:
                    stats["top_senders"][sender] = (
                        stats["top_senders"].get(sender, 0) + 1
                    )

            # Convert top senders to sorted list
            top_senders_list = sorted(
                stats["top_senders"].items(), key=lambda x: x[1], reverse=True
            )[:10]  # Top 10 senders

            stats["top_senders"] = [
                {"sender": sender, "count": count} for sender, count in top_senders_list
            ]

            # Add calculated percentages
            total = stats["total_messages"]
            if total > 0:
                stats["percentages"] = {
                    "unread": round((stats["unread_count"] / total) * 100, 1),
                    "flagged": round((stats["flagged_count"] / total) * 100, 1),
                    "with_attachments": round(
                        (stats["with_attachments"] / total) * 100, 1
                    ),
                }

            # Human readable size
            def format_size(bytes_count):
                for unit in ["B", "KB", "MB", "GB"]:
                    if bytes_count < 1024.0:
                        return f"{bytes_count:.1f} {unit}"
                    bytes_count /= 1024.0
                return f"{bytes_count:.1f} TB"

            stats["total_size_formatted"] = format_size(stats["total_size"])
            stats["average_size_formatted"] = (
                format_size(stats["total_size"] / total) if total > 0 else "0 B"
            )

            # Restore original folder
            if folder_name and folder_name != current_folder:
                state.mailbox.folder.set(current_folder)

            return stats

        except Exception as e:
            # Restore original folder on error
            if folder_name and folder_name != current_folder:
                try:
                    state.mailbox.folder.set(current_folder)
                except Exception:
                    pass
            return f"Failed to get folder statistics: {str(e)}"

    @mcp.tool()
    async def get_all_folders_statistics():
        """Get statistics for all folders in the mailbox."""
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            current_folder = state.mailbox.folder.get()
            folders = state.mailbox.folder.list()
            all_stats = []

            for folder in folders:
                try:
                    # Get basic stats for each folder
                    state.mailbox.folder.set(folder.name)
                    messages = list(state.mailbox.fetch(headers_only=True))

                    unread_count = sum(
                        1 for msg in messages if MailMessageFlags.SEEN not in msg.flags
                    )

                    total_size = sum(msg.size for msg in messages)
                    with_attachments = sum(
                        1 for msg in messages if len(msg.attachments) > 0
                    )

                    def format_size(bytes_count):
                        for unit in ["B", "KB", "MB", "GB"]:
                            if bytes_count < 1024.0:
                                return f"{bytes_count:.1f} {unit}"
                            bytes_count /= 1024.0
                        return f"{bytes_count:.1f} TB"

                    folder_stats = {
                        "name": folder.name,
                        "total_messages": len(messages),
                        "unread_count": unread_count,
                        "read_count": len(messages) - unread_count,
                        "with_attachments": with_attachments,
                        "total_size": total_size,
                        "total_size_formatted": format_size(total_size),
                        "delimiter": folder.delimiter,
                        "flags": list(folder.flags) if hasattr(folder, "flags") else [],
                    }

                    all_stats.append(folder_stats)

                except Exception as e:
                    # Skip folders that can't be accessed
                    all_stats.append(
                        {
                            "name": folder.name,
                            "error": f"Could not access folder: {str(e)}",
                        }
                    )

            # Restore original folder
            state.mailbox.folder.set(current_folder)

            # Calculate totals
            total_messages = sum(
                stats.get("total_messages", 0)
                for stats in all_stats
                if "error" not in stats
            )
            total_unread = sum(
                stats.get("unread_count", 0)
                for stats in all_stats
                if "error" not in stats
            )
            total_size = sum(
                stats.get("total_size", 0)
                for stats in all_stats
                if "error" not in stats
            )

            def format_size(bytes_count):
                for unit in ["B", "KB", "MB", "GB"]:
                    if bytes_count < 1024.0:
                        return f"{bytes_count:.1f} {unit}"
                    bytes_count /= 1024.0
                return f"{bytes_count:.1f} TB"

            return {
                "message": f"Statistics for {len(all_stats)} folders",
                "summary": {
                    "total_folders": len(all_stats),
                    "total_messages": total_messages,
                    "total_unread": total_unread,
                    "total_size": total_size,
                    "total_size_formatted": format_size(total_size),
                },
                "folders": all_stats,
            }

        except Exception as e:
            # Restore original folder on error
            try:
                state.mailbox.folder.set(current_folder)
            except Exception:
                pass
            return f"Failed to get all folders statistics: {str(e)}"

    # HEADER-ONLY OPERATIONS
    @mcp.tool()
    async def get_email_headers(uid: str):
        """
        Get only the headers of a specific email for fast preview.

        Args:
            uid: The UID of the email to get headers for.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Fetch with headers only for performance
            for msg in state.mailbox.fetch(AND(uid=uid), headers_only=True):
                return {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "to": msg.to,
                    "cc": msg.cc,
                    "bcc": msg.bcc,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "flags": list(msg.flags),
                    "attachment_count": len(msg.attachments),
                    "message_id": msg.message_id,
                    "in_reply_to": getattr(msg, "in_reply_to", None),
                    "references": getattr(msg, "references", None),
                }

            return f"Email with UID {uid} not found."

        except Exception as e:
            return f"Failed to get email headers: {str(e)}"

    @mcp.tool()
    async def batch_get_headers(uid_list: str):
        """
        Get headers for multiple emails efficiently.

        Args:
            uid_list: Comma-separated list of email UIDs.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Parse UID list
            uids = [uid.strip() for uid in uid_list.split(",") if uid.strip()]
            if not uids:
                return "No valid UIDs provided."

            # Fetch headers for all UIDs at once
            messages = state.mailbox.fetch(headers_only=True)

            # Filter to only requested UIDs
            results = []
            uid_set = set(uids)
            for msg in messages:
                if msg.uid in uid_set:
                    result = {
                        "uid": msg.uid,
                        "from": msg.from_,
                        "to": msg.to,
                        "subject": msg.subject,
                        "date": msg.date_str,
                        "size": msg.size,
                        "flags": list(msg.flags),
                        "attachment_count": len(msg.attachments),
                    }
                    results.append(result)

            return {
                "message": f"Retrieved headers for {len(results)} emails",
                "requested_count": len(uids),
                "found_count": len(results),
                "emails": results,
            }

        except Exception as e:
            return f"Failed to batch get headers: {str(e)}"
