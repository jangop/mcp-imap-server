"""Command line interface for managing IMAP account credentials."""

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn
import socket
from imap_tools import MailBox

from .credentials import credential_manager, CredentialError, PasswordNotFoundError

app = typer.Typer(
    help="Manage IMAP account credentials for mcp-imap-server", no_args_is_help=True
)
console = Console()


def _exit_with_error() -> None:
    """Helper function to exit with error code 1."""
    raise typer.Exit(1)


def _test_imap_connection(
    username: str, password: str, server: str, timeout: int = 10
) -> tuple[bool, str]:
    """
    Test IMAP connection with given credentials.

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Try to connect and authenticate
        with MailBox(server).login(username, password, initial_folder=None):
            return True, "✅ Connection successful!"

    except socket.gaierror:
        return False, f"❌ Cannot resolve server: {server}"
    except TimeoutError:
        return False, f"❌ Connection timeout to {server}"
    except ConnectionRefusedError:
        return False, f"❌ Connection refused by {server}"
    except Exception as e:
        error_msg = str(e).lower()
        if "authentication failed" in error_msg or "login failed" in error_msg:
            return False, "❌ Authentication failed - check username/password"
        elif "certificate" in error_msg or "ssl" in error_msg:
            return False, f"❌ SSL/TLS error: {e}"
        elif "timeout" in error_msg:
            return False, f"❌ Connection timeout: {e}"
        else:
            return False, f"❌ Connection failed: {e}"


def _verify_credentials_with_progress(
    username: str, password: str, server: str
) -> bool:
    """Test credentials with a progress spinner."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"Testing connection to {server}...", total=None)

        success, message = _test_imap_connection(username, password, server)

        progress.update(task, description=message)
        progress.stop()

        rprint(message)
        return success


@app.command()
def list():
    """List all stored IMAP accounts."""
    accounts = credential_manager.list_accounts()

    if not accounts:
        rprint("[yellow]No accounts stored.[/yellow]")
        return

    table = Table(title="Stored IMAP Accounts")
    table.add_column("Account Name", style="cyan", no_wrap=True)
    table.add_column("Username", style="green")
    table.add_column("Server", style="blue")
    table.add_column("Password Status", style="magenta")

    for account_name in accounts:
        try:
            credentials = credential_manager.get_account(account_name)
            if credentials:
                table.add_row(
                    account_name, credentials.username, credentials.server, "✓ Secure"
                )
        except PasswordNotFoundError:
            # Get account metadata without password
            config = credential_manager._read_config()
            account_data = config.get("accounts", {}).get(account_name, {})
            table.add_row(
                account_name,
                account_data.get("username", "Unknown"),
                account_data.get("server", "Unknown"),
                "⚠ Missing",
            )
        except CredentialError:
            table.add_row(account_name, "Error", "Error", "✗ Error")

    console.print(table)

    # Show summary
    working_accounts = 0
    missing_passwords = 0
    error_accounts = 0

    for account_name in accounts:
        try:
            credential_manager.get_account(account_name)
            working_accounts += 1
        except PasswordNotFoundError:
            missing_passwords += 1
        except CredentialError:
            error_accounts += 1

    rprint(
        f"\n[blue]Summary:[/blue] {working_accounts} working, {missing_passwords} missing passwords, {error_accounts} errors"
    )


