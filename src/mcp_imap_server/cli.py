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

    for account_name in accounts:
        credentials = credential_manager.get_account(account_name)
        if credentials:
            table.add_row(account_name, credentials.username, credentials.server)

    console.print(table)


@app.command()
def add(
    name: str = typer.Argument(..., help="Account name (e.g., 'work', 'personal')"),
    username: str = typer.Option(..., "--username", "-u", help="IMAP username"),
    password: str = typer.Option(
        ..., "--password", "-p", hide_input=True, help="IMAP password"
    ),
    server: str = typer.Option(..., "--server", "-s", help="IMAP server hostname"),
):
    """Add a new IMAP account or update an existing one."""
    try:
        # Check if account already exists
        existing = credential_manager.get_account(name)
        if existing:
            if not typer.confirm(f"Account '{name}' already exists. Update it?"):
                rprint("[yellow]Operation cancelled.[/yellow]")
                return

        credential_manager.add_account(name, username, password, server)

        if existing:
            rprint(f"[green]Account '{name}' updated successfully![/green]")
        else:
            rprint(f"[green]Account '{name}' added successfully![/green]")

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
        None, "--password", "-p", hide_input=True, help="New IMAP password"
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
        existing = credential_manager.get_account(name)
        if not existing:
            rprint(f"[red]Account '{name}' not found.[/red]")
            raise typer.Exit(1)

        # Confirm removal unless --force is used
        if not force:
            rprint("[blue]Account details:[/blue]")
            rprint(f"  Name: {name}")
            rprint(f"  Username: {existing.username}")
            rprint(f"  Server: {existing.server}")

            if not typer.confirm(f"Are you sure you want to remove account '{name}'?"):
                rprint("[yellow]Operation cancelled.[/yellow]")
                return

        success = credential_manager.remove_account(name)
        if success:
            rprint(f"[green]Account '{name}' removed successfully![/green]")
        else:
            rprint(f"[red]Failed to remove account '{name}'.[/red]")
            raise typer.Exit(1)

    except Exception as e:
        rprint(f"[red]Error removing account: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def config():
    """Show configuration file location."""
    config_path = credential_manager.config_file
    rprint(f"[blue]Configuration file:[/blue] {config_path}")

    if config_path.exists():
        rprint("[green]✓ File exists[/green]")

        # Show file size
        size = config_path.stat().st_size
        rprint(f"[blue]Size:[/blue] {size} bytes")

        # Count accounts
        accounts = credential_manager.list_accounts()
        count = len(accounts)
        rprint(f"[blue]Accounts:[/blue] {count}")
    else:
        rprint(
            "[yellow]✗ File does not exist (will be created when first account is added)[/yellow]"
        )


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
