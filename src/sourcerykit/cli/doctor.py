"""Doctor command — validate configuration and connectivity."""

import asyncio
import dataclasses
from collections.abc import Callable

from sourcerykit.cli.init import run_full_bootstrap
from sourcerykit.cli.utils import console, run_connectivity_check
from sourcerykit.config import Settings, get_settings
from sourcerykit.db._engine import get_connection_info
from sourcerykit.provably._errors import ProvablyConnectionError, ProvablyUnauthorizedError
from sourcerykit.provably.auth_service import auth_service
from sourcerykit.provably.service import service


def _check_api_key_and_org(settings: Settings) -> tuple[bool, str]:
    """Validate API key and org_id in one call (list_organizations uses API key)."""
    if not settings.api_key:
        return False, "PROVABLY_API_KEY is missing — run 'sourcerykit init'"

    try:
        orgs = asyncio.run(auth_service.list_organizations())
    except ProvablyUnauthorizedError:
        return False, "API key is invalid or expired — run 'sourcerykit init'"
    except ProvablyConnectionError:
        return False, "Cannot reach Provably API (network error)"
    except Exception as e:
        return False, f"API key check failed: {e}"

    org_ids = [str(o.get("id", "")) for o in orgs]
    if str(settings.org_id) not in org_ids:
        return False, f"Org ID {settings.org_id} not found — run 'sourcerykit init'"

    return True, f"API key valid, org found ({len(orgs)} org(s))"


def _check_postgres(settings: Settings) -> tuple[bool, str]:
    """Validate postgres_url connectivity."""
    if not settings.postgres_url:
        return False, "SOURCERYKIT_POSTGRES_URL is missing — run 'sourcerykit init'"

    if run_connectivity_check(settings.postgres_url, quiet=True):
        return True, "PostgreSQL connection successful"
    return False, "PostgreSQL connection failed — check your SOURCERYKIT_POSTGRES_URL"


def _check_project_name(settings: Settings) -> tuple[bool, str]:
    """Validate project_name is set."""
    if settings.project_name:
        return True, f"'{settings.project_name}'"
    return False, "SOURCERYKIT_PROJECT_NAME is missing — run 'sourcerykit init'"


def _check_bootstrap_ids(settings: Settings) -> tuple[bool, str]:
    """Validate all bootstrap resource IDs are present."""
    if settings.has_bootstrap_ids:
        return True, "All bootstrap IDs present"

    missing = [
        f.name
        for f in dataclasses.fields(settings)
        if (f.name.endswith("_id") or f.name == "integration_key") and not getattr(settings, f.name)
    ]
    return False, f"Missing: {', '.join(missing)} — run 'sourcerykit doctor --fix'"


# --- Deep checks — verify IDs exist in Provably backend ---
async def _deep_check_collection_and_ids(settings: Settings) -> tuple[bool, str]:
    """Verify Provably resources match local config using the same calls as bootstrap."""
    if not settings.has_bootstrap_ids or settings.middleware_id is None:
        return False, "Bootstrap IDs missing — run 'sourcerykit doctor --fix'"

    remote_mw = await service.get_middleware_id()
    if remote_mw != settings.middleware_id:
        return False, f"Middleware mismatch (local={settings.middleware_id}, remote={remote_mw})"

    connection_info = get_connection_info()
    remote_db = await service.get_database_id(settings.middleware_id, connection_info)
    if remote_db != settings.database_id:
        return False, f"Database mismatch (local={settings.database_id}, remote={remote_db})"

    ids = await service.get_database_schema_id_and_table_id(settings.middleware_id, connection_info)
    if ids["schema_id"] != settings.schema_id:
        return False, f"Schema mismatch (local={settings.schema_id}, remote={ids['schema_id']})"
    if ids["table_id"] != settings.table_id:
        return False, f"Table mismatch (local={settings.table_id}, remote={ids['table_id']})"

    remote_col = await service.get_collection_id(settings.project_name)
    if remote_col != settings.collection_id:
        return False, f"Collection mismatch (local={settings.collection_id}, remote={remote_col})"

    return True, f"Collection '{settings.project_name}' verified (middleware, db, schema, table, collection)"


