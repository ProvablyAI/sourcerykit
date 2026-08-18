"""Sandbox database management commands."""

import asyncio

import questionary
import typer

from sourcerykit.cli.utils import console, mask_postgres_url, require_settings
from sourcerykit.config import save_local_env
from sourcerykit.provably.service import service

sandbox = typer.Typer(no_args_is_help=True)


@sandbox.command()
def create() -> None:
    """Create or retrieve a hosted sandbox database."""
    settings = require_settings()
    org_id = settings.org_id
    if not org_id:
        console.print("[red]❌ No organisation configured. Run 'sourcerykit init' first.[/red]")
        raise typer.Exit(code=1)

    console.print("Creating sandbox...", end=" ")
    uri = asyncio.run(service.create_sandbox(org_id))
    save_local_env(SOURCERYKIT_POSTGRES_URL=uri)
    console.print("DONE ✅")
    console.print(f"\n  connection_uri = {mask_postgres_url(uri)}")


@sandbox.command()
def status() -> None:
    """Show sandbox status and connection URI."""
    require_settings()

    sandbox_data = asyncio.run(service.get_sandbox())
    if not sandbox_data:
        console.print("[yellow]No sandbox found.[/yellow]")
        return

    status_val = sandbox_data.get("status", "unknown")
    uri = sandbox_data.get("connection_uri", "")
    console.print(f"  status          = {status_val}")
    console.print(f"  connection_uri  = {mask_postgres_url(uri)}")


@sandbox.command()
def delete(
    yes: bool = typer.Option(False, "--yes", "-y", help="skip confirmation"),
) -> None:
    """Delete the sandbox database."""
    require_settings()

    if not yes:
        confirm = questionary.confirm(
            "Delete sandbox? All data will be lost.", default=False
        ).ask()
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            return

    console.print("Deleting sandbox...", end=" ")
    asyncio.run(service.delete_sandbox())
    console.print("DONE ✅")
