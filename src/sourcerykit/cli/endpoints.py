import asyncio

import questionary
import typer
from rich.table import Table

from sourcerykit.cli.utils import console, require_settings
from sourcerykit.errors import SourceryKitTrustError
from sourcerykit.trusted_endpoints import service
from sourcerykit.trusted_endpoints.service import sanitize_and_extract_trusted_url

endpoints = typer.Typer(no_args_is_help=True)


@endpoints.command()
def add(url: str, label: str = typer.Option(None, "--label", "-l", help="optional display label")) -> None:
    require_settings()
    try:
        sanitize_and_extract_trusted_url(url)
    except SourceryKitTrustError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(code=1)
    asyncio.run(service.insert_trusted_endpoint(url=url, display_label=label))
    console.print(f"[bold green]✅ Endpoint added:[/bold green] {url}" + (f" ({label})" if label else ""))


@endpoints.command()
def list() -> None:
    require_settings()
    rows = asyncio.run(service.list_all_trusted_endpoints_detailed())

    if not rows:
        console.print("[yellow]No trusted endpoints found.[/yellow]")
        return

    table = Table(title="Trusted Endpoints")
    table.add_column("URL", style="cyan")
    table.add_column("Label", style="white")
    table.add_column("Policy", style="dim")
    table.add_column("Created by", style="dim")

    for ep in rows:
        table.add_row(ep["url"], ep["label"], ep["policy_version"], ep["created_by"])

    console.print(table)


@endpoints.command()
def remove(url: str) -> None:
    require_settings()
    confirm = questionary.confirm(f"Remove endpoint '{url}'?", default=False).ask()
    if not confirm:
        console.print("[yellow]Cancelled.[/yellow]")
        return
    asyncio.run(service.remove_trusted_endpoint(url=url))
    console.print(f"[bold green]✅ Endpoint removed:[/bold green] {url}")
