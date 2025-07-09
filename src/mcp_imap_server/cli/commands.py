"""CLI account management commands for IMAP server."""

import imaplib
import ssl
from ..shared.credentials import CredentialManager
import argparse
import sys


def add_imap_account(
    email: str,
    password: str,
    imap_server: str,
    imap_port: int = 993,
    use_ssl: bool = True,
):
    """
    Add a new IMAP account to the credential store.

    Args:
        email: Email address
        password: Email password or app password
        imap_server: IMAP server hostname
        imap_port: IMAP port (default: 993 for SSL)
        use_ssl: Whether to use SSL connection (default: True)
    """
    try:
        # Test the connection first
        connection_test = test_imap_connection(
            email, password, imap_server, imap_port, use_ssl
        )

        # Check if connection test was successful
        if isinstance(connection_test, str) and "Failed" in connection_test:
            return f"Connection test failed: {connection_test}"

        # Save credentials if connection test passed
        cred_manager = CredentialManager()
        cred_manager.add_account(
            name=email,
            username=email,
            password=password,
            server=f"{imap_server}:{imap_port}:{use_ssl}",
        )
    except Exception as e:
        return f"Failed to add IMAP account: {e!s}"
    else:
        return {
            "message": f"Successfully added IMAP account for {email}",
            "email": email,
            "imap_server": imap_server,
            "imap_port": imap_port,
            "use_ssl": use_ssl,
            "connection_test": "passed",
        }


def remove_imap_account(email: str):
    """
    Remove an IMAP account from the credential store.

    Args:
        email: Email address to remove
    """
    try:
        # Check if credentials exist and remove them
        cred_manager = CredentialManager()
        success = cred_manager.remove_account(email)

        if success:
            return {
                "message": f"Successfully removed IMAP account for {email}",
                "email": email,
            }
        else:
            return f"No credentials found for {email}"

    except Exception as e:
        return f"Failed to remove IMAP account: {e!s}"


def list_imap_accounts(test: bool = True):
    """List all configured IMAP accounts, print a table, and test connections unless --no-test is passed."""
    from rich.table import Table
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn

    cred_manager = CredentialManager()
    accounts = cred_manager.list_accounts()
    console = Console()
    table = Table(title="IMAP Accounts")
    table.add_column("Email", style="bold")
    table.add_column("IMAP Server")
    table.add_column("Port")
    table.add_column("SSL")
    table.add_column("Status")

    # Test accounts with progress indicator
    if test and accounts:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Testing accounts...", total=len(accounts))
            for email in accounts:
                progress.update(task, description=f"Testing {email}...")
                account = cred_manager.get_account(email)
                if account:
                    # Parse server info
                    try:
                        server_parts = account.server.split(":")
                        imap_server = server_parts[0]
                        imap_port = (
                            str(server_parts[1]) if len(server_parts) > 1 else "993"
                        )
                        use_ssl = (
                            server_parts[2].lower() == "true"
                            if len(server_parts) > 2
                            else True
                        )
                    except Exception:
                        imap_server = account.server
                        imap_port = "?"
                        use_ssl = True
                    status = test_imap_account(email)
                    table.add_row(
                        email,
                        imap_server,
                        imap_port,
                        "Yes" if use_ssl else "No",
                        status,
                    )
                else:
                    table.add_row(email, "?", "?", "?", "NOT FOUND")
                progress.advance(task)
    else:
        # No testing or no accounts
        for email in accounts:
            account = cred_manager.get_account(email)
            if account:
                # Parse server info
                try:
                    server_parts = account.server.split(":")
                    imap_server = server_parts[0]
                    imap_port = str(server_parts[1]) if len(server_parts) > 1 else "993"
                    use_ssl = (
                        server_parts[2].lower() == "true"
                        if len(server_parts) > 2
                        else True
                    )
                except Exception:
                    imap_server = account.server
                    imap_port = "?"
                    use_ssl = True
                status = "-"
                table.add_row(
                    email, imap_server, imap_port, "Yes" if use_ssl else "No", status
                )
            else:
                table.add_row(email, "?", "?", "?", "NOT FOUND")
    console.print(table)


def update_imap_account(
    email: str,
    password: str = "",
    imap_server: str = "",
    imap_port: int = 0,
    use_ssl: bool = True,
):
    """
    Update an existing IMAP account configuration.

    Args:
        email: Email address to update
        password: New password (optional)
        imap_server: New IMAP server hostname (optional)
        imap_port: New IMAP port (optional, 0 to keep current)
        use_ssl: Whether to use SSL connection (default: True)
    """
    try:
        # Update credentials if account exists
        cred_manager = CredentialManager()
        existing_account = cred_manager.get_account(email)
        if not existing_account:
            return f"No account found for {email}."
        existing_server = existing_account.server
        existing_port = 993
        existing_ssl = True
        # Use existing values if new ones not provided
        new_server = imap_server or existing_server
        new_port = imap_port or existing_port
        new_ssl = use_ssl if use_ssl is not None else existing_ssl
        cred_manager.update_account(
            name=email,
            username=email,
            password=password,
            server=f"{new_server}:{new_port}:{new_ssl}",
        )
    except Exception as e:
        return f"Failed to update IMAP account: {e!s}"
    else:
        return {
            "message": f"Successfully updated IMAP account for {email}",
            "email": email,
            "imap_server": new_server,
            "imap_port": new_port,
            "use_ssl": new_ssl,
            "connection_test": "passed",
        }


