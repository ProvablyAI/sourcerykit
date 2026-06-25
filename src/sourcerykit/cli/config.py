import re
from urllib.parse import urlparse, urlunparse

import questionary
import typer

from sourcerykit.cli.init import clear_auth_caches, create_db_tables, run_provably_handshake, save_bootstrap_ids
from sourcerykit.cli.utils import (
    console,
    mask_secret,
    prompt_postgres_url_with_retry,
    prompt_project_name,
    require_settings,
)
from sourcerykit.config import get_settings, load_local_env, save_app_dir_config, save_local_env

config = typer.Typer(no_args_is_help=True)


@config.command()
def list(show_key: bool = typer.Option(False, "--show-key", help="show secrets in clear text")) -> None:
    """Pretty print the active configuration (global + local)."""
    settings = require_settings()

    api_key_display = settings.api_key if show_key else mask_secret(settings.api_key)
    console.print("\n📋 [bold]Global Config[/bold] \n")
    console.print(f"[cyan]PROVABLY_API_KEY[/cyan]       = [yellow]'{api_key_display}'[/yellow]")

    if show_key:
        pg_display = settings.postgres_url
    else:
        parsed = urlparse(settings.postgres_url)
        pg_display = (
            urlunparse(parsed._replace(netloc=parsed.netloc.replace(f":{parsed.password}@", ":***@")))
            if parsed.password
            else settings.postgres_url
        )

    console.print("\n📋 [bold]Local Config[/bold] (.env)\n")
    console.print(f"[cyan]SOURCERYKIT_POSTGRES_URL[/cyan]  = [yellow]'{pg_display}'[/yellow]")
    console.print(f"[cyan]SOURCERYKIT_PROJECT_NAME[/cyan]  = [yellow]'{settings.project_name}'[/yellow]")

    console.print()


@config.command()
def set() -> None:
    """Interactively set or update configuration variables."""
    console.print("\n⚙️  [bold]SourceryKit Configuration Setup[/bold]\n")

    choices = questionary.checkbox(
        "Which configuration variables would you like to update?",
        choices=[
            questionary.Choice("PROVABLY_API_KEY (global)", checked=False),
            questionary.Choice("SOURCERYKIT_POSTGRES_URL (local)", checked=False),
            questionary.Choice("SOURCERYKIT_PROJECT_NAME (local)", checked=False),
        ],
    ).ask()

    if not choices:
        console.print("[yellow]No variables selected. Configuration unchanged.[/yellow]")
        return

    # --- Collect inputs ---

    api_key = None
    if "PROVABLY_API_KEY (global)" in choices:
        api_key = questionary.password("Enter your PROVABLY_API_KEY:").ask()
        if api_key is not None:
            api_key = api_key.strip()
            if not api_key:
                console.print("[red]❌ API key cannot be empty.[/red]")
                api_key = None
            elif not re.fullmatch(r"zk-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", api_key):
                console.print("[red]❌ API key must match format zk-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx[/red]")
                api_key = None

    postgres_url = None
    postgres_changed = False
    if "SOURCERYKIT_POSTGRES_URL (local)" in choices:
        local_env = load_local_env()
        current_url = local_env.get("SOURCERYKIT_POSTGRES_URL", "")
        result = prompt_postgres_url_with_retry()
        if result and result != current_url:
            postgres_url = result
            postgres_changed = True
        elif result == current_url:
            console.print("[yellow]Same URL — no change.[/yellow]")

    project_name = None
    project_changed = False
    if "SOURCERYKIT_PROJECT_NAME (local)" in choices:
        local_env = load_local_env()
        current_name = local_env.get("SOURCERYKIT_PROJECT_NAME", "")
        result = prompt_project_name(current=current_name)
        if result and result != current_name:
            project_name = result
            project_changed = True
        elif result == current_name:
            console.print("[yellow]Same name — no change.[/yellow]")

    # --- Save config ---

    if api_key:
        save_app_dir_config(api_key=api_key)

    local_updates: dict[str, str] = {}
    if postgres_url:
        local_updates["SOURCERYKIT_POSTGRES_URL"] = postgres_url
    if project_name:
        local_updates["SOURCERYKIT_PROJECT_NAME"] = project_name
    if local_updates:
        save_local_env(**local_updates)

    # --- Re-bootstrap if needed ---

    if postgres_changed or project_changed:
        settings = get_settings()
        name = settings.project_name

        clear_auth_caches()

        if postgres_changed:
            console.print("\n🔧 [bold]Re-bootstrapping (DB + Provably)...[/bold]")
            try:
                create_db_tables()
                console.print("  ✅ Database tables created")
            except Exception as e:
                console.print(f"  [red]❌ DB tables failed: {e}[/red]")
                return
        else:
            console.print("\n🔧 [bold]Re-running Provably handshake (new collection name)...[/bold]")

        try:
            run_provably_handshake(name)
            console.print("  ✅ Provably handshake completed")
        except Exception as e:
            console.print(f"  [red]❌ Handshake failed: {e}[/red]")
            return

        save_bootstrap_ids()
        console.print("  ✅ Bootstrap IDs saved\n")

    console.print("[bold green]✨ Configuration updated.[/bold green]")
