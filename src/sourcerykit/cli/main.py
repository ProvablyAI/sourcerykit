"""SourceryKit bootstrap wizard"""

import asyncio
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import quote

import psycopg
import questionary
from dotenv import set_key

from sourcerykit.cli import logo
from sourcerykit.config import Settings
from sourcerykit.errors import SourceryKitConfigError
from sourcerykit.provably._auth_api import Organization, OrganizationType, User
from sourcerykit.provably._errors import (
    ProvablyConnectionError,
    ProvablyUnauthorizedError,
)
from sourcerykit.provably.auth_service import ProvablyAuthService

service = ProvablyAuthService()


# ------------------------------------------------------------------
# PHASE 4 & 5 UTILITIES
# ------------------------------------------------------------------


def _print_credentials(api_key: str, org_id: str, postgres_url: str) -> None:
    print("\n" + "π" * 65)
    print(" 🎉 SOURCERYKIT CREDENTIALS GENERATED")
    print("π" * 65)
    print(f" PROVABLY_API_KEY      = {api_key}")
    print(f" SOURCERYKIT_ORG_ID       = {org_id}")
    print(f" SOURCERYKIT_POSTGRES_URL = {postgres_url}")
    print("π" * 65 + "\n")


def _save_to_env(api_key: str, org_id: str, postgres_url: str) -> None:
    """Prompts for the environment path and synchronizes setup credentials using python-dotenv."""
    print("\n" + "─" * 65)
    print(" 💾 Save your environment variables")
    print("─" * 65)
    path_input = questionary.text(
        message="Where should we save these environment variables?",
        default=".env",
        validate=lambda text: True if len(text.strip()) > 0 else "Path cannot be empty.",
    ).ask()

    if not path_input:
        print("⚠️ Skipped saving to file.")
        return

    path = path_input.strip()

    try:
        Path(path).touch(exist_ok=True)

        set_key(path, "PROVABLY_API_KEY", api_key)
        set_key(path, "SOURCERYKIT_ORG_ID", org_id)
        set_key(path, "SOURCERYKIT_POSTGRES_URL", postgres_url)

        print(f"✨ Saved successfully to {path}!")

    except Exception as e:
        print(f"❌ Failed to write to {path}: {e}")


def _ask_postgres_url() -> str:
    print("\nEnter your remote database details:")

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
    password = answers["password"]
    database = answers["database"].strip()

    return f"postgresql://{quote(username, safe='')}:{quote(password, safe='')}@{host}:{port}/{database}"


def _run_connectivity_check(api_key: str, org_id: str, postgres_url: str) -> bool:
    """Validate credential format then test the Postgres connection."""
    try:
        Settings(
            api_key=api_key,
            org_id=uuid.UUID(org_id),
            postgres_url=postgres_url,
        )
    except (SourceryKitConfigError, ValueError) as e:
        print(f"\n❌ Invalid format. Details: {e}")
        return False

    print("Testing database connection...", end=" ", flush=True)
    try:
        with psycopg.connect(postgres_url):
            pass
        print("CONNECTED ✅")
        print("✨ Database check passed successfully!")
        return True

    except Exception as e:
        print("FAILED ❌")
        print("\n⚠️ Connection Error: Could not reach your database.")
        print(f"Details: {e}")
        print("Please double-check your credentials, firewall, or routing rules.\n")
        return False


def _collect_register_inputs() -> dict[str, Any]:
    print("\n" + "─" * 65)
    print(" 🔑 Create your account")
    print("─" * 65)
    questions = [
        {
            "type": "text",
            "name": "email",
            "message": "Email address:",
            "validate": lambda text: True if len(text.strip()) > 0 else "Email cannot be empty.",
        },
        {
            "type": "password",
            "name": "password",
            "message": "Password:",
            "validate": lambda text: True if len(text.strip()) > 0 else "Password cannot be empty.",
        },
    ]
    return questionary.prompt(questions) or {}


def _collect_org_inputs() -> dict[str, Any]:
    org_type_choices = [{"name": t.value, "value": t} for t in OrganizationType]

    questions: list[dict[str, Any]] = [
        {
            "type": "text",
            "name": "handle",
            "message": "Organisation handle (unique slug, e.g. my-org):",
            "validate": lambda text: True if len(text.strip()) > 0 else "Handle cannot be empty.",
        },
        {
            "type": "text",
            "name": "name",
            "message": "Organisation display name:",
            "validate": lambda text: True if len(text.strip()) > 0 else "Name cannot be empty.",
        },
        {
            "type": "select",
            "name": "org_type",
            "message": "Organisation type:",
            "choices": org_type_choices,
        },
    ]
    return questionary.prompt(questions) or {}


# ------------------------------------------------------------------
# PHASE 2: CREDENTIAL COLLECTION & ACCOUNT SETUP
# ------------------------------------------------------------------


def _run_register() -> str:
    """Handles the user registration setup path."""
    inputs = _collect_register_inputs()
    if not inputs:
        return ""

    email: str = inputs.get("email", "").strip()
    user = User(email=email, password=inputs["password"])

    # --- Create account ---
    try:
        print("\nCreating your account...")
        asyncio.run(service.create_account(user))
        print("\n" + "π" * 65)
        print(" We've sent a verification link to your email inbox.")
        print(" Please check your mail and verify your account to continue.")
        print("π" * 65)
        print("\n📌 NEXT STEPS:")
        print(" 1. Click the link in your email to verify your account.")
        print(" 2. Return here, choose 'Log in', and link your database.")
        print("\n" + "─" * 65)

        print("\n")
        questionary.press_any_key_to_continue("Press any key to return to the main menu...").ask()
        return email

    except ProvablyConnectionError as e:
        print(f"❌ Network error during registration: {e}")
        return ""


