"""Email basic operations tools for IMAP server."""

import imaplib
from datetime import datetime, UTC
from imap_tools.query import AND
from mcp.server.fastmcp import FastMCP
from ..state import get_mailbox


def register_email_basic_operations_tools(mcp: FastMCP):
    """Register email basic operations tools with the MCP server."""

    @mcp.tool()
    async def list_emails(limit: int = 10, headers_only: bool = True):
        """
        List recent emails from the current folder.

        Args:
            limit: Maximum number of emails to return (default: 10)
            headers_only: If True, only fetch headers for faster loading (default: True)
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Fetch all messages to sort by date, then take the most recent
            all_messages = list(mailbox.fetch(headers_only=headers_only))

            # Sort by date (most recent first) - handle timezone-aware dates properly
            def get_sort_date(msg):
                if msg.date is None:
                    return datetime.min.replace(tzinfo=UTC)
                # If date is timezone-naive, assume UTC
                if msg.date.tzinfo is None:
                    return msg.date.replace(tzinfo=UTC)
                return msg.date

            sorted_messages = sorted(
                all_messages,
                key=lambda msg: get_sort_date(msg),
                reverse=True,
            )

            # Take the most recent ones
            recent_messages = sorted_messages[:limit]

            results = []
            for msg in recent_messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "flags": list(msg.flags),
                }
                if not headers_only:
                    result.update(
                        {
                            "text": msg.text,
                            "html": msg.html,
                            "attachment_count": len(msg.attachments),
                        }
                    )
                results.append(result)

            return {
                "message": f"Retrieved {len(results)} emails",
                "folder": mailbox.folder,
                "count": len(results),
                "limit": limit,
                "headers_only": headers_only,
                "emails": results,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to list emails: {e!s}"

    @mcp.tool()
    async def filter_emails_by_sender(
        sender: str, limit: int = 10, headers_only: bool = True
    ):
        """
        Filter emails by sender address.

        Args:
            sender: Sender email address to filter by
            limit: Maximum number of emails to return (default: 10)
            headers_only: If True, only fetch headers for faster loading (default: True)
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Create search criteria for sender
            criteria = AND(from_=sender)

            # Fetch messages
            messages = mailbox.fetch(
                criteria, limit=limit, headers_only=headers_only
            )

            results = []
            for msg in messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "flags": list(msg.flags),
                }
                if not headers_only:
                    result.update(
                        {
                            "text": msg.text,
                            "html": msg.html,
                            "attachment_count": len(msg.attachments),
                        }
                    )
                results.append(result)

            return {
                "message": f"Found {len(results)} emails from '{sender}'",
                "sender": sender,
                "folder": mailbox.folder,
                "count": len(results),
                "limit": limit,
                "headers_only": headers_only,
                "emails": results,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to filter emails by sender: {e!s}"

    @mcp.tool()
    async def filter_emails_by_subject(
        subject: str, limit: int = 10, headers_only: bool = True
    ):
        """
        Filter emails by subject line (partial match).

        Args:
            subject: Subject text to search for
            limit: Maximum number of emails to return (default: 10)
            headers_only: If True, only fetch headers for faster loading (default: True)
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Create search criteria for subject
            criteria = AND(subject=subject)

            # Fetch messages
            messages = mailbox.fetch(
                criteria, limit=limit, headers_only=headers_only
            )

            results = []
            for msg in messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "flags": list(msg.flags),
                }
                if not headers_only:
                    result.update(
                        {
                            "text": msg.text,
                            "html": msg.html,
                            "attachment_count": len(msg.attachments),
                        }
                    )
                results.append(result)

            return {
                "message": f"Found {len(results)} emails with subject containing '{subject}'",
                "subject_filter": subject,
                "folder": mailbox.folder,
                "count": len(results),
                "limit": limit,
                "headers_only": headers_only,
                "emails": results,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to filter emails by subject: {e!s}"

    @mcp.tool()
    async def get_recent_emails(count: int = 5, headers_only: bool = True):
        """
        Get the most recent emails from the current folder.

        Args:
            count: Number of recent emails to retrieve (default: 5)
            headers_only: If True, only fetch headers for faster loading (default: True)
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Fetch all messages to sort by date, then take the most recent
            all_messages = list(mailbox.fetch(headers_only=headers_only))

            # Sort by date (most recent first) - handle timezone-aware dates properly
            def get_sort_date(msg):
                if msg.date is None:
                    return datetime.min.replace(tzinfo=UTC)
                # If date is timezone-naive, assume UTC
                if msg.date.tzinfo is None:
                    return msg.date.replace(tzinfo=UTC)
                return msg.date

            sorted_messages = sorted(
                all_messages,
                key=lambda msg: get_sort_date(msg),
                reverse=True,
            )

            # Take the most recent ones
            recent_messages = sorted_messages[:count]

            results = []
            for msg in recent_messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "flags": list(msg.flags),
                }
                if not headers_only:
                    result.update(
                        {
                            "text": msg.text,
                            "html": msg.html,
                            "attachment_count": len(msg.attachments),
                        }
                    )
                results.append(result)

            return {
                "message": f"Retrieved {len(results)} most recent emails",
                "folder": mailbox.folder,
                "count": len(results),
                "requested_count": count,
                "headers_only": headers_only,
                "emails": results,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to get recent emails: {e!s}"

    @mcp.tool()
    async def read_email(uid: int):
        """
        Read a specific email by its UID and return full content.

        Args:
            uid: Email UID to read
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Get the specific message using UID criteria
            message = None
            for msg in mailbox.fetch(f"UID {uid}"):
                message = msg
                break

            if not message:
                return f"Email with UID {uid} not found."

            return {
                "message": f"Email content for UID {uid}",
                "uid": uid,
                "from": message.from_,
                "to": message.to,
                "cc": message.cc,
                "bcc": message.bcc,
                "subject": message.subject,
                "date": message.date_str,
                "size": message.size,
                "flags": list(message.flags),
                "text": message.text,
                "html": message.html,
                "attachment_count": len(message.attachments),
                "attachments": [
                    {
                        "filename": att.filename or "unnamed",
                        "content_type": att.content_type,
                        "size": len(att.payload) if att.payload else 0,
                    }
                    for att in message.attachments
                ],
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to read email: {e!s}"

    @mcp.tool()
    async def mark_email_as_read(uid: int):
        """
        Mark a specific email as read.

        Args:
            uid: Email UID to mark as read
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Mark as read
            mailbox.flag(str(uid), r"\Seen", True)

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to mark email as read: {e!s}"
        else:
            return {
                "message": f"Successfully marked email UID {uid} as read",
                "uid": uid,
                "operation": "mark_as_read",
            }

    @mcp.tool()
    async def delete_email(uid: int):
        """
        Delete a specific email.

        Args:
            uid: Email UID to delete
        """
        mailbox = get_mailbox(mcp.get_context())

        try:
            # Delete the email
            mailbox.flag(str(uid), r"\Deleted", True)
            mailbox.expunge()

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to delete email: {e!s}"
        else:
            return {
                "message": f"Successfully deleted email UID {uid}",
                "uid": uid,
                "operation": "delete",
            }