@app.command()
def add(
    name: str = typer.Argument(..., help="Account name (e.g., 'work', 'personal')"),
    username: str | None = typer.Option(None, "--username", "-u", help="IMAP username"),
    password: str | None = typer.Option(
        None,
        "--password",
        "-p",
        help="IMAP password (will prompt securely if not provided)",
    ),
    server: str | None = typer.Option(
        None, "--server", "-s", help="IMAP server hostname"
    ),
    verify: bool = typer.Option(
        True,
        "--verify/--no-verify",
        help="Test connection after adding credentials (default: True)",
    ),
):
    """Add a new IMAP account or update an existing one."""
    try:
        # Check if account already exists
        existing = credential_manager.get_account(name)
        if existing:
            if not typer.confirm(f"Account '{name}' already exists. Update it?"):
                rprint("[yellow]Operation cancelled.[/yellow]")
                return

        # Prompt for missing information
        if username is None:
            username = typer.prompt("Username")

        if password is None:
            password = typer.prompt("Password", hide_input=True)

        if server is None:
            server = typer.prompt("IMAP Server")

        credential_manager.add_account(name, username, password, server)

        if existing:
            rprint(f"[green]Account '{name}' updated successfully![/green]")
        else:
            rprint(f"[green]Account '{name}' added successfully![/green]")

        rprint("[dim]Password stored securely in system keyring[/dim]")

        # Verify credentials if requested
        if verify:
            rprint("\n[blue]Verifying credentials...[/blue]")
            if _verify_credentials_with_progress(username, password, server):
                rprint(
                    "[green]✅ Account verification successful! Ready to use.[/green]"
                )
            else:
                rprint("[yellow]⚠ Account saved but verification failed.[/yellow]")
                rprint(
                    "[yellow]You may want to check and update the credentials.[/yellow]"
                )
                if typer.confirm("Remove the account due to failed verification?"):
                    credential_manager.remove_account(name)
                    rprint(f"[yellow]Account '{name}' removed.[/yellow]")
                    _exit_with_error()

    except CredentialError as e:
        rprint(f"[red]Credential error: {e}[/red]")
        rprint(
            "[yellow]Tip: Make sure you're logged into your system and keyring is available[/yellow]"
        )
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[red]Error adding account: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def update(
    name: str = typer.Argument(..., help="Account name to update"),
    username: str | None = typer.Option(
        None, "--username", "-u", help="New IMAP username"
    ),
    password: str | None = typer.Option(
        None,
        "--password",
        "-p",
        help="New IMAP password (will prompt securely if flag is used)",
    ),
    server: str | None = typer.Option(
        None, "--server", "-s", help="New IMAP server hostname"
    ),
    verify: bool = typer.Option(
        True,
        "--verify/--no-verify",
        help="Test connection after updating credentials (default: True)",
    ),
):
    """Update an existing IMAP account."""
    try:
        # Get existing credentials
        existing = credential_manager.get_account(name)
        if not existing:
            rprint(f"[red]Account '{name}' not found.[/red]")
            _exit_with_error()

        # Handle password prompting - check if --password flag was used
        import sys

        password_flag_used = "--password" in sys.argv or "-p" in sys.argv
        if password_flag_used and password is None:
            password = typer.prompt("New password", hide_input=True)

        # Use existing values if new ones not provided
        new_username = username if username is not None else existing.username
        new_password = password if password is not None else existing.password
        new_server = server if server is not None else existing.server

        # Show what will be updated
        changes = []
        if username is not None and username != existing.username:
            changes.append(f"username: {existing.username} → {new_username}")
        if password is not None:
            changes.append("password: [hidden] → [hidden]")
        if server is not None and server != existing.server:
            changes.append(f"server: {existing.server} → {new_server}")

        if not changes:
            rprint("[yellow]No changes specified.[/yellow]")
            return

        rprint(f"[blue]Updating account '{name}':[/blue]")
        for change in changes:
            rprint(f"  • {change}")

        if not typer.confirm("Continue?"):
            rprint("[yellow]Operation cancelled.[/yellow]")
            return

        credential_manager.add_account(name, new_username, new_password, new_server)
        rprint(f"[green]Account '{name}' updated successfully![/green]")

        # Verify credentials if requested
        if verify:
            rprint("\n[blue]Verifying updated credentials...[/blue]")
            if _verify_credentials_with_progress(
                new_username, new_password, new_server
            ):
                rprint(
                    "[green]✅ Account verification successful! Ready to use.[/green]"
                )
            else:
                rprint("[yellow]⚠ Account updated but verification failed.[/yellow]")
                rprint(
                    "[yellow]You may want to check and update the credentials again.[/yellow]"
                )

    except Exception as e:
        rprint(f"[red]Error updating account: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def remove(
    name: str = typer.Argument(..., help="Account name to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Remove an IMAP account."""
    try:
        # Check if account exists
        try:
            existing = credential_manager.get_account(name)
        except PasswordNotFoundError:
            rprint(
                f"[yellow]Warning: Account '{name}' exists but password not found in keyring[/yellow]"
            )
            rprint("[yellow]Will remove account metadata anyway[/yellow]")
            existing = None

        if not existing and name not in credential_manager.list_accounts():
            rprint(f"[red]Account '{name}' not found.[/red]")
            _exit_with_error()

        # Confirm removal unless --force is used
        if not force:
            if existing:
                rprint("[blue]Account details:[/blue]")
                rprint(f"  Name: {name}")
                rprint(f"  Username: {existing.username}")
                rprint(f"  Server: {existing.server}")
            else:
                rprint(f"[blue]Account: {name}[/blue] (password missing from keyring)")

            if not typer.confirm(f"Are you sure you want to remove account '{name}'?"):
                rprint("[yellow]Operation cancelled.[/yellow]")
                return

        success = credential_manager.remove_account(name)
        if success:
            rprint(f"[green]Account '{name}' removed successfully![/green]")
            rprint("[dim]Password removed from system keyring[/dim]")
        else:
            rprint(f"[red]Failed to remove account '{name}'.[/red]")
            _exit_with_error()

    except CredentialError as e:
        rprint(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[red]Error removing account: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def test(
    name: str = typer.Argument(..., help="Account name to test"),
):
    """Test IMAP connection for an existing account."""
    try:
        # Get account credentials
        account = credential_manager.get_account(name)
        if not account:
            rprint(f"[red]Account '{name}' not found.[/red]")
            _exit_with_error()

        rprint(f"[blue]Testing account '{name}'...[/blue]")
        rprint(f"[dim]Server: {account.server}[/dim]")
        rprint(f"[dim]Username: {account.username}[/dim]")

        if _verify_credentials_with_progress(
            account.username, account.password, account.server
        ):
            rprint(f"[green]✅ Account '{name}' is working correctly![/green]")
        else:
            rprint(f"[red]❌ Account '{name}' failed connection test.[/red]")
            rprint(
                "[yellow]Consider updating the credentials with: mcp-imap-credentials update[/yellow]"
            )
            _exit_with_error()

    except PasswordNotFoundError:
        rprint(f"[red]Password not found in keyring for account '{name}'.[/red]")
        rprint("[yellow]Try running: mcp-imap-credentials migrate[/yellow]")
        raise typer.Exit(1) from None
    except CredentialError as e:
        rprint(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        rprint(f"[red]Error testing account: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def info():
    """Show information about keyring backend and configuration."""
    try:
        # Get keyring info
        keyring_info = credential_manager.get_keyring_info()

        rprint("[blue]MCP IMAP Server Configuration[/blue]\n")

        # Show config file location
        rprint(f"[cyan]Config file:[/cyan] {credential_manager.config_file}")

        # Show keyring info
        rprint("\n[cyan]Keyring Backend:[/cyan]")
        if "error" in keyring_info:
            rprint(f"  [red]Error: {keyring_info['error']}[/red]")
        else:
            rprint(f"  Backend: {keyring_info.get('backend', 'Unknown')}")
            rprint(f"  Name: {keyring_info.get('name', 'Unknown')}")
            rprint(f"  Priority: {keyring_info.get('priority', 'Unknown')}")

        # Show accounts summary
        accounts = credential_manager.list_accounts()
        rprint(f"\n[cyan]Accounts:[/cyan] {len(accounts)} stored")

        if accounts:
            for account in accounts:
                try:
                    credential_manager.get_account(account)
                    rprint(f"  ✓ {account}")
                except PasswordNotFoundError:
                    rprint(f"  ⚠ {account} (password missing)")
                except CredentialError:
                    rprint(f"  ✗ {account} (error)")

    except Exception as e:
        rprint(f"[red]Error getting info: {e}[/red]")
        raise typer.Exit(1) from None


@app.command()
def migrate():
    """Migrate accounts with plain-text passwords to secure keyring storage."""
    try:
        config = credential_manager._read_config()

        if "accounts" not in config:
            rprint("[yellow]No accounts found to migrate.[/yellow]")
            return

        accounts_to_migrate = []
        for account_name, account_data in config["accounts"].items():
            if "password" in account_data:
                accounts_to_migrate.append(account_name)

        if not accounts_to_migrate:
            rprint("[green]All accounts already use secure keyring storage![/green]")
            return

        rprint(
            f"[yellow]Found {len(accounts_to_migrate)} account(s) with plain-text passwords:[/yellow]"
        )
        for account in accounts_to_migrate:
            rprint(f"  • {account}")

        if not typer.confirm("\nMigrate these accounts to secure keyring storage?"):
            rprint("[yellow]Migration cancelled.[/yellow]")
            return

        # Trigger migration by accessing each account
        migrated = 0
        for account_name in accounts_to_migrate:
            try:
                credential_manager.get_account(account_name)
                migrated += 1
                rprint(f"[green]✓ Migrated: {account_name}[/green]")
            except Exception as e:
                rprint(f"[red]✗ Failed to migrate {account_name}: {e}[/red]")

        rprint(
            f"\n[green]Migration completed! {migrated}/{len(accounts_to_migrate)} accounts migrated.[/green]"
        )
        rprint(
            "[dim]Plain-text passwords have been removed from the config file.[/dim]"
        )

    except Exception as e:
        rprint(f"[red]Migration error: {e}[/red]")
        raise typer.Exit(1) from None


def main() -> None:
    """Main entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
