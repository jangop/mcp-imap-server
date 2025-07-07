"""Email management tools for IMAP server."""

import os
from pathlib import Path
from imap_tools import AND, MailMessageFlags
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
