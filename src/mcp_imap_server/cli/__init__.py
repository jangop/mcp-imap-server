"""CLI tools for IMAP server credential management."""

from .commands import (
    add_imap_account,
    remove_imap_account,
    list_imap_accounts,
    update_imap_account,
    test_imap_connection,
    main,
)

__all__ = [
    "add_imap_account",
    "list_imap_accounts",
    "main",
    "remove_imap_account",
    "test_imap_connection",
    "update_imap_account",
]
