"""Folder statistics tools for IMAP server."""

import imaplib
from mcp.server.fastmcp import FastMCP
from ..state import get_mailbox


def register_folder_statistics_tools(mcp: FastMCP):
    """Register folder statistics tools with the MCP server."""

    @mcp.tool()
    async def get_folder_statistics(folder_name: str = ""):
        """
        Get comprehensive statistics for a folder.

        Args:
            folder_name: Name of the folder (empty for current folder)
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Get folder statistics
            if folder_name:
                # Switch to specific folder for statistics
                original_folder = mailbox.folder.get() or "INBOX"
                mailbox.folder.set(folder_name)

                # Get statistics for the specific folder - convert generator to list
                messages = list(mailbox.fetch())
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
                mailbox.folder.set(str(original_folder))
            else:
                # Use current folder
                folder_name = mailbox.folder.get() or "INBOX"
                messages = list(mailbox.fetch())
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

            # Calculate percentages
            read_percentage = (
                (read_count / total_messages * 100) if total_messages > 0 else 0
            )
            unread_percentage = (
                (unread_count / total_messages * 100) if total_messages > 0 else 0
            )
            flagged_percentage = (
                (flagged_count / total_messages * 100) if total_messages > 0 else 0
            )

            return {
                "message": f"Statistics for folder '{folder_name}'",
                "folder": folder_name,
                "total_messages": total_messages,
                "read_messages": read_count,
                "unread_messages": unread_count,
                "flagged_messages": flagged_count,
                "read_percentage": round(read_percentage, 2),
                "unread_percentage": round(unread_percentage, 2),
                "flagged_percentage": round(flagged_percentage, 2),
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get folder statistics: {e!s}"

    @mcp.tool()
    async def get_folder_size_distribution(folder_name: str = ""):
        """
        Get email size distribution for a folder.

        Args:
            folder_name: Name of the folder (empty for current folder)
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Use current folder if none specified
            original_folder = mailbox.folder.get() or "INBOX"
            if folder_name and folder_name != str(original_folder):
                mailbox.folder.set(folder_name)
            else:
                folder_name = str(original_folder)

            # Get all messages
            all_messages = list(mailbox.fetch(headers_only=True))

            if not all_messages:
                return {
                    "message": f"No messages in folder '{folder_name}'",
                    "folder": folder_name,
                    "total_messages": 0,
                }

            # Calculate size statistics
            sizes = [msg.size for msg in all_messages]
            total_size = sum(sizes)
            avg_size = total_size / len(sizes) if sizes else 0
            max_size = max(sizes) if sizes else 0
            min_size = min(sizes) if sizes else 0

            # Create size distribution
            size_ranges = {
                "0-1KB": 0,
                "1KB-10KB": 0,
                "10KB-100KB": 0,
                "100KB-1MB": 0,
                "1MB-10MB": 0,
                "10MB+": 0,
            }

            for size in sizes:
                if size < 1024:
                    size_ranges["0-1KB"] += 1
                elif size < 10 * 1024:
                    size_ranges["1KB-10KB"] += 1
                elif size < 100 * 1024:
                    size_ranges["10KB-100KB"] += 1
                elif size < 1024 * 1024:
                    size_ranges["100KB-1MB"] += 1
                elif size < 10 * 1024 * 1024:
                    size_ranges["1MB-10MB"] += 1
                else:
                    size_ranges["10MB+"] += 1

            # Restore original folder if we changed it
            if folder_name != original_folder and mailbox:
                mailbox.folder.set(original_folder)

            return {
                "message": f"Size distribution for folder '{folder_name}'",
                "folder": folder_name,
                "total_messages": len(all_messages),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "average_size_bytes": round(avg_size, 2),
                "average_size_kb": round(avg_size / 1024, 2),
                "max_size_bytes": max_size,
                "max_size_mb": round(max_size / (1024 * 1024), 2),
                "min_size_bytes": min_size,
                "size_distribution": size_ranges,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get folder size distribution: {e!s}"

    @mcp.tool()
    async def get_folder_date_distribution(folder_name: str = ""):
        """
        Get email date distribution for a folder.

        Args:
            folder_name: Name of the folder (empty for current folder)
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Use current folder if none specified
            original_folder = mailbox.folder.get() or "INBOX"
            if folder_name and folder_name != str(original_folder):
                mailbox.folder.set(folder_name)
            else:
                folder_name = str(original_folder)

            # Get all messages
            all_messages = list(mailbox.fetch(headers_only=True))

            if not all_messages:
                return {
                    "message": f"No messages in folder '{folder_name}'",
                    "folder": folder_name,
                    "total_messages": 0,
                }

            # Calculate date statistics
            dates = []
            for msg in all_messages:
                if msg.date:
                    dates.append(msg.date)

            if not dates:
                return {
                    "message": f"No messages with valid dates in folder '{folder_name}'",
                    "folder": folder_name,
                    "total_messages": len(all_messages),
                }

            # Sort dates
            dates.sort()

            # Calculate date ranges
            oldest_date = dates[0]
            newest_date = dates[-1]
            date_range = newest_date - oldest_date

            # Create monthly distribution
            monthly_distribution = {}
            for date in dates:
                month_key = f"{date.year}-{date.month:02d}"
                monthly_distribution[month_key] = (
                    monthly_distribution.get(month_key, 0) + 1
                )

            # Restore original folder if we changed it
            if folder_name != original_folder and mailbox:
                mailbox.folder.set(original_folder)

            return {
                "message": f"Date distribution for folder '{folder_name}'",
                "folder": folder_name,
                "total_messages": len(all_messages),
                "messages_with_dates": len(dates),
                "oldest_date": oldest_date.isoformat(),
                "newest_date": newest_date.isoformat(),
                "date_range_days": date_range.days,
                "monthly_distribution": monthly_distribution,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get folder date distribution: {e!s}"

    @mcp.tool()
    async def get_top_senders(folder_name: str = "", limit: int = 10):
        """
        Get top senders by email count in a folder.

        Args:
            folder_name: Name of the folder (empty for current folder)
            limit: Number of top senders to return (default: 10)
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Use current folder if none specified
            original_folder = mailbox.folder.get() or "INBOX"
            if folder_name and folder_name != str(original_folder):
                mailbox.folder.set(folder_name)
            else:
                folder_name = str(original_folder)

            # Get all messages
            all_messages = list(mailbox.fetch(headers_only=True))

            if not all_messages:
                return {
                    "message": f"No messages in folder '{folder_name}'",
                    "folder": folder_name,
                    "total_messages": 0,
                }

            # Count emails by sender
            sender_counts: dict[str, int] = {}
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
            if folder_name != original_folder and mailbox:
                mailbox.folder.set(original_folder)

            return {
                "message": f"Top {len(top_senders_with_percentage)} senders in folder '{folder_name}'",
                "folder": folder_name,
                "total_messages": total_messages,
                "top_senders": top_senders_with_percentage,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get top senders: {e!s}"
