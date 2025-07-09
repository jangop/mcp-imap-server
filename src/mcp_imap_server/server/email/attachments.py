"""Email attachment tools for IMAP server."""

import base64
import imaplib
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from ..state import get_state_or_error


def register_email_attachment_tools(mcp: FastMCP):
    """Register email attachment tools with the MCP server."""

    @mcp.tool()
    async def extract_attachments(
        uid: int, save_path: str = "", include_inline: bool = False
    ):
        """
        Extract attachments from a specific email.

        Args:
            uid: Email UID
            save_path: Directory to save attachments (optional)
            include_inline: Include inline attachments (default: False)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Get the specific message using UID criteria
            message = None
            for msg in state.mailbox.fetch(f"UID {uid}"):
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
                if include_inline or not att.is_inline:
                    attachments_to_process.append(att)

            if not attachments_to_process:
                return {
                    "message": f"No {'non-inline ' if not include_inline else ''}attachments found in email UID {uid}",
                    "email_subject": message.subject,
                    "attachment_count": 0,
                    "attachments": [],
                }

            attachments_info = []
            saved_files = []

            for att in attachments_to_process:
                att_info = {
                    "filename": att.filename or "unnamed",
                    "content_type": att.content_type,
                    "size": len(att.payload) if att.payload else 0,
                    "is_inline": att.is_inline,
                    "content_id": getattr(att, "content_id", None),
                }

                # Save to disk if save_path provided
                if save_path and att.payload:
                    try:
                        # Create directory if it doesn't exist
                        save_dir = Path(save_path)
                        save_dir.mkdir(parents=True, exist_ok=True)

                        # Generate unique filename if needed
                        filename = att.filename or f"attachment_{len(saved_files) + 1}"
                        file_path = save_dir / filename

                        # Handle duplicate filenames
                        counter = 1
                        original_path = file_path
                        while file_path.exists():
                            stem = original_path.stem
                            suffix = original_path.suffix
                            file_path = (
                                original_path.parent / f"{stem}_{counter}{suffix}"
                            )
                            counter += 1

                        # Write attachment to file
                        with open(file_path, "wb") as f:
                            f.write(att.payload)

                        att_info["saved_path"] = str(file_path)
                        saved_files.append(str(file_path))

                    except (OSError, PermissionError) as e:
                        att_info["save_error"] = f"Failed to save: {e!s}"
                else:
                    # Include base64 content if not saving to disk
                    if att.payload:
                        att_info["content_base64"] = base64.b64encode(
                            att.payload
                        ).decode()

                attachments_info.append(att_info)

            return {
                "message": f"Extracted {len(attachments_info)} attachments from email UID {uid}",
                "email_subject": message.subject,
                "email_from": message.from_,
                "attachment_count": len(attachments_info),
                "saved_to_disk": len(saved_files),
                "save_path": save_path if save_path else None,
                "attachments": attachments_info,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to extract attachments: {e!s}"
        except (OSError, PermissionError) as e:
            return f"File system error: {e!s}"

    @mcp.tool()
    async def list_email_attachments(uid: int, include_inline: bool = False):
        """
        List attachments in a specific email without downloading them.

        Args:
            uid: Email UID
            include_inline: Include inline attachments (default: False)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Get the specific message using UID criteria
            message = None
            for msg in state.mailbox.fetch(f"UID {uid}"):
                message = msg
                break

            if not message:
                return f"Email with UID {uid} not found."

            if not message.attachments:
                return {
                    "message": f"No attachments found in email UID {uid}",
                    "email_subject": message.subject,
                    "email_from": message.from_,
                    "email_date": message.date_str,
                    "attachment_count": 0,
                    "attachments": [],
                }

            # Filter and list attachments
            attachments_info = []
            for att in message.attachments:
                if include_inline or not att.is_inline:
                    att_info = {
                        "filename": att.filename or "unnamed",
                        "content_type": att.content_type,
                        "size": len(att.payload) if att.payload else 0,
                        "size_formatted": _format_size(
                            len(att.payload) if att.payload else 0
                        ),
                        "is_inline": att.is_inline,
                        "content_id": getattr(att, "content_id", None),
                    }
                    attachments_info.append(att_info)

            return {
                "message": f"Found {len(attachments_info)} {'attachments' if include_inline else 'non-inline attachments'} in email UID {uid}",
                "email_subject": message.subject,
                "email_from": message.from_,
                "email_date": message.date_str,
                "attachment_count": len(attachments_info),
                "total_size": sum(att["size"] for att in attachments_info),
                "total_size_formatted": _format_size(
                    sum(att["size"] for att in attachments_info)
                ),
                "attachments": attachments_info,
            }

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to list attachments: {e!s}"


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
