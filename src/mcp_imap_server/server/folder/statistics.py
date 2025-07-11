"""Folder statistics tools for IMAP server."""

import imaplib
from datetime import datetime, timedelta
from imap_tools import AND
from mcp.server.fastmcp import FastMCP
from ..state import get_state_or_error


def register_folder_statistics_tools(mcp: FastMCP):
    """Register folder statistics tools with the MCP server."""

    @mcp.tool()
    async def get_folder_statistics(folder_name: str = ""):
        """
        Get comprehensive statistics for a folder.

        Args:
            folder_name: Name of the folder (empty for current folder)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Get folder statistics
            if folder_name:
                # Switch to specific folder for statistics
                original_folder = state.mailbox.folder
                state.mailbox.folder.set(folder_name)

                # Get statistics for the specific folder - convert generator to list
                messages = list(state.mailbox.fetch())
                total_messages = len(messages)

                # Count read/unread messages
                read_count = 0
                unread_count = 0
                flagged_count = 0

                for msg in messages:
                    if "\\Seen" in msg.flags:
                        read_count += 1
                    else:
                        unread_count += 1

                    if "\\Flagged" in msg.flags:
                        flagged_count += 1

                # Restore original folder
                state.mailbox.folder.set(original_folder)

                result = {
                    "message": f"Statistics for folder '{folder_name}'",
                    "folder": folder_name,
                    "total_messages": total_messages,
                    "read_messages": read_count,
                    "unread_messages": unread_count,
                    "flagged_messages": flagged_count,
                    "read_percentage": f"{(read_count / total_messages) * 100:.1f}%"
                    if total_messages > 0
                    else "0%",
                }
            else:
                # Get overall statistics across all folders
                folder_names = []
                try:
                    folder_manager = state.mailbox.folder
                    folder_names = [folder.name for folder in folder_manager.list()]
                except (
                    imaplib.IMAP4.error,
                    imaplib.IMAP4.abort,
                    AttributeError,
                    TypeError,
                ):
                    # Fallback: try to get just the current folder
                    folder_names = [str(state.mailbox.folder)]

                total_folders = len(folder_names)
                total_messages = 0
                total_read = 0
                total_unread = 0
                total_flagged = 0

                for folder_name in folder_names:
                    try:
                        state.mailbox.folder.set(folder_name)
                        messages = list(state.mailbox.fetch())
                        total_messages += len(messages)

                        for msg in messages:
                            if "\\Seen" in msg.flags:
                                total_read += 1
                            else:
                                total_unread += 1

                            if "\\Flagged" in msg.flags:
                                total_flagged += 1
                    except (
                        imaplib.IMAP4.error,
                        imaplib.IMAP4.abort,
                        AttributeError,
                        TypeError,
                    ):
                        continue  # Skip folders that can't be accessed

                result = {
                    "message": "Overall email statistics",
                    "total_folders": total_folders,
                    "total_messages": total_messages,
                    "read_messages": total_read,
                    "unread_messages": total_unread,
                    "flagged_messages": total_flagged,
                    "read_percentage": f"{(total_read / total_messages) * 100:.1f}%"
                    if total_messages > 0
                    else "0%",
                }
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get folder statistics: {e!s}"
        else:
            return result

    @mcp.tool()
    async def get_folder_size_breakdown(
        folder_name: str = "", size_ranges: bool = True
    ):
        """
        Get size breakdown analysis for a folder.

        Args:
            folder_name: Name of the folder (empty for current folder)
            size_ranges: Include size range breakdown
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Use current folder if none specified
            original_folder = state.mailbox.folder
            if folder_name and folder_name != str(original_folder):
                state.mailbox.folder.set(folder_name)
            else:
                folder_name = str(original_folder)

            # Get all messages
            all_messages = list(state.mailbox.fetch(headers_only=True))

            if not all_messages:
                return {
                    "message": f"No messages in folder '{folder_name}'",
                    "folder": folder_name,
                    "total_messages": 0,
                }

            # Calculate size statistics
            sizes = [msg.size for msg in all_messages]
            total_size = sum(sizes)
            avg_size = total_size // len(sizes)
            max_size = max(sizes)
            min_size = min(sizes)

            result = {
                "message": f"Size breakdown for folder '{folder_name}'",
                "folder": folder_name,
                "total_messages": len(all_messages),
                "total_size_bytes": total_size,
                "total_size_formatted": _format_size(total_size),
                "average_size_bytes": avg_size,
                "average_size_formatted": _format_size(avg_size),
                "largest_email_bytes": max_size,
                "largest_email_formatted": _format_size(max_size),
                "smallest_email_bytes": min_size,
                "smallest_email_formatted": _format_size(min_size),
            }

            # Add size ranges if requested
            if size_ranges:
                ranges = {
                    "tiny (< 1KB)": 0,
                    "small (1KB - 10KB)": 0,
                    "medium (10KB - 100KB)": 0,
                    "large (100KB - 1MB)": 0,
                    "very_large (1MB - 10MB)": 0,
                    "huge (> 10MB)": 0,
                }

                for size in sizes:
                    if size < 1024:
                        ranges["tiny (< 1KB)"] += 1
                    elif size < 10240:
                        ranges["small (1KB - 10KB)"] += 1
                    elif size < 102400:
                        ranges["medium (10KB - 100KB)"] += 1
                    elif size < 1048576:
                        ranges["large (100KB - 1MB)"] += 1
                    elif size < 10485760:
                        ranges["very_large (1MB - 10MB)"] += 1
                    else:
                        ranges["huge (> 10MB)"] += 1

                result["size_ranges"] = ranges

            # Restore original folder if we changed it
            if folder_name != original_folder:
                state.mailbox.folder.set(original_folder)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get folder size breakdown: {e!s}"
        else:
            return result

    @mcp.tool()
    async def get_folder_activity_stats(folder_name: str = "", days: int = 30):
        """
        Get activity statistics for a folder over the specified time period.

        Args:
            folder_name: Name of the folder (empty for current folder)
            days: Number of days to analyze (default: 30)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Use current folder if none specified
            original_folder = state.mailbox.folder
            if folder_name and folder_name != str(original_folder):
                state.mailbox.folder.set(folder_name)
            else:
                folder_name = str(original_folder)

            # Calculate date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)

            # Search for messages in the date range
            criteria = AND(date_gte=start_date)
            recent_messages = list(state.mailbox.fetch(criteria, headers_only=True))

            # Count by day
            daily_counts = {}
            for i in range(days + 1):
                date = start_date + timedelta(days=i)
                daily_counts[date.strftime("%Y-%m-%d")] = 0

            # Count messages per day
            for msg in recent_messages:
                if msg.date:
                    date_str = msg.date.strftime("%Y-%m-%d")
                    if date_str in daily_counts:
                        daily_counts[date_str] += 1

            # Calculate weekly averages
            weekly_totals = []
            for week_start in range(0, days, 7):
                week_end = min(week_start + 7, days)
                week_total = sum(
                    daily_counts.get(
                        (start_date + timedelta(days=d)).strftime("%Y-%m-%d"), 0
                    )
                    for d in range(week_start, week_end)
                )
                weekly_totals.append(week_total)

            # Get busiest and quietest days
            sorted_days = sorted(daily_counts.items(), key=lambda x: x[1], reverse=True)
            busiest_day = sorted_days[0] if sorted_days else None
            quietest_day = sorted_days[-1] if sorted_days else None

            # Restore original folder if we changed it
            if folder_name != original_folder:
                state.mailbox.folder.set(original_folder)

            return {
                "message": f"Activity statistics for folder '{folder_name}' over {days} days",
                "folder": folder_name,
                "period_days": days,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "total_messages_in_period": len(recent_messages),
                "daily_average": len(recent_messages) / days if days > 0 else 0,
                "weekly_averages": weekly_totals,
                "busiest_day": {
                    "date": busiest_day[0] if busiest_day else None,
                    "count": busiest_day[1] if busiest_day else 0,
                },
                "quietest_day": {
                    "date": quietest_day[0] if quietest_day else None,
                    "count": quietest_day[1] if quietest_day else 0,
                },
                "daily_counts": daily_counts,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get folder activity statistics: {e!s}"

    @mcp.tool()
    async def get_top_senders(folder_name: str = "", limit: int = 10):
        """
        Get top senders by email count in a folder.

        Args:
            folder_name: Name of the folder (empty for current folder)
            limit: Number of top senders to return (default: 10)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Use current folder if none specified
            original_folder = state.mailbox.folder
            if folder_name and folder_name != str(original_folder):
                state.mailbox.folder.set(folder_name)
            else:
                folder_name = str(original_folder)

            # Get all messages
            all_messages = list(state.mailbox.fetch(headers_only=True))

            if not all_messages:
                return {
                    "message": f"No messages in folder '{folder_name}'",
                    "folder": folder_name,
                    "total_messages": 0,
                }

            # Count emails by sender
            sender_counts = {}
            for msg in all_messages:
                sender = msg.from_ or "Unknown"
                sender_counts[sender] = sender_counts.get(sender, 0) + 1

            # Sort by count and get top senders
            sorted_senders = sorted(
                sender_counts.items(), key=lambda x: x[1], reverse=True
            )
            top_senders = sorted_senders[:limit]

            # Calculate percentages
            total_messages = len(all_messages)
            top_senders_with_percentage = [
                {
                    "sender": sender,
                    "count": count,
                    "percentage": round((count / total_messages) * 100, 2),
                }
                for sender, count in top_senders
            ]

            # Restore original folder if we changed it
            if folder_name != original_folder:
                state.mailbox.folder.set(original_folder)

            return {
                "message": f"Top {len(top_senders)} senders in folder '{folder_name}'",
                "folder": folder_name,
                "total_messages": total_messages,
                "unique_senders": len(sender_counts),
                "top_senders": top_senders_with_percentage,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get top senders: {e!s}"


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    size = float(size_bytes)
    i = 0

    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024
        i += 1

    return f"{size:.1f} {size_names[i]}"
