"""Command line interface for managing IMAP account credentials."""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from .credentials import credential_manager

app = typer.Typer(help="Manage IMAP account credentials for mcp-imap-server")
console = Console()


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
        except RuntimeError as e:
            if "Password not found in keyring" in str(e):
                # Get account metadata without password
                config = credential_manager._read_config()
                account_data = config.get("accounts", {}).get(account_name, {})
                table.add_row(
                    account_name,
                    account_data.get("username", "Unknown"),
                    account_data.get("server", "Unknown"),
                    "⚠ Missing",
                )
            else:
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
        except RuntimeError as e:
            if "Password not found in keyring" in str(e):
                missing_passwords += 1
            else:
                error_accounts += 1

    rprint(
        f"\n[blue]Summary:[/blue] {working_accounts} working, {missing_passwords} missing passwords, {error_accounts} errors"
    )


@app.command()
def add(
    name: str = typer.Argument(..., help="Account name (e.g., 'work', 'personal')"),
    username: Optional[str] = typer.Option(
        None, "--username", "-u", help="IMAP username"
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        help="IMAP password (will prompt securely if not provided)",
    ),
    server: Optional[str] = typer.Option(
        None, "--server", "-s", help="IMAP server hostname"
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

    except RuntimeError as e:
        rprint(f"[red]Keyring error: {e}[/red]")
        rprint(
            "[yellow]Tip: Make sure you're logged into your system and keyring is available[/yellow]"
        )
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Error adding account: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    name: str = typer.Argument(..., help="Account name to update"),
    username: Optional[str] = typer.Option(
        None, "--username", "-u", help="New IMAP username"
    ),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        help="New IMAP password (will prompt securely if flag is used)",
    ),
    server: Optional[str] = typer.Option(
        None, "--server", "-s", help="New IMAP server hostname"
    ),
):
    """Update an existing IMAP account."""
    try:
        # Get existing credentials
        existing = credential_manager.get_account(name)
        if not existing:
            rprint(f"[red]Account '{name}' not found.[/red]")
            raise typer.Exit(1)

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

    except Exception as e:
        rprint(f"[red]Error updating account: {e}[/red]")
        raise typer.Exit(1)


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
        except RuntimeError as e:
            if "Password not found in keyring" in str(e):
                rprint(
                    f"[yellow]Warning: Account '{name}' exists but password not found in keyring[/yellow]"
                )
                rprint("[yellow]Will remove account metadata anyway[/yellow]")
                existing = None
            else:
                raise

        if not existing and name not in credential_manager.list_accounts():
            rprint(f"[red]Account '{name}' not found.[/red]")
            raise typer.Exit(1)

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
            raise typer.Exit(1)

    except RuntimeError as e:
        rprint(f"[red]Keyring error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Error removing account: {e}[/red]")
        raise typer.Exit(1)


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
                except RuntimeError as e:
                    if "Password not found in keyring" in str(e):
                        rprint(f"  ⚠ {account} (password missing)")
                    else:
                        rprint(f"  ✗ {account} (error)")

    except Exception as e:
        rprint(f"[red]Error getting info: {e}[/red]")
        raise typer.Exit(1)


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
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
