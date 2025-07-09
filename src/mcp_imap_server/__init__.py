"""MCP IMAP Server - A comprehensive Model Context Protocol server for IMAP email management."""

from .server import create_server, main as server_main
from .cli.commands import main as cli_main

__version__ = "0.1.0"

__all__ = [
    "cli_main",
    "create_server",
    "server_main",
]
