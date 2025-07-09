"""Email search tools for IMAP server."""

import imaplib
from datetime import datetime
from imap_tools import AND, OR
from mcp.server.fastmcp import FastMCP
from ..state import get_state_or_error


def register_email_search_tools(mcp: FastMCP):
    """Register email search tools with the MCP server."""

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
            return f"Invalid date format. Use YYYY-MM-DD format. Error: {e!s}"
        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to search emails by date: {e!s}"

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

        if min_size <= 0 and max_size <= 0:
            return "Please specify min_size and/or max_size greater than 0."

        try:
            # Create search criteria
            if min_size > 0 and max_size > 0:
                criteria = AND(size_gt=min_size, size_lt=max_size)
            elif min_size > 0:
                criteria = AND(size_gt=min_size)
            else:
                criteria = AND(size_lt=max_size)

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

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to search emails by size: {e!s}"

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

        if not search_body and not search_subject:
            return "Please enable search_body and/or search_subject."

        try:
            # Build search criteria
            if search_body and search_subject:
                criteria = OR(body=search_text, subject=search_text)
            elif search_body:
                criteria = AND(body=search_text)
            else:
                criteria = AND(subject=search_text)

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

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to search emails by text: {e!s}"

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
                if attachment_count < min_attachments:
                    continue

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

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to search emails with attachments: {e!s}"

    @mcp.tool()
    async def search_emails_by_flags(
        seen: bool | None = None,
        flagged: bool | None = None,
        deleted: bool | None = None,
        draft: bool | None = None,
        answered: bool | None = None,
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
            flag_descriptions.append(f"{'answered' if answered else 'not answered'}")

        if not criteria_kwargs:
            return "Please specify at least one flag filter (seen, flagged, deleted, draft, answered)."

        try:
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

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
            return f"Failed to search emails by flags: {e!s}"

    @mcp.tool()
    async def advanced_email_search(
        sender: str = "",
        subject: str = "",
        body_text: str = "",
        start_date: str = "",
        end_date: str = "",
        min_size: int = 0,
        max_size: int = 0,
        has_attachments: bool | None = None,
        is_unread: bool | None = None,
        is_flagged: bool | None = None,
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
                    search_description.append(f"between {start_date} and {end_date}")
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

        try:
            # Combine all criteria with AND
            if len(criteria_parts) == 1:
                final_criteria = criteria_parts[0]
            else:
                final_criteria = AND(*criteria_parts)

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

        except (imaplib.IMAP4.error, imaplib.IMAP4.abort, ValueError) as e:
            return f"Failed to perform advanced search: {e!s}"
