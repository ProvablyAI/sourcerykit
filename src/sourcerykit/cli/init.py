"""SourceryKit bootstrap wizard"""

import asyncio
import sys
import uuid

import questionary
import typer

from sourcerykit.bootstrap._cache import _BOOTSTRAP_INSTANCE
from sourcerykit.cli import logo
from sourcerykit.cli.utils import (
    console,
    logout,
    mask_postgres_url,
    mask_secret,
    prompt_postgres_url_with_retry,
    prompt_project_name,
)
from sourcerykit.config import load_app_dir_config, save_app_dir_config, save_local_env
from sourcerykit.db._engine import get_engine
from sourcerykit.db._schema import ensure_schema
from sourcerykit.provably._api import get_api as get_main_api
from sourcerykit.provably._auth_api import Organization, OrganizationType
from sourcerykit.provably._errors import (
    ProvablyConnectionError,
    ProvablyUnauthorizedError,
)
from sourcerykit.provably._http import get_http
from sourcerykit.provably.auth_service import ProvablyAuthService
from sourcerykit.provably.oauth_login import browser_login, fetch_user_email
from sourcerykit.provably.service import service as provably_service

service = ProvablyAuthService()


def _run_oauth_browser(
    *,
    postgres_url: str | None = None,
    project_name: str | None = None,
    sandbox: bool = False,
) -> None:
    """OAuth2 browser login, then run the post-auth setup phases.

    Opens the consent page in the browser, fetches the logged-in user's email
    from ``/api/v1/user/current``, and continues with the database/project setup.
    """
    try:
        console.print("\n[bold]🔐 Browser authentication[/bold]")
        tokens = asyncio.run(browser_login())
        email = asyncio.run(fetch_user_email(tokens.access_token))
    except ProvablyConnectionError as e:
        console.print(f"[red]❌ Network error: {e}[/red]")
        return
    except Exception as e:
        console.print(f"[red]❌ Browser login failed: {e}[/red]")
        return

    save_app_dir_config(token=tokens.access_token, refresh_token=tokens.refresh_token, email=email)
    if _execute_post_auth_phases(
        tokens.access_token,
        email=email,
        postgres_url=postgres_url,
        project_name=project_name,
        sandbox=sandbox,
    ):
        console.print("\n👋 Setup closed. Happy coding!")
        raise typer.Exit()


# --- Bootstrap helpers ---
def clear_auth_caches() -> None:
    """Clear cached HTTP/API singletons so they pick up new credentials."""
    get_http.cache_clear()
    get_main_api.cache_clear()


def create_db_tables() -> None:
    """Create all database tables defined in the metadata. Raises on failure."""
    asyncio.run(ensure_schema(get_engine()))


def run_provably_handshake(project_name: str) -> None:
    """Run the Provably handshake for the given project. Raises on failure."""
    asyncio.run(_BOOTSTRAP_INSTANCE.run_handshake(project_name=project_name))


def save_bootstrap_ids() -> None:
    """Persist bootstrap IDs from the current handshake result to the local .env."""
    save_local_env(
        SOURCERYKIT_MIDDLEWARE_ID=str(_BOOTSTRAP_INSTANCE.middleware_id),
        SOURCERYKIT_DATABASE_ID=str(_BOOTSTRAP_INSTANCE.database_id),
        SOURCERYKIT_SCHEMA_ID=str(_BOOTSTRAP_INSTANCE.schema_id),
        SOURCERYKIT_TABLE_ID=str(_BOOTSTRAP_INSTANCE.table_id),
        SOURCERYKIT_COLLECTION_ID=str(_BOOTSTRAP_INSTANCE.collection_id),
        SOURCERYKIT_INTEGRATION_KEY=str(_BOOTSTRAP_INSTANCE.integration_key),
    )


def run_full_bootstrap(project_name: str, *, sandbox: bool = False) -> bool:
    """Run the full bootstrap: clear caches, create tables, handshake, save IDs.

    Returns True on success, False on failure (errors are printed).
    """
    clear_auth_caches()

    if not sandbox:
        console.print(" Creating database tables...", end=" ")
        sys.stdout.flush()
        try:
            create_db_tables()
            console.print("DONE ✅")
        except Exception as e:
            console.print(f"[red]FAILED ❌[/red]\n   {e}")
            return False

    console.print(" Running Provably handshake...", end=" ")
    sys.stdout.flush()
    try:
        run_provably_handshake(project_name)
        console.print("DONE ✅")
    except Exception as e:
        console.print(f"[red]FAILED ❌[/red]\n   {e}")
        return False

    save_bootstrap_ids()
    return True


