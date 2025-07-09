"""Shared utilities for IMAP server."""

from .credentials import CredentialManager, credential_manager

__all__ = [
    "CredentialManager",
    "credential_manager",
]
