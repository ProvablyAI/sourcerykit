import asyncio
from pathlib import Path

import questionary
import typer

from sourcerykit.cli.utils import console, require_settings
from sourcerykit.provably.service import ProvablyService

service = ProvablyService()


def send_feedback(
    description: str | None = None,
    attach_file: str | None = None,
) -> None:
    """Submit interactive feedback or bug reports."""
    require_settings()
    console.print("\n📣 [bold]Send Feedback to SourceryKit[/bold]\n")

    # read description
    if description:
        desc = description.strip()
    else:
        desc = questionary.text("Please provide a description of your feedback/issue:", multiline=True).ask()

    if not desc or not desc.strip():
        console.print("[yellow]⚠️  Feedback description cannot be empty. Aborting.[/yellow]")
        raise typer.Exit(code=1)

    # read file
    file_bytes = b""
    if attach_file:
        path = Path(attach_file.strip()).expanduser().resolve()
        if not path.exists() or not path.is_file():
            console.print(f"[red]❌ Error: File not found at '{path}'[/red]")
            raise typer.Exit(code=1)
        try:
            file_bytes = path.read_bytes()
            console.print(f"[green]✓ Attached '{path.name}' ({len(file_bytes)} bytes)[/green]")
        except PermissionError:
            console.print(f"[red]❌ Permission denied when reading '{path}'[/red]")
            raise typer.Exit(code=1)
    elif not description:
        # Only ask about file attachment in fully interactive mode
        attach = questionary.confirm(
            "Would you like to attach a file (e.g., a log or screenshot)?", default=False
        ).ask()

        if attach:
            file_path_str = questionary.text("Enter the path to the file you want to attach:").ask()

            if file_path_str:
                path = Path(file_path_str.strip()).expanduser().resolve()

                if not path.exists() or not path.is_file():
                    console.print(f"[red]❌ Error: File not found at '{path}'[/red]")
                    raise typer.Exit(code=1)

                try:
                    file_bytes = path.read_bytes()
                    console.print(f"[green]✓ Attached '{path.name}' ({len(file_bytes)} bytes)[/green]")
                except PermissionError:
                    console.print(f"[red]❌ Permission denied when reading '{path}'[/red]")
                    raise typer.Exit(code=1)

    console.print("\n🚀 Sending feedback...")

    # send feedback
    try:
        asyncio.run(service.create_feedback(desc.strip(), file_bytes))
        console.print("\n✨ [bold green]Success![/bold green] Thank you for your feedback.")
    except Exception as e:
        console.print(f"\n[red]❌ Failed to submit feedback: {e}[/red]")
        raise typer.Exit(code=1)
