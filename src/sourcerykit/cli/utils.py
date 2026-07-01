"""Shared CLI utilities."""

import json
import sys
from urllib.parse import quote, urlparse, urlunparse

import psycopg
import questionary
import typer
from rich.console import Console

from sourcerykit.config import CONFIG_FILE, Settings, get_settings, load_app_dir_config
from sourcerykit.provably._api import get_api as get_main_api
from sourcerykit.provably._http import get_http

console = Console()


def mask_secret(value: str, show_last: int = 4) -> str:
    """Mask a secret string, showing only the last *show_last* characters."""
    if not value:
        return ""
    return value[-show_last:].rjust(len(value), "*")


def mask_postgres_url(url: str) -> str:
    """Mask the password in a Postgres URL."""
    parsed = urlparse(url)
    if parsed.password:
        return urlunparse(parsed._replace(netloc=parsed.netloc.replace(f":{parsed.password}@", ":***@")))
    return url


def require_settings() -> Settings:
    """Return settings or exit with a clear 'run init' message."""
    try:
        return get_settings()
    except Exception as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(code=1)


def logout() -> None:
    """Clear stored session (token + email) from global config."""
    payload = load_app_dir_config()
    for key in ("token", "email"):
        payload.pop(key, None)
    CONFIG_FILE.write_text(json.dumps(payload))
    load_app_dir_config.cache_clear()
    get_settings.cache_clear()
    get_http.cache_clear()
    get_main_api.cache_clear()


def ask_postgres_url() -> str:
    """Interactively collect Postgres connection details and return a URL."""
    console.print("\n[bold]Enter your remote database details:[/bold]")

    questions = [
        {
            "type": "text",
            "name": "host",
            "message": "  Host (IP or DNS):",
            "validate": lambda text: True if len(text.strip()) > 0 else "Host cannot be empty.",
        },
        {
            "type": "text",
            "name": "port",
            "message": "  Port:",
            "default": "5432",
            "validate": lambda text: (
                True if text.isdigit() and 1 <= int(text) <= 65535 else "Please enter a valid port number (1-65535)."
            ),
        },
        {
            "type": "text",
            "name": "username",
            "message": "  Username:",
            "validate": lambda text: True if len(text.strip()) > 0 else "Username cannot be empty.",
        },
        {
            "type": "password",
            "name": "password",
            "message": "  Password:",
            "validate": lambda text: True if len(text.strip()) > 0 else "Password cannot be empty.",
        },
        {
            "type": "text",
            "name": "database",
            "message": "  Database name:",
            "validate": lambda text: True if len(text.strip()) > 0 else "Database name cannot be empty.",
        },
    ]

    answers = questionary.prompt(questions)
    if not answers:
        return ""

    host = answers["host"].strip()
    port = int(answers["port"])
    username = answers["username"].strip()
    password = answers["password"].strip()
    database = answers["database"].strip()

    return f"postgresql://{quote(username, safe='')}:{quote(password, safe='')}@{host}:{port}/{database}"


def run_connectivity_check(postgres_url: str, quiet: bool = False) -> bool:
    """Test the Postgres connection."""
    if not quiet:
        console.print("Testing database connection...", end=" ")
        sys.stdout.flush()
    try:
        with psycopg.connect(postgres_url):
            pass
        if not quiet:
            console.print("CONNECTED ✅")
        return True

    except Exception as e:
        if not quiet:
            console.print("FAILED ❌")
            console.print("\n⚠️ Connection Error: Could not reach your database.")
            console.print(f"Details: {e}")
            console.print("Please double-check your credentials, firewall, or routing rules.\n")
        return False


def _normalize_postgres_url(url: str) -> str:
    """Re-encode credentials in a Postgres URL so special chars don't break parsing."""
    parsed = urlparse(url)
    if not parsed.username:
        return url
    encoded_user = quote(parsed.username, safe="")
    encoded_pass = quote(parsed.password or "", safe="")
    netloc = f"{encoded_user}:{encoded_pass}@{parsed.hostname}:{parsed.port or 5432}"
    return str(urlunparse(parsed._replace(netloc=netloc)))


def prompt_postgres_url_with_retry(postgres_url: str | None = None) -> str | None:
    """Prompt for Postgres URL with connectivity check and retry loop.

    If *postgres_url* is provided, validate it non-interactively (single attempt).
    Returns the validated URL, or None if the user cancelled/aborted.
    """
    if postgres_url:
        postgres_url = _normalize_postgres_url(postgres_url)
        if run_connectivity_check(postgres_url):
            return postgres_url
        console.print("[red]❌ Database connection failed.[/red]")
        raise typer.Exit(code=1)

    while True:
        postgres_url = ask_postgres_url()
        if not postgres_url:
            return None
        if run_connectivity_check(postgres_url):
            return str(postgres_url)
        retry = questionary.confirm(
            message="Connection failed. Would you like to check your details and try again?",
            default=True,
        ).ask()
        if not retry:
            return None


def prompt_project_name(current: str = "", project_name: str | None = None) -> str | None:
    """Prompt for a project name with validation and normalization.

    If *project_name* is provided, normalize and return it without prompting.
    Returns the normalized name, or None if the user cancelled.
    """
    if project_name:
        normalized = project_name.strip().lower().replace(" ", "-")
        if not normalized:
            console.print("[red]❌ Project name cannot be empty.[/red]")
            raise typer.Exit(code=1)
        return normalized

    label = f" (Current: {current})" if current else ""
    raw = questionary.text(
        f"Enter project name{label}:",
        validate=lambda text: True if len(text.strip()) > 0 else "Project name cannot be empty.",
    ).ask()
    if not raw:
        return None
    return str(raw.strip().lower().replace(" ", "-"))