async def _deep_check_integration(settings: Settings) -> tuple[bool, str]:
    """Verify integration_key has the expected format (API key, not UUID)."""
    if not settings.integration_key:
        return False, "SOURCERYKIT_INTEGRATION_KEY is missing — run 'sourcerykit doctor --fix'"

    if not settings.integration_key.startswith("i-"):
        return False, f"SOURCERYKIT_INTEGRATION_KEY has unexpected format: {settings.integration_key!r}"

    return True, "Integration key format valid"


def _run_deep_check_collection_and_ids(settings: Settings) -> tuple[bool, str]:
    try:
        return asyncio.run(_deep_check_collection_and_ids(settings))
    except ProvablyUnauthorizedError:
        return False, "API key expired — run 'sourcerykit init'"
    except ProvablyConnectionError:
        return False, "Cannot reach Provably API (network error)"
    except Exception as e:
        return False, f"Collection check failed: {e}"


def _run_deep_check_integration(settings: Settings) -> tuple[bool, str]:
    try:
        return asyncio.run(_deep_check_integration(settings))
    except ProvablyUnauthorizedError:
        return False, "API key expired — run 'sourcerykit init'"
    except ProvablyConnectionError:
        return False, "Cannot reach Provably API (network error)"
    except Exception as e:
        return False, f"Integration check failed: {e}"


def run_doctor(fix: bool = False) -> None:
    """Validate global config, local config, and connectivity."""
    console.print("\n🩺 [bold]SourceryKit Doctor[/bold]\n")

    try:
        settings = get_settings()
    except Exception as e:
        console.print(f"[red]❌ Cannot load settings: {e}[/red]")
        console.print("\n[bold yellow]Run 'sourcerykit init' to configure[/bold yellow]\n")
        return

    checks: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
        ("API key + org", lambda: _check_api_key_and_org(settings)),
        ("PostgreSQL", lambda: _check_postgres(settings)),
        ("Project name", lambda: _check_project_name(settings)),
        ("Bootstrap IDs", lambda: _check_bootstrap_ids(settings)),
        ("Collection + IDs", lambda: _run_deep_check_collection_and_ids(settings)),
        ("Integration", lambda: _run_deep_check_integration(settings)),
    ]

    passed = 0
    total = len(checks)
    failed_indices: list[int] = []

    for i, (label, check_fn) in enumerate(checks):
        ok, detail = check_fn()
        icon = "[green]✅[/green]" if ok else "[red]❌[/red]"
        console.print(f"  {icon} {label}: {detail}")
        if ok:
            passed += 1
        else:
            failed_indices.append(i)

    # --fix: attempt to create missing bootstrap IDs
    if fix and failed_indices:
        console.print("\n  🔧 [bold]Running bootstrap handshake...[/bold]", end=" ")
        try:
            if run_full_bootstrap(settings.project_name):
                console.print("[green]DONE ✅[/green]")
                get_settings.cache_clear()
                settings = get_settings()
                for i in failed_indices:
                    label, check_fn = checks[i]
                    ok, detail = check_fn()
                    icon = "[green]✅[/green]" if ok else "[red]❌[/red]"
                    console.print(f"  {icon} {label}: {detail}")
                    if ok:
                        passed += 1
            else:
                console.print("[red]FAILED ❌[/red]")
        except Exception as e:
            console.print(f"[red]FAILED ❌[/red]\n   {e}")

    if passed == total:
        console.print(f"\n[bold green]All {total} checks passed![/bold green]\n")
    else:
        console.print(f"\n[bold yellow]{passed}/{total} checks passed — run 'sourcerykit init' to fix[/bold yellow]\n")
