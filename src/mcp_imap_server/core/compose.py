"""Email composition tools for IMAP server."""

import imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email.utils

from mcp.server.fastmcp import FastMCP
from .state import get_state_or_error


def register_compose_tools(mcp: FastMCP):
    """Register email composition tools with the MCP server."""

    @mcp.tool()
    async def append_email(
        folder: str,
        subject: str,
        from_address: str,
        to_addresses: str,
        body_text: str = "",
        body_html: str = "",
        cc_addresses: str = "",
        bcc_addresses: str = "",
        reply_to: str = "",
        is_draft: bool = False,
    ):
        """
        Create and append an email to the specified folder (e.g., Drafts).

        Args:
            folder: Target folder name (e.g., "Drafts", "INBOX")
            subject: Email subject line
            from_address: Sender email address
            to_addresses: Recipient email addresses (comma-separated)
            body_text: Plain text body content (optional)
            body_html: HTML body content (optional)
            cc_addresses: CC recipients (comma-separated, optional)
            bcc_addresses: BCC recipients (comma-separated, optional)
            reply_to: Reply-to address (optional)
            is_draft: Whether to mark email as draft (default: False)
        """
        state, error = get_state_or_error(mcp.get_context())
        if error:
            return error

        try:
            # Create the email message
            if body_html and body_text:
                # Create multipart message with both text and HTML
                msg = MIMEMultipart("alternative")
                text_part = MIMEText(body_text, "plain", "utf-8")
                html_part = MIMEText(body_html, "html", "utf-8")
                msg.attach(text_part)
                msg.attach(html_part)
            elif body_html:
                # HTML only
                msg = MIMEText(body_html, "html", "utf-8")
            else:
                # Plain text only (default if no body provided)
                msg = MIMEText(body_text or "", "plain", "utf-8")

            # Set email headers
            msg["Subject"] = subject
            msg["From"] = from_address
            msg["To"] = to_addresses
            msg["Date"] = email.utils.formatdate(localtime=True)
            msg["Message-ID"] = email.utils.make_msgid()

            if cc_addresses:
                msg["Cc"] = cc_addresses
            if bcc_addresses:
                msg["Bcc"] = bcc_addresses
            if reply_to:
                msg["Reply-To"] = reply_to

            # Set flags for the message
            flags = []
            if is_draft:
                flags.append(r"\Draft")

            # Convert message to bytes
            message_bytes = msg.as_bytes()

            # Append to the specified folder
            state.mailbox.append(message_bytes, folder, flag_set=flags)
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to create email: {e!s}"
        else:
            return f"Email successfully created and saved to '{folder}' folder."
