"""Folder management tools for IMAP server."""

from mcp.server.fastmcp import FastMCP
from .state import get_state_or_error
from datetime import datetime


def register_folder_tools(mcp: FastMCP):
    """Register folder-related tools with the MCP server."""

    @mcp.tool()
    async def list_folders():
        """List all available folders."""
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        folders = state.mailbox.folder.list()
        return [folder.name for folder in folders]

    @mcp.tool()
    async def select_folder(folder_name: str):
        """
        Switch to a specific folder.

        Args:
            folder_name: The name of the folder to switch to.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        state.mailbox.folder.set(folder_name)
        return f"Switched to folder: {folder_name}"

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

    @mcp.tool()
    async def list_folders_detailed():
        """
        List all folders with detailed information including hierarchy.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            folders = state.mailbox.folder.list()
            folder_info = []

            for folder in folders:
                # Determine folder level based on separator
                level = folder.name.count(folder.delimiter) if folder.delimiter else 0

                folder_data = {
                    "name": folder.name,
                    "flags": list(folder.flags) if folder.flags else [],
                    "delimiter": folder.delimiter,
                    "level": level,
                    "is_selectable": "\\Noselect" not in (folder.flags or []),
                    "has_children": "\\HasChildren" in (folder.flags or []),
                    "has_no_children": "\\HasNoChildren" in (folder.flags or []),
                }
                folder_info.append(folder_data)

            # Sort by name for consistent display
            folder_info.sort(key=lambda x: x["name"])

            return {
                "message": f"Found {len(folder_info)} folders",
                "count": len(folder_info),
                "folders": folder_info,
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
            if not state.mailbox.folder.exists(folder_name):
                return f"Folder '{folder_name}' does not exist."

            # Save current folder and switch to target folder
            current_folder = state.mailbox.folder.get()
            state.mailbox.folder.set(folder_name)

            # Get folder info
            folder_status = state.mailbox.folder.status(folder_name)

            # Count various message types
            total_messages = len(list(state.mailbox.fetch(headers_only=True)))
            unread_messages = len(
                list(state.mailbox.fetch("UNSEEN", headers_only=True))
            )

            # Get folder attributes
            folders = state.mailbox.folder.list()
            folder_obj = None
            for folder in folders:
                if folder.name == folder_name:
                    folder_obj = folder
                    break

            # Restore original folder
            state.mailbox.folder.set(current_folder)

            info = {
                "name": folder_name,
                "total_messages": total_messages,
                "unread_messages": unread_messages,
                "read_messages": total_messages - unread_messages,
                "flags": list(folder_obj.flags)
                if folder_obj and folder_obj.flags
                else [],
                "delimiter": folder_obj.delimiter if folder_obj else "/",
                "is_selectable": folder_obj
                and "\\Noselect" not in (folder_obj.flags or []),
                "status": folder_status._asdict() if folder_status else {},
            }

            return info

        except Exception as e:
            return f"Failed to get folder info for '{folder_name}': {str(e)}"

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
        Subscribe to a folder to make it visible in mail clients.

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
        Unsubscribe from a folder to hide it from mail clients.

        Args:
            folder_name: The name of the folder to unsubscribe from.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            if not state.mailbox.folder.exists(folder_name):
                return f"Folder '{folder_name}' does not exist."

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
            page: Page number to retrieve (1-based, default: 1)
            page_size: Number of emails per page (1-1000, default: 20)
            headers_only: If True, only fetch headers for faster loading (default: True)
            unread_only: If True, only show unread emails (default: False)
            reverse: If True, show newest emails first (default: True)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if page < 1:
            return "Page number must be 1 or greater."

        if page_size < 1 or page_size > 1000:
            return "Page size must be between 1 and 1000."

        try:
            # Build search criteria
            criteria = "UNSEEN" if unread_only else None

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
                "emails": results,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev,
                    "showing_count": len(results),
                },
                "filter": {
                    "headers_only": headers_only,
                    "unread_only": unread_only,
                    "reverse": reverse,
                },
            }

        except Exception as e:
            return f"Failed to list emails with pagination: {str(e)}"

    # FOLDER STATISTICS & ANALYTICS
    @mcp.tool()
    async def get_folder_statistics(folder_name: str):
        """
        Get comprehensive statistics for a specific folder.

        Args:
            folder_name: The name of the folder to analyze.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            if not state.mailbox.folder.exists(folder_name):
                return f"Folder '{folder_name}' does not exist."

            # Save current folder and switch to target folder
            current_folder = state.mailbox.folder.get()
            state.mailbox.folder.set(folder_name)

            # Get all message headers for analysis
            messages = list(state.mailbox.fetch(headers_only=True))
            total_count = len(messages)

            if total_count == 0:
                state.mailbox.folder.set(current_folder)
                return {
                    "folder_name": folder_name,
                    "total_messages": 0,
                    "message": "Folder is empty",
                }

            # Initialize counters
            unread_count = 0
            flagged_count = 0
            deleted_count = 0
            draft_count = 0
            answered_count = 0
            with_attachments = 0
            total_size = 0
            sender_counts = {}

            # Size distribution
            size_ranges = {
                "small": 0,  # < 100KB
                "medium": 0,  # 100KB - 1MB
                "large": 0,  # 1MB - 10MB
                "very_large": 0,  # > 10MB
            }

            # Recent activity counters
            now = datetime.now()
            today_count = 0
            this_week_count = 0
            this_month_count = 0

            # Process each message
            for msg in messages:
                # Flag analysis
                flags = set(msg.flags) if msg.flags else set()
                if "\\Seen" not in flags:
                    unread_count += 1
                if "\\Flagged" in flags:
                    flagged_count += 1
                if "\\Deleted" in flags:
                    deleted_count += 1
                if "\\Draft" in flags:
                    draft_count += 1
                if "\\Answered" in flags:
                    answered_count += 1

                # Attachment analysis
                if len(msg.attachments) > 0:
                    with_attachments += 1

                # Size analysis
                msg_size = msg.size or 0
                total_size += msg_size

                if msg_size < 100_000:  # 100KB
                    size_ranges["small"] += 1
                elif msg_size < 1_000_000:  # 1MB
                    size_ranges["medium"] += 1
                elif msg_size < 10_000_000:  # 10MB
                    size_ranges["large"] += 1
                else:
                    size_ranges["very_large"] += 1

                # Sender analysis
                sender = msg.from_ or "unknown"
                sender_counts[sender] = sender_counts.get(sender, 0) + 1

                # Recent activity analysis
                if msg.date:
                    try:
                        # Convert to naive datetime if timezone-aware
                        msg_date = msg.date
                        if msg_date.tzinfo is not None:
                            msg_date = msg_date.replace(tzinfo=None)

                        days_ago = (now - msg_date).days
                        if days_ago == 0:
                            today_count += 1
                        if days_ago <= 7:
                            this_week_count += 1
                        if days_ago <= 30:
                            this_month_count += 1
                    except Exception:
                        # Skip date analysis for this message if there's an error
                        pass

            # Top senders (limit to top 10)
            top_senders = sorted(
                sender_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]

            # Restore original folder
            state.mailbox.folder.set(current_folder)

            return {
                "folder_name": folder_name,
                "total_messages": total_count,
                "message_flags": {
                    "unread": unread_count,
                    "read": total_count - unread_count,
                    "flagged": flagged_count,
                    "deleted": deleted_count,
                    "draft": draft_count,
                    "answered": answered_count,
                },
                "attachments": {
                    "with_attachments": with_attachments,
                    "without_attachments": total_count - with_attachments,
                    "percentage_with_attachments": round(
                        (with_attachments / total_count) * 100, 1
                    ),
                },
                "size_analysis": {
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "average_size_bytes": round(total_size / total_count)
                    if total_count > 0
                    else 0,
                    "size_distribution": size_ranges,
                },
                "recent_activity": {
                    "today": today_count,
                    "this_week": this_week_count,
                    "this_month": this_month_count,
                },
                "top_senders": [
                    {"sender": sender, "count": count} for sender, count in top_senders
                ],
            }

        except Exception as e:
            return f"Failed to get folder statistics for '{folder_name}': {str(e)}"

    @mcp.tool()
    async def get_all_folders_statistics():
        """
        Get statistics for all folders in the mailbox.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            folders = state.mailbox.folder.list()
            folder_stats = []
            total_mailbox_messages = 0
            total_mailbox_size = 0

            for folder in folders:
                # Skip folders that can't be selected
                if folder.flags and "\\Noselect" in folder.flags:
                    continue

                try:
                    # Get basic stats for each folder
                    current_folder = state.mailbox.folder.get()
                    state.mailbox.folder.set(folder.name)

                    messages = list(state.mailbox.fetch(headers_only=True))
                    message_count = len(messages)

                    if message_count > 0:
                        unread_count = len(
                            [
                                msg
                                for msg in messages
                                if "\\Seen" not in (msg.flags or [])
                            ]
                        )
                        folder_size = sum(msg.size or 0 for msg in messages)

                        folder_stats.append(
                            {
                                "name": folder.name,
                                "total_messages": message_count,
                                "unread_messages": unread_count,
                                "read_messages": message_count - unread_count,
                                "size_bytes": folder_size,
                                "size_mb": round(folder_size / (1024 * 1024), 2),
                                "average_message_size": round(
                                    folder_size / message_count
                                )
                                if message_count > 0
                                else 0,
                            }
                        )

                        total_mailbox_messages += message_count
                        total_mailbox_size += folder_size
                    else:
                        folder_stats.append(
                            {
                                "name": folder.name,
                                "total_messages": 0,
                                "unread_messages": 0,
                                "read_messages": 0,
                                "size_bytes": 0,
                                "size_mb": 0,
                                "average_message_size": 0,
                            }
                        )

                    state.mailbox.folder.set(current_folder)

                except Exception as e:
                    # If we can't access a folder, skip it but log the error
                    folder_stats.append(
                        {
                            "name": folder.name,
                            "error": f"Cannot access folder: {str(e)}",
                            "total_messages": 0,
                            "unread_messages": 0,
                            "read_messages": 0,
                            "size_bytes": 0,
                            "size_mb": 0,
                            "average_message_size": 0,
                        }
                    )

            # Sort by message count (descending)
            folder_stats.sort(key=lambda x: x.get("total_messages", 0), reverse=True)

            return {
                "total_folders": len(folder_stats),
                "mailbox_summary": {
                    "total_messages": total_mailbox_messages,
                    "total_size_bytes": total_mailbox_size,
                    "total_size_mb": round(total_mailbox_size / (1024 * 1024), 2),
                    "total_size_gb": round(
                        total_mailbox_size / (1024 * 1024 * 1024), 2
                    ),
                    "average_message_size": round(
                        total_mailbox_size / total_mailbox_messages
                    )
                    if total_mailbox_messages > 0
                    else 0,
                },
                "folders": folder_stats,
            }

        except Exception as e:
            return f"Failed to get all folders statistics: {str(e)}"

    # HEADERS-ONLY OPERATIONS
    @mcp.tool()
    async def get_email_headers(uid: str):
        """
        Get just the headers of a specific email for quick preview.

        Args:
            uid: The UID of the email to get headers for.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Fetch just the headers
            for msg in state.mailbox.fetch(f"UID {uid}", headers_only=True):
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
                }

            return f"Email with UID {uid} not found."

        except Exception as e:
            return f"Failed to get email headers for UID {uid}: {str(e)}"

    @mcp.tool()
    async def batch_get_headers(uid_list: str):
        """
        Get headers for multiple emails efficiently.

        Args:
            uid_list: Comma-separated list of email UIDs to get headers for.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        # Parse UID list
        uids = [uid.strip() for uid in uid_list.split(",") if uid.strip()]
        if not uids:
            return "No valid UIDs provided."

        try:
            # Build UID search criteria
            uid_criteria = " ".join(uids)

            # Fetch headers for all UIDs in one go
            messages = state.mailbox.fetch(f"UID {uid_criteria}", headers_only=True)

            results = []
            for msg in messages:
                results.append(
                    {
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
                    }
                )

            return {
                "message": f"Retrieved headers for {len(results)} out of {len(uids)} requested emails",
                "requested_count": len(uids),
                "found_count": len(results),
                "headers": results,
            }

        except Exception as e:
            return f"Failed to get batch headers: {str(e)}"
