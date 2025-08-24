"""Email attachment tools for IMAP server."""

import imaplib
from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP
from ..state import get_mailbox


def register_email_attachment_tools(mcp: FastMCP):
    """Register email attachment tools with the MCP server."""

    @mcp.tool()
    async def extract_attachments(
        uid: int, save_path: str = "", include_inline: bool = False
    ) -> dict[str, Any] | str:
        """
        Extract attachments from a specific email.

        Args:
            uid: Email UID
            save_path: Directory to save attachments (optional)
            include_inline: Include inline attachments (default: False)
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

            if not message.attachments:
                return {
                    "message": f"No attachments found in email UID {uid}",
                    "email_subject": message.subject,
                    "attachment_count": 0,
                    "attachments": [],
                }

            # Filter attachments based on include_inline
            attachments_to_process = []
            for att in message.attachments:
                is_inline = att.content_disposition == "inline"
                if include_inline or not is_inline:
                    attachments_to_process.append(att)

            if not attachments_to_process:
                return {
                    "message": f"No {'non-inline ' if not include_inline else ''}attachments found in email UID {uid}",
                    "email_subject": message.subject,
                    "attachment_count": 0,
                    "attachments": [],
                }

            saved_files = []
            for i, attachment in enumerate(attachments_to_process):
                filename = None  # Initialize filename variable
                try:
                    # Generate filename if not provided
                    if attachment.filename:
                        filename = attachment.filename
                    else:
                        # Create a filename based on content type and index
                        ext = (
                            attachment.content_type.split("/")[-1]
                            if "/" in attachment.content_type
                            else "bin"
                        )
                        filename = f"attachment_{i + 1}.{ext}"

                    # Save to specified path or current directory
                    if save_path:
                        save_dir = Path(save_path)
                        save_dir.mkdir(parents=True, exist_ok=True)
                        file_path = save_dir / filename
                    else:
                        file_path = Path(filename)

                    # Write attachment data
                    with open(file_path, "wb") as f:
                        f.write(attachment.payload)

                    saved_files.append(
                        {
                            "filename": filename,
                            "path": str(file_path),
                            "size": len(attachment.payload),
                            "content_type": attachment.content_type,
                            "content_id": attachment.content_id,
                        }
                    )

                except Exception as e:
                    saved_files.append(
                        {
                            "filename": filename if filename else f"attachment_{i + 1}",
                            "error": f"Failed to save: {e!s}",
                            "size": len(attachment.payload),
                            "content_type": attachment.content_type,
                        }
                    )

            return {
                "message": f"Successfully extracted {len(saved_files)} attachments from email UID {uid}",
                "email_subject": message.subject,
                "email_uid": uid,
                "attachment_count": len(saved_files),
                "saved_files": saved_files,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to extract attachments: {e!s}"

    @mcp.tool()
    async def list_attachments(uid: int) -> dict[str, Any] | str:
        """
        List attachments for a specific email without extracting them.

        Args:
            uid: Email UID
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

            if not message.attachments:
                return {
                    "message": f"No attachments found in email UID {uid}",
                    "email_subject": message.subject,
                    "email_uid": uid,
                    "attachment_count": 0,
                    "attachments": [],
                }

            attachments_info = []
            for i, attachment in enumerate(message.attachments):
                attachments_info.append(
                    {
                        "index": i + 1,
                        "filename": attachment.filename or f"attachment_{i + 1}",
                        "content_type": attachment.content_type,
                        "size": len(attachment.payload) if attachment.payload else 0,
                        "content_id": attachment.content_id,
                        "content_disposition": attachment.content_disposition,
                    }
                )

            return {
                "message": f"Found {len(attachments_info)} attachments in email UID {uid}",
                "email_subject": message.subject,
                "email_uid": uid,
                "attachment_count": len(attachments_info),
                "attachments": attachments_info,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to list attachments: {e!s}"
