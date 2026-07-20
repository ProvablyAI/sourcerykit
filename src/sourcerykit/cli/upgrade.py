"""Upgrade command — check for new version + run database migrations."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import questionary

from sourcerykit.cli.utils import console


def _get_latest_pypi_version() -> str | None:
    """Fetch latest sourcerykit version from PyPI. Returns None on failure."""
    try:
        with urlopen("https://pypi.org/pypi/sourcerykit/json", timeout=5) as resp:
            import json

            data: dict[str, Any] = json.loads(resp.read())
            return str(data["info"]["version"])
    except (URLError, KeyError, OSError):
        return None


def _run_migrations() -> bool:
    """Run alembic upgrade head. Returns True on success."""
    from alembic.command import upgrade
    from alembic.config import Config

    # Locate alembic directory: dev (repo root) or installed package
    alembic_dir = Path(__file__).resolve().parents[3] / "alembic"
    if not alembic_dir.is_dir():
        alembic_dir = Path(__file__).resolve().parents[2] / "_alembic"

    if not alembic_dir.is_dir():
        console.print("[red]❌ Cannot locate migration scripts.[/red]")
        return False

    config = Config()
    config.set_main_option("script_location", str(alembic_dir))
    config.attributes["configure_logger"] = False

    try:
        upgrade(config, "head")
        return True
    except Exception as e:
        console.print(f"[red]❌ Migration failed: {e}[/red]")
        return False


def run_upgrade() -> None:
    """Check for package updates and run database migrations."""
    console.print("\n⬆️  [bold]SourceryKit Upgrade[/bold]\n")

    installed = importlib.metadata.version("sourcerykit")
    latest = _get_latest_pypi_version()

    if latest:
        if installed == latest:
            console.print(f"  ✅ Already on latest version: v{installed}")
        else:
            console.print(f"  📦 Installed: v{installed}  →  Latest: v{latest}")
            if questionary.confirm("Upgrade package now?", default=True).ask():
                console.print("  Upgrading...", end=" ")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "sourcerykit"],
                    capture_output=True,
                )
                if result.returncode == 0:
                    console.print("[green]DONE ✅[/green]")
                else:
                    console.print("[red]FAILED ❌[/red]")
                    console.print(f"  {result.stderr.decode().strip()}")
                    console.print("  Run manually: pip install --upgrade sourcerykit")
                    return
            else:
                console.print("  [yellow]⚠️  Skipping package upgrade.[/yellow]")
    else:
        console.print(f"  ℹ️  Installed: v{installed} (could not check PyPI)")

    console.print("\n  Running database migrations...", end=" ")
    if _run_migrations():
        console.print("[green]DONE ✅[/green]\n")
    else:
        console.print("[red]FAILED ❌[/red]\n")
