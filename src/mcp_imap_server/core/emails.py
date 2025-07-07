"""Email management tools for IMAP server."""

import os
from datetime import datetime
from pathlib import Path
from imap_tools import AND, OR, MailMessageFlags
from mcp.server.fastmcp import FastMCP
from .state import get_state_or_error


def register_email_tools(mcp: FastMCP):
    """Register email-related tools with the MCP server."""

    @mcp.tool()
    async def list_emails(list_unread_only: bool = False):
        """
        List emails in the current folder.

        Args:
            list_unread_only: If True, only list unread emails, otherwise list all emails.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        if list_unread_only:
            # Only fetch unread emails
            messages = state.mailbox.fetch(AND("UNSEEN"))
        else:
            # Fetch all emails (don't use AND with empty criteria)
            messages = state.mailbox.fetch()

        return [
            {"uid": msg.uid, "from": msg.from_, "subject": msg.subject}
            for msg in messages
        ]

    @mcp.tool()
    async def filter_emails_by_sender(sender: str, list_unread_only: bool = False):
        """
        List emails from a specific sender.

        Args:
            sender: Email address of the sender to filter by.
            list_unread_only: If True, only show unread emails from this sender.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        criteria = [f'(FROM "{sender}")']
        if list_unread_only:
            criteria.append("UNSEEN")

        messages = state.mailbox.fetch(AND(*criteria))
        return [
            {"uid": msg.uid, "from": msg.from_, "subject": msg.subject}
            for msg in messages
        ]

    @mcp.tool()
    async def filter_emails_by_subject(subject: str, list_unread_only: bool = False):
        """
        List emails containing specific text in the subject.

        Args:
            subject: Text to search for in email subjects.
            list_unread_only: If True, only show unread emails with this subject.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        criteria = [f'(SUBJECT "{subject}")']
        if list_unread_only:
            criteria.append("UNSEEN")

        messages = state.mailbox.fetch(AND(*criteria))
        return [
            {"uid": msg.uid, "from": msg.from_, "subject": msg.subject}
            for msg in messages
        ]

    # ADVANCED SEARCH & FILTERING
    @mcp.tool()
    async def search_emails_by_date_range(
        start_date: str, end_date: str = "", headers_only: bool = True
    ):
        """
        Search emails within a specific date range.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (optional, defaults to start_date)
            headers_only: If True, only fetch headers for faster search (default: True)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Parse dates
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else start

            # Build search criteria
            if start == end:
                criteria = AND(date=start)
            else:
                criteria = AND(date_gte=start, date_lt=end)

            # Fetch messages
            messages = state.mailbox.fetch(criteria, headers_only=headers_only)

            results = []
            for msg in messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
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
                "message": f"Found {len(results)} emails between {start_date} and {end_date or start_date}",
                "start_date": start_date,
                "end_date": end_date or start_date,
                "count": len(results),
                "headers_only": headers_only,
                "emails": results,
            }

        except ValueError as e:
            return f"Invalid date format. Use YYYY-MM-DD format. Error: {str(e)}"
        except Exception as e:
            return f"Failed to search emails by date: {str(e)}"

    @mcp.tool()
    async def search_emails_by_size(
        min_size: int = 0, max_size: int = 0, headers_only: bool = True
    ):
        """
        Search emails by size range.

        Args:
            min_size: Minimum size in bytes (0 for no minimum)
            max_size: Maximum size in bytes (0 for no maximum)
            headers_only: If True, only fetch headers for faster search (default: True)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Build search criteria based on size constraints
            criteria_parts = []

            if min_size > 0:
                criteria_parts.append(f"size_gt={min_size}")
            if max_size > 0:
                criteria_parts.append(f"size_lt={max_size}")

            if not criteria_parts:
                return "Please specify min_size and/or max_size greater than 0."

            # Create search criteria
            if len(criteria_parts) == 1:
                if min_size > 0:
                    criteria = AND(size_gt=min_size)
                else:
                    criteria = AND(size_lt=max_size)
            else:
                criteria = AND(size_gt=min_size, size_lt=max_size)

            # Fetch messages
            messages = state.mailbox.fetch(criteria, headers_only=headers_only)

            results = []
            for msg in messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
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

            size_filter = f"{min_size}-{max_size}" if max_size > 0 else f">{min_size}"
            return {
                "message": f"Found {len(results)} emails with size {size_filter} bytes",
                "min_size": min_size,
                "max_size": max_size,
                "count": len(results),
                "headers_only": headers_only,
                "emails": results,
            }

        except Exception as e:
            return f"Failed to search emails by size: {str(e)}"

    @mcp.tool()
    async def search_emails_by_body_text(
        search_text: str,
        search_body: bool = True,
        search_subject: bool = False,
        headers_only: bool = False,
    ):
        """
        Search emails containing specific text in body and/or subject.

        Args:
            search_text: Text to search for
            search_body: Search in email body (default: True)
            search_subject: Search in subject line (default: False)
            headers_only: If True, only fetch headers (default: False, since we're searching content)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Build search criteria
            if search_body and search_subject:
                criteria = OR(body=search_text, subject=search_text)
            elif search_body:
                criteria = AND(body=search_text)
            elif search_subject:
                criteria = AND(subject=search_text)
            else:
                return "Please enable search_body and/or search_subject."

            # Fetch messages
            messages = state.mailbox.fetch(criteria, headers_only=headers_only)

            results = []
            for msg in messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                }
                if not headers_only:
                    result.update(
                        {
                            "text": msg.text[:200] + "..."
                            if msg.text and len(msg.text) > 200
                            else msg.text,
                            "html": msg.html[:200] + "..."
                            if msg.html and len(msg.html) > 200
                            else msg.html,
                            "attachment_count": len(msg.attachments),
                        }
                    )
                results.append(result)

            search_location = []
            if search_body:
                search_location.append("body")
            if search_subject:
                search_location.append("subject")

            return {
                "message": f"Found {len(results)} emails containing '{search_text}' in {' and '.join(search_location)}",
                "search_text": search_text,
                "search_locations": search_location,
                "count": len(results),
                "headers_only": headers_only,
                "emails": results,
            }

        except Exception as e:
            return f"Failed to search emails by text: {str(e)}"

    @mcp.tool()
    async def search_emails_with_attachments(
        min_attachments: int = 1, headers_only: bool = True
    ):
        """
        Find emails that have attachments.

        Args:
            min_attachments: Minimum number of attachments (default: 1)
            headers_only: If True, only fetch headers for faster search (default: True)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Fetch all messages and filter by attachment count
            # Note: IMAP doesn't have a direct "has attachments" search, so we fetch and filter
            messages = state.mailbox.fetch(headers_only=headers_only)

            results = []
            for msg in messages:
                attachment_count = len(msg.attachments)
                if attachment_count >= min_attachments:
                    result = {
                        "uid": msg.uid,
                        "from": msg.from_,
                        "subject": msg.subject,
                        "date": msg.date_str,
                        "size": msg.size,
                        "attachment_count": attachment_count,
                    }
                    if not headers_only:
                        result.update({"text": msg.text, "html": msg.html})
                    results.append(result)

            return {
                "message": f"Found {len(results)} emails with {min_attachments}+ attachments",
                "min_attachments": min_attachments,
                "count": len(results),
                "headers_only": headers_only,
                "emails": results,
            }

        except Exception as e:
            return f"Failed to search emails with attachments: {str(e)}"

    @mcp.tool()
    async def search_emails_by_flags(
        seen: bool = None,
        flagged: bool = None,
        deleted: bool = None,
        draft: bool = None,
        answered: bool = None,
        headers_only: bool = True,
    ):
        """
        Search emails by their flags.

        Args:
            seen: True for read emails, False for unread, None to ignore
            flagged: True for flagged emails, False for unflagged, None to ignore
            deleted: True for deleted emails, False for not deleted, None to ignore
            draft: True for draft emails, False for not draft, None to ignore
            answered: True for answered emails, False for not answered, None to ignore
            headers_only: If True, only fetch headers for faster search (default: True)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Build search criteria based on flags
            criteria_kwargs = {}
            flag_descriptions = []

            if seen is not None:
                criteria_kwargs["seen"] = seen
                flag_descriptions.append(f"{'read' if seen else 'unread'}")

            if flagged is not None:
                criteria_kwargs["flagged"] = flagged
                flag_descriptions.append(f"{'flagged' if flagged else 'unflagged'}")

            if deleted is not None:
                criteria_kwargs["deleted"] = deleted
                flag_descriptions.append(f"{'deleted' if deleted else 'not deleted'}")

            if draft is not None:
                criteria_kwargs["draft"] = draft
                flag_descriptions.append(f"{'draft' if draft else 'not draft'}")

            if answered is not None:
                criteria_kwargs["answered"] = answered
                flag_descriptions.append(
                    f"{'answered' if answered else 'not answered'}"
                )

            if not criteria_kwargs:
                return "Please specify at least one flag filter (seen, flagged, deleted, draft, answered)."

            # Create search criteria
            criteria = AND(**criteria_kwargs)

            # Fetch messages
            messages = state.mailbox.fetch(criteria, headers_only=headers_only)

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
                "message": f"Found {len(results)} emails that are {' and '.join(flag_descriptions)}",
                "flag_criteria": flag_descriptions,
                "count": len(results),
                "headers_only": headers_only,
                "emails": results,
            }

        except Exception as e:
            return f"Failed to search emails by flags: {str(e)}"

    @mcp.tool()
    async def advanced_email_search(
        sender: str = "",
        subject: str = "",
        body_text: str = "",
        start_date: str = "",
        end_date: str = "",
        min_size: int = 0,
        max_size: int = 0,
        has_attachments: bool = None,
        is_unread: bool = None,
        is_flagged: bool = None,
        headers_only: bool = True,
    ):
        """
        Advanced email search combining multiple criteria.

        Args:
            sender: Sender email address to search for
            subject: Text to search in subject line
            body_text: Text to search in email body
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            min_size: Minimum size in bytes
            max_size: Maximum size in bytes
            has_attachments: True to find emails with attachments, False without, None to ignore
            is_unread: True for unread emails, False for read, None to ignore
            is_flagged: True for flagged emails, False for unflagged, None to ignore
            headers_only: If True, only fetch headers for faster search (default: True)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Build search criteria
            criteria_parts = []
            search_description = []

            if sender:
                criteria_parts.append(AND(from_=sender))
                search_description.append(f"from '{sender}'")

            if subject:
                criteria_parts.append(AND(subject=subject))
                search_description.append(f"subject containing '{subject}'")

            if body_text:
                criteria_parts.append(AND(body=body_text))
                search_description.append(f"body containing '{body_text}'")

            if start_date:
                try:
                    start = datetime.strptime(start_date, "%Y-%m-%d").date()
                    if end_date:
                        end = datetime.strptime(end_date, "%Y-%m-%d").date()
                        criteria_parts.append(AND(date_gte=start, date_lt=end))
                        search_description.append(
                            f"between {start_date} and {end_date}"
                        )
                    else:
                        criteria_parts.append(AND(date=start))
                        search_description.append(f"on {start_date}")
                except ValueError:
                    return "Invalid date format. Use YYYY-MM-DD format."

            if min_size > 0:
                criteria_parts.append(AND(size_gt=min_size))
                search_description.append(f"larger than {min_size} bytes")

            if max_size > 0:
                criteria_parts.append(AND(size_lt=max_size))
                search_description.append(f"smaller than {max_size} bytes")

            if is_unread is not None:
                criteria_parts.append(AND(seen=not is_unread))
                search_description.append("unread" if is_unread else "read")

            if is_flagged is not None:
                criteria_parts.append(AND(flagged=is_flagged))
                search_description.append("flagged" if is_flagged else "unflagged")

            if not criteria_parts:
                return "Please specify at least one search criterion."

            # Combine all criteria with AND
            if len(criteria_parts) == 1:
                final_criteria = criteria_parts[0]
            else:
                final_criteria = AND(*[c for c in criteria_parts])

            # Fetch messages
            messages = state.mailbox.fetch(final_criteria, headers_only=headers_only)

            results = []
            for msg in messages:
                # Filter by attachments if specified (since IMAP doesn't support this natively)
                if has_attachments is not None:
                    attachment_count = len(msg.attachments)
                    if has_attachments and attachment_count == 0:
                        continue
                    if not has_attachments and attachment_count > 0:
                        continue

                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "attachment_count": len(msg.attachments),
                    "flags": list(msg.flags),
                }
                if not headers_only:
                    result.update(
                        {
                            "text": msg.text[:200] + "..."
                            if msg.text and len(msg.text) > 200
                            else msg.text,
                            "html": msg.html[:200] + "..."
                            if msg.html and len(msg.html) > 200
                            else msg.html,
                        }
                    )
                results.append(result)

            if has_attachments is not None:
                search_description.append(
                    "with attachments" if has_attachments else "without attachments"
                )

            return {
                "message": f"Found {len(results)} emails matching advanced search criteria",
                "search_criteria": search_description,
                "count": len(results),
                "headers_only": headers_only,
                "emails": results,
            }

        except Exception as e:
            return f"Failed to perform advanced search: {str(e)}"

    @mcp.tool()
    async def get_recent_emails(count: int = 10, headers_only: bool = True):
        """
        Get the most recent emails from the current folder.

        Args:
            count: Number of recent emails to retrieve (default: 10)
            headers_only: If True, only fetch headers for faster retrieval (default: True)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Fetch emails in reverse order (most recent first) with limit
            messages = state.mailbox.fetch(
                reverse=True, limit=count, headers_only=headers_only
            )

            results = []
            for msg in messages:
                result = {
                    "uid": msg.uid,
                    "from": msg.from_,
                    "subject": msg.subject,
                    "date": msg.date_str,
                    "size": msg.size,
                    "attachment_count": len(msg.attachments),
                }
                if not headers_only:
                    result.update({"text": msg.text, "html": msg.html})
                results.append(result)

            return {
                "message": f"Retrieved {len(results)} most recent emails",
                "count": len(results),
                "requested_count": count,
                "headers_only": headers_only,
                "emails": results,
            }

        except Exception as e:
            return f"Failed to get recent emails: {str(e)}"

    @mcp.tool()
    async def read_email(uid: str):
        """
        Read the content of a specific email.

        Args:
            uid: The UID of the email to read.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        for msg in state.mailbox.fetch(AND(uid=uid)):
            return {
                "from": msg.from_,
                "subject": msg.subject,
                "date": msg.date_str,
                "text": msg.text,
                "html": msg.html,
            }
        return "Email not found."

    @mcp.tool()
    async def extract_attachments(uid: str, save_directory: str = "./attachments"):
        """
        Extract and save all attachments from a specific email.

        Args:
            uid: The UID of the email to extract attachments from.
            save_directory: Directory to save attachments to (default: ./attachments).
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Create save directory if it doesn't exist
            save_path = Path(save_directory)
            save_path.mkdir(parents=True, exist_ok=True)

            # Find the email
            message = None
            for msg in state.mailbox.fetch(AND(uid=uid)):
                message = msg
                break

            if not message:
                return f"Email with UID {uid} not found."

            # Extract attachments
            extracted_files = []
            attachment_count = 0

            for attachment in message.attachments:
                attachment_count += 1

                # Get filename, or create one if not available
                filename = attachment.filename
                if not filename:
                    # Create filename based on content type
                    extension = ""
                    if attachment.content_type:
                        if attachment.content_type.startswith("image/"):
                            extension = f".{attachment.content_type.split('/')[-1]}"
                        elif attachment.content_type == "application/pdf":
                            extension = ".pdf"
                        elif attachment.content_type.startswith("text/"):
                            extension = ".txt"
                    filename = f"attachment_{attachment_count}{extension}"

                # Ensure filename is safe for filesystem
                safe_filename = "".join(
                    c for c in filename if c.isalnum() or c in "._-"
                )
                if not safe_filename:
                    safe_filename = f"attachment_{attachment_count}"

                # Handle duplicate filenames
                file_path = save_path / safe_filename
                counter = 1
                while file_path.exists():
                    name, ext = os.path.splitext(safe_filename)
                    file_path = save_path / f"{name}_{counter}{ext}"
                    counter += 1

                # Save the attachment
                with open(file_path, "wb") as f:
                    f.write(attachment.payload)

                extracted_files.append(
                    {
                        "filename": file_path.name,
                        "path": str(file_path),
                        "size": len(attachment.payload),
                        "content_type": attachment.content_type or "unknown",
                        "original_filename": attachment.filename or "unknown",
                    }
                )

            if not extracted_files:
                return f"No attachments found in email {uid}."

            return {
                "message": f"Successfully extracted {len(extracted_files)} attachment(s) from email {uid}",
                "save_directory": str(save_path.absolute()),
                "files": extracted_files,
            }

        except Exception as e:
            return f"Failed to extract attachments from email {uid}: {str(e)}"

    @mcp.tool()
    async def list_email_attachments(uid: str):
        """
        List all attachments in a specific email without downloading them.

        Args:
            uid: The UID of the email to check for attachments.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Find the email
            message = None
            for msg in state.mailbox.fetch(AND(uid=uid)):
                message = msg
                break

            if not message:
                return f"Email with UID {uid} not found."

            # List attachments
            attachments_info = []
            attachment_count = 0

            for attachment in message.attachments:
                attachment_count += 1
                attachments_info.append(
                    {
                        "filename": attachment.filename
                        or f"attachment_{attachment_count}",
                        "content_type": attachment.content_type or "unknown",
                        "size": len(attachment.payload),
                        "content_id": getattr(attachment, "content_id", None),
                        "content_disposition": getattr(
                            attachment, "content_disposition", None
                        ),
                    }
                )

            if not attachments_info:
                return f"No attachments found in email {uid}."

            return {
                "email_uid": uid,
                "email_subject": message.subject,
                "email_from": message.from_,
                "attachment_count": len(attachments_info),
                "attachments": attachments_info,
            }

        except Exception as e:
            return f"Failed to list attachments for email {uid}: {str(e)}"

    # BULK OPERATIONS
    @mcp.tool()
    async def bulk_mark_as_read(uid_list: str, chunk_size: int = 100):
        """
        Mark multiple emails as read in bulk.

        Args:
            uid_list: Comma-separated list of email UIDs to mark as read
            chunk_size: Number of emails to process per IMAP command (default: 100)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Parse UID list
            uids = [uid.strip() for uid in uid_list.split(",") if uid.strip()]
            if not uids:
                return "No valid UIDs provided."

            # Mark as read in chunks for better performance
            state.mailbox.flag(uids, MailMessageFlags.SEEN, True, chunks=chunk_size)

            return {
                "message": f"Successfully marked {len(uids)} emails as read",
                "processed_count": len(uids),
                "chunk_size": chunk_size,
                "uids": uids,
            }

        except Exception as e:
            return f"Failed to mark emails as read: {str(e)}"

    @mcp.tool()
    async def bulk_mark_as_unread(uid_list: str, chunk_size: int = 100):
        """
        Mark multiple emails as unread in bulk.

        Args:
            uid_list: Comma-separated list of email UIDs to mark as unread
            chunk_size: Number of emails to process per IMAP command (default: 100)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Parse UID list
            uids = [uid.strip() for uid in uid_list.split(",") if uid.strip()]
            if not uids:
                return "No valid UIDs provided."

            # Mark as unread in chunks
            state.mailbox.flag(uids, MailMessageFlags.SEEN, False, chunks=chunk_size)

            return {
                "message": f"Successfully marked {len(uids)} emails as unread",
                "processed_count": len(uids),
                "chunk_size": chunk_size,
                "uids": uids,
            }

        except Exception as e:
            return f"Failed to mark emails as unread: {str(e)}"

    @mcp.tool()
    async def bulk_delete_emails(uid_list: str, chunk_size: int = 100):
        """
        Delete multiple emails in bulk.

        Args:
            uid_list: Comma-separated list of email UIDs to delete
            chunk_size: Number of emails to process per IMAP command (default: 100)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Parse UID list
            uids = [uid.strip() for uid in uid_list.split(",") if uid.strip()]
            if not uids:
                return "No valid UIDs provided."

            # Delete in chunks for better performance
            state.mailbox.delete(uids, chunks=chunk_size)

            return {
                "message": f"Successfully deleted {len(uids)} emails",
                "processed_count": len(uids),
                "chunk_size": chunk_size,
                "uids": uids,
            }

        except Exception as e:
            return f"Failed to delete emails: {str(e)}"

    @mcp.tool()
    async def bulk_move_emails(
        uid_list: str, destination_folder: str, chunk_size: int = 100
    ):
        """
        Move multiple emails to a specified folder in bulk.

        Args:
            uid_list: Comma-separated list of email UIDs to move
            destination_folder: The name of the destination folder
            chunk_size: Number of emails to process per IMAP command (default: 100)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Parse UID list
            uids = [uid.strip() for uid in uid_list.split(",") if uid.strip()]
            if not uids:
                return "No valid UIDs provided."

            # Check if destination folder exists, create it if it doesn't
            if not state.mailbox.folder.exists(destination_folder):
                state.mailbox.folder.create(destination_folder)

            # Move emails in chunks for better performance
            state.mailbox.move(uids, destination_folder, chunks=chunk_size)

            return {
                "message": f"Successfully moved {len(uids)} emails to '{destination_folder}'",
                "processed_count": len(uids),
                "destination_folder": destination_folder,
                "chunk_size": chunk_size,
                "uids": uids,
            }

        except Exception as e:
            return f"Failed to move emails: {str(e)}"

    @mcp.tool()
    async def bulk_copy_emails(
        uid_list: str, destination_folder: str, chunk_size: int = 100
    ):
        """
        Copy multiple emails to a specified folder in bulk.

        Args:
            uid_list: Comma-separated list of email UIDs to copy
            destination_folder: The name of the destination folder
            chunk_size: Number of emails to process per IMAP command (default: 100)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Parse UID list
            uids = [uid.strip() for uid in uid_list.split(",") if uid.strip()]
            if not uids:
                return "No valid UIDs provided."

            # Check if destination folder exists, create it if it doesn't
            if not state.mailbox.folder.exists(destination_folder):
                state.mailbox.folder.create(destination_folder)

            # Copy emails in chunks for better performance
            state.mailbox.copy(uids, destination_folder, chunks=chunk_size)

            return {
                "message": f"Successfully copied {len(uids)} emails to '{destination_folder}'",
                "processed_count": len(uids),
                "destination_folder": destination_folder,
                "chunk_size": chunk_size,
                "uids": uids,
            }

        except Exception as e:
            return f"Failed to copy emails: {str(e)}"

    @mcp.tool()
    async def bulk_flag_emails(
        uid_list: str, flag_name: str, set_flag: bool = True, chunk_size: int = 100
    ):
        """
        Add or remove flags from multiple emails in bulk.

        Args:
            uid_list: Comma-separated list of email UIDs to flag
            flag_name: Flag to set/unset (seen, flagged, deleted, draft, answered, or custom)
            set_flag: True to add flag, False to remove flag (default: True)
            chunk_size: Number of emails to process per IMAP command (default: 100)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Parse UID list
            uids = [uid.strip() for uid in uid_list.split(",") if uid.strip()]
            if not uids:
                return "No valid UIDs provided."

            # Map common flag names to IMAP flags
            flag_mapping = {
                "seen": MailMessageFlags.SEEN,
                "flagged": MailMessageFlags.FLAGGED,
                "deleted": MailMessageFlags.DELETED,
                "draft": MailMessageFlags.DRAFT,
                "answered": MailMessageFlags.ANSWERED,
            }

            # Get the actual flag to use
            flag = flag_mapping.get(flag_name.lower(), flag_name)

            # Set/unset flags in chunks for better performance
            state.mailbox.flag(uids, flag, set_flag, chunks=chunk_size)

            action = "set" if set_flag else "removed"
            return {
                "message": f"Successfully {action} '{flag_name}' flag on {len(uids)} emails",
                "processed_count": len(uids),
                "flag_name": flag_name,
                "flag_set": set_flag,
                "chunk_size": chunk_size,
                "uids": uids,
            }

        except Exception as e:
            return f"Failed to flag emails: {str(e)}"

    @mcp.tool()
    async def mark_as_read(uid: str):
        """
        Mark an email as read.

        Args:
            uid: The UID of the email to mark as read.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        state.mailbox.flag(uid, r"\Seen", True)
        return f"Email {uid} marked as read."

    @mcp.tool()
    async def delete_email(uid: str):
        """
        Delete an email.

        Args:
            uid: The UID of the email to delete.
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        state.mailbox.delete(uid)
        return f"Email {uid} deleted."