def test_imap_account(email: str) -> str:
    """Test IMAP connection using stored credentials for a given email/account name."""
    cred_manager = CredentialManager()
    account = cred_manager.get_account(email)
    if not account:
        return "NOT FOUND"
    try:
        # Parse server info
        try:
            server_parts = account.server.split(":")
            imap_server = server_parts[0]
            imap_port = int(server_parts[1]) if len(server_parts) > 1 else 993
            use_ssl = (
                server_parts[2].lower() == "true" if len(server_parts) > 2 else True
            )
        except Exception:
            imap_server = account.server
            imap_port = 993
            use_ssl = True
        if use_ssl:
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        else:
            mail = imaplib.IMAP4(imap_server, imap_port)
        mail.login(account.username, account.password)
        mail.logout()
    except Exception as e:
        return f"FAILED: {e.__class__.__name__}"  # Short error
    else:
        return "OK"


def test_imap_connection(
    email: str, password: str, imap_server: str, imap_port: int, use_ssl: bool
):
    """
    Test IMAP connection with provided credentials.
    This is a helper function used by other commands.
    """
    try:
        # Create IMAP connection
        if use_ssl:
            mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        else:
            mail = imaplib.IMAP4(imap_server, imap_port)

        # Login
        mail.login(email, password)

        # List folders to verify connection works
        mail.list()

        # Logout
        mail.logout()
    except (imaplib.IMAP4.error, imaplib.IMAP4.abort) as e:
        return f"IMAP connection failed: {e!s}"
    except ssl.SSLError as e:
        return f"SSL connection failed: {e!s}"
    except OSError as e:
        return f"Network connection failed: {e!s}"
    except Exception as e:
        return f"Connection test failed: {e!s}"
    else:
        return {
            "message": "Connection test successful",
            "email": email,
            "server": imap_server,
            "port": imap_port,
            "ssl": use_ssl,
        }


def main():
    """CLI entry point for credential management."""
    parser = argparse.ArgumentParser(description="IMAP Credential Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add account command
    add_parser = subparsers.add_parser("add", help="Add an IMAP account")
    add_parser.add_argument("email", help="Email address")
    add_parser.add_argument("password", help="Password")
    add_parser.add_argument("server", help="IMAP server")
    add_parser.add_argument(
        "--port", type=int, default=993, help="IMAP port (default: 993)"
    )
    add_parser.add_argument("--no-ssl", action="store_true", help="Disable SSL")

    # Remove account command
    remove_parser = subparsers.add_parser("remove", help="Remove an IMAP account")
    remove_parser.add_argument("email", help="Email address")

    # List accounts command
    list_parser = subparsers.add_parser("list", help="List all accounts")
    list_parser.add_argument(
        "--no-test",
        action="store_true",
        help="Do not test connections, just list accounts",
    )

    # Update account command
    update_parser = subparsers.add_parser("update", help="Update an IMAP account")
    update_parser.add_argument("email", help="Email address")
    update_parser.add_argument("--password", help="New password")
    update_parser.add_argument("--server", help="New IMAP server")
    update_parser.add_argument("--port", type=int, help="New IMAP port")
    update_parser.add_argument("--no-ssl", action="store_true", help="Disable SSL")

    # Test connection command (improved)
    test_parser = subparsers.add_parser(
        "test", help="Test IMAP connection for a stored account"
    )
    test_parser.add_argument("email", help="Email address (account name)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == "add":
            result = add_imap_account(
                email=args.email,
                password=args.password,
                imap_server=args.server,
                imap_port=args.port,
                use_ssl=not args.no_ssl,
            )
            print(result)
        elif args.command == "remove":
            result = remove_imap_account(email=args.email)
            print(result)
        elif args.command == "list":
            list_imap_accounts(test=not args.no_test)
        elif args.command == "update":
            result = update_imap_account(
                email=args.email,
                password=args.password or "",
                imap_server=args.server or "",
                imap_port=args.port or 0,
                use_ssl=not args.no_ssl if args.no_ssl is not None else True,
            )
            print(result)
        elif args.command == "test":
            status = test_imap_account(args.email)
            print(f"{args.email}: {status}")
        else:
            print(f"Unknown command: {args.command}")
            return
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