# --- Post auth phases: organization, database, project name, bootstrap, save all


def _execute_post_auth_phases(
    token: str,
    *,
    email: str,
    postgres_url: str | None = None,
    project_name: str | None = None,
    sandbox: bool = False,
) -> bool:
    """Executes organisation, database, project, bootstrap, and saving steps."""

    # --- organization ---
    try:
        orgs = asyncio.run(service.get_organizations(token))
    except ProvablyConnectionError as e:
        console.print(f"[red]❌ Error fetching organizations: {e}[/red]")
        orgs = []

    if not orgs:
        base_handle = email.split("@")[0].strip().lower()
        handle = base_handle
        attempt = 1
        org_id = ""

        console.print(f"\n🏢 Creating organization '{handle}'...")
        max_attempts = 10
        while attempt <= max_attempts:
            org = Organization(
                handle=handle,
                name=handle,
                organization_type=OrganizationType.DEMOGRAPHICS,
            )
            try:
                org_id = str(asyncio.run(service.create_organization(token, org)))
                console.print(f"  ✅ Organization created: {handle}")
                break
            except ProvablyConnectionError as e:
                console.print(f"[red]❌ Network error: {e}[/red]")
                return False
            except Exception as e:
                if "Handle already exists" in str(e):
                    attempt += 1
                    if attempt > max_attempts:
                        console.print(
                            f"[red]❌ Could not find an available handle after {max_attempts} attempts.[/red]"
                        )
                        return False
                    handle = f"{base_handle}-{attempt}"
                    console.print(f"  ⚠️  Handle taken, retrying as '{handle}'...")
                    continue
                console.print(f"[red]❌ Error: {e}[/red]")
                return False

    elif len(orgs) == 1:
        org_id = str(orgs[0]["id"])
    else:
        console.print("\n[bold]🏢 Choose your organization workspace[/bold]")
        choices = [{"name": f"{o.get('name', o['id'])} ({o['id']})", "value": str(o["id"])} for o in orgs]
        org_id = questionary.select(
            message="Select an organization to use:",
            choices=choices,
        ).ask()

    if not org_id:
        return False

    try:
        api_key = asyncio.run(service.get_api_key(token))
    except ProvablyConnectionError as e:
        console.print(f"[red]❌ Error retrieving API key: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Key exchange failed: {e}[/red]")
        return False

    save_app_dir_config(api_key=api_key, org_id=org_id)
    clear_auth_caches()

    # --- database ---
    if sandbox:
        console.print("\n[bold]🗄️  Creating hosted sandbox database...[/bold]")
        try:
            postgres_url = asyncio.run(provably_service.create_sandbox(uuid.UUID(org_id), token=token))
            console.print("  ✅ Sandbox created")
        except Exception as e:
            console.print(f"[red]❌ Failed to create sandbox: {e}[/red]")
            return False
    else:
        console.print("\n[bold]🗄️  Database setup[/bold]")
        console.print(" SourceryKit requires access to a dedicated PostgreSQL database to")
        console.print(" automatically maintain your 'Intercepts Table'. This table acts")
        console.print(" as an append-only transaction ledger, logging every request and")
        console.print(" response for secure historical tracking and system auditing.\n")

        if postgres_url:
            # Non-interactive: use provided URL
            postgres_url = prompt_postgres_url_with_retry(postgres_url)
        else:
            db_choice = questionary.select(
                message="How would you like to set up your database?",
                choices=[
                    {"name": "Hosted sandbox (recommended)", "value": "sandbox"},
                    {"name": "Use my own PostgreSQL database", "value": "own"},
                ],
            ).ask()

            if not db_choice:
                console.print("[yellow]⚠️ Database setup cancelled.[/yellow]")
                return False

            if db_choice == "sandbox":
                try:
                    postgres_url = asyncio.run(provably_service.create_sandbox(uuid.UUID(org_id), token=token))
                    sandbox = True
                    console.print("  ✅ Sandbox created")
                except Exception as e:
                    console.print(f"[red]❌ Failed to create sandbox: {e}[/red]")
                    return False
            else:
                console.print(" [bold]⚠️  DATABASE REQUIREMENTS:[/bold]")
                console.print(" • Only PostgreSQL databases are supported.")
                console.print(" • The database MUST be hosted and publicly accessible over the web.")
                console.print(" • Local databases (localhost / 127.0.0.1) will NOT work.")
                postgres_url = prompt_postgres_url_with_retry(postgres_url)

        if not postgres_url:
            console.print("[yellow]⚠️ Database setup cancelled.[/yellow]")
            return False

    # --- project name ---
    console.print("\n[bold]📦 Name your project[/bold]")
    project_name = prompt_project_name(project_name=project_name)
    if not project_name:
        console.print("[yellow]⚠️ Setup aborted.[/yellow]")
        return False

    # --- save all ---
    console.print("\n[bold]🔧 Bootstrapping Provably resources...[/bold]")

    save_local_env(
        SOURCERYKIT_PROJECT_NAME=project_name,
        SOURCERYKIT_POSTGRES_URL=postgres_url,
    )

    run_full_bootstrap(project_name, sandbox=sandbox)

    console.print("\n[bold green]🎉 SOURCERYKIT SETUP COMPLETE[/bold green]\n")
    console.print(" Global config:")
    console.print(f"   PROVABLY_API_KEY    = {mask_secret(api_key)}")
    console.print(f"   SOURCERYKIT_ORG_ID  = {org_id}\n")
    console.print(" Local config (.env):")
    console.print(f"   SOURCERYKIT_PROJECT_NAME    = {project_name}")
    console.print(f"   SOURCERYKIT_POSTGRES_URL    = {mask_postgres_url(postgres_url)}")
    console.print(f"   SOURCERYKIT_COLLECTION_ID   = {_BOOTSTRAP_INSTANCE.collection_id}")
    integration_key = _BOOTSTRAP_INSTANCE.integration_key or ""
    console.print(f"   SOURCERYKIT_INTEGRATION_KEY = {mask_secret(integration_key)}\n")
    return True