def _run_login(*, prefill_email: str = "") -> None:
    """Handles authentication."""
    print("\n" + "─" * 65)
    print(" 🔐 Log in to your account")
    print("─" * 65)
    email = questionary.text(
        message="Email address:",
        default=prefill_email,
        validate=lambda text: True if len(text.strip()) > 0 else "Email cannot be empty.",
    ).ask()
    if not email:
        return

    password = questionary.password(
        message="Password:",
        validate=lambda text: True if len(text.strip()) > 0 else "Password cannot be empty.",
    ).ask()
    if not password:
        return

    try:
        print("\nLogging in...")
        result = asyncio.run(service.login(User(email=email, password=password)))
    except ProvablyUnauthorizedError:
        print("\n❌ Invalid email/password, or your account isn't verified yet.")
        print("Please check your verification link or try again.")
        return
    except ProvablyConnectionError as e:
        print(f"❌ Network error: {e}")
        return

    token = result.get("token") or result.get("access_token", "")
    if not token:
        print("❌ Login failed: Token missing from API response.")
        return

    _execute_post_auth_phases(token)


# ------------------------------------------------------------------
# PHASE 3, 4, & 5: ORGANIZATION, DATABASE, AND ENV
# ------------------------------------------------------------------


def _execute_post_auth_phases(token: str) -> None:
    """Executes the organisation, database configuration, and saving steps."""

    # --- PHASE 3: ORGANIZATION ---
    try:
        orgs = asyncio.run(service.get_organizations(token))
    except ProvablyConnectionError as e:
        print(f"❌ Error fetching organizations: {e}")
        orgs = []

    if not orgs:
        while True:
            print("\n" + "─" * 65)
            print(" 🏢 Create your organization workspace")
            print("─" * 65)
            print("No organizations found for this account. Let's create a new one.")
            org_inputs = _collect_org_inputs()
            if not org_inputs:
                return

            org = Organization(
                handle=org_inputs["handle"],
                name=org_inputs["name"],
                organization_type=org_inputs["org_type"],
            )

            try:
                print("Creating organization...")
                org_id = str(asyncio.run(service.create_organization(token, org)))
                break
            except ProvablyConnectionError as e:
                print(f"❌ Network error: {e}")
                return
            except Exception as e:
                error_msg = str(e)
                if "Handle already exists" in error_msg:
                    print(f"\n❌ Error: The handle '{org_inputs['handle']}' is already taken.")
                    retry = questionary.confirm(
                        message="Would you like to try again with a different handle?", default=True
                    ).ask()
                    if not retry:
                        print("Setup cancelled.")
                        return
                    continue
                else:
                    print(f"❌ Error: Unexpected issue occurred: {e}")
                    return

    elif len(orgs) == 1:
        id = orgs[0]["id"]
        org_id = str(id)
    else:
        print("\n" + "─" * 65)
        print(" 🏢 Choose your organization workspace")
        print("─" * 65)
        choices = [{"name": f"{o.get('name', o['id'])} ({o['id']})", "value": str(o["id"])} for o in orgs]
        org_id = questionary.select(
            message="Select an organization to use:",
            choices=choices,
        ).ask()

    if not org_id:
        return

    try:
        api_key = asyncio.run(service.get_api_key(token))
    except ProvablyConnectionError as e:
        print(f"❌ Error retrieving API key: {e}")
        return
    except Exception as e:
        print(f"❌ Key exchange failed: {e}")
        return

    # --- PHASE 4: DATABASE ---
    print("\n" + "π" * 65)
    print(" 🛠️  Link your Postgres database")
    print("π" * 65)
    print(" SourceryKit requires access to a dedicated PostgreSQL database to")
    print(" automatically maintain your 'Intercepts Table'. This table acts")
    print(" as an append-only transaction ledger, logging every request and")
    print(" response for secure historical tracking and system auditing.")
    print("")
    print(" ⚠️  DATABASE REQUIREMENTS:")
    print(" • Only PostgreSQL databases are supported.")
    print(" • The database MUST be hosted and publicly accessible over the web.")
    print(" • Local databases (localhost / 127.0.0.1) will NOT work.")
    print("π" * 65)

    while True:
        postgres_url = _ask_postgres_url()
        if not postgres_url:
            print("⚠️ Database setup cancelled.")
            return

        # Immediate verification call
        success = _run_connectivity_check(api_key, org_id, postgres_url)
        if success:
            break

        retry = questionary.confirm(
            message="Connection failed. Would you like to check your details and try again?", default=True
        ).ask()

        if not retry:
            print("⚠️ Setup aborted.")
            return

    # --- PHASE 5: ENV ---
    _save_to_env(api_key, org_id, postgres_url)
    _print_credentials(api_key, org_id, postgres_url)


def main() -> None:
    print(logo.print_logo(), "\n\n")

    saved_email = ""

    while True:
        action = questionary.select(
            message="Welcome to the SourceryKit Wizard! How would you like to proceed?",
            choices=[
                {"name": "Log in with an existing account", "value": "login"},
                {"name": "Create a new account", "value": "register"},
                {"name": "Exit", "value": "exit"},
            ],
        ).ask()

        if action == "exit" or not action:
            print("\n👋 Setup closed. Happy coding!")
            return

        if action == "register":
            saved_email = _run_register()
        else:
            _run_login(prefill_email=saved_email)


if __name__ == "__main__":
    main()