def config_provably(
    *,
    postgres_url: str | None = None,
    project_name: str | None = None,
    sandbox: bool = False,
) -> None:
    console.print(logo.print_logo(), "\n\n")

    # Non-interactive: any flag implies a browser login, then continue with the flags.
    if postgres_url or project_name or sandbox:
        _run_oauth_browser(postgres_url=postgres_url, project_name=project_name, sandbox=sandbox)
        return

    while True:
        global_cfg = load_app_dir_config()
        stored_token = global_cfg.get("token", "")
        stored_email_addr = global_cfg.get("email", "")

        if stored_token:
            action = questionary.select(
                message="Welcome to the SourceryKit Wizard! How would you like to proceed?",
                choices=[
                    {"name": "Continue (stored session)", "value": "continue"},
                    {"name": "Logout", "value": "logout"},
                    {"name": "Exit", "value": "exit"},
                ],
            ).ask()

            if action == "exit" or not action:
                console.print("\n👋 Setup closed. Happy coding!")
                return

            if action == "logout":
                logout()
                console.print("🔒 Logged out.\n")
                continue

            # continue — try stored token
            try:
                if _execute_post_auth_phases(
                    stored_token,
                    email=stored_email_addr,
                    postgres_url=postgres_url,
                    project_name=project_name,
                    sandbox=sandbox,
                ):
                    console.print("\n👋 Setup closed. Happy coding!")
                    raise typer.Exit()
            except ProvablyUnauthorizedError:
                console.print("[yellow]⚠️  Stored session expired. Please log in again.[/yellow]\n")
                # Clear expired token so next iteration shows the browser login
                logout()
                continue
        else:
            action = questionary.select(
                message="Welcome to the SourceryKit Wizard! How would you like to proceed?",
                choices=[
                    {"name": "Log in with browser (OAuth)", "value": "oauth"},
                    {"name": "Exit", "value": "exit"},
                ],
            ).ask()

            if action == "exit" or not action:
                console.print("\n👋 Setup closed. Happy coding!")
                return

            _run_oauth_browser(sandbox=sandbox)
