"""Settings — all env vars used by sourcerykit."""

import dataclasses
import functools
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
from dotenv import dotenv_values, set_key

from sourcerykit.errors import SourceryKitConfigError

# TODO: Replace with uuid.NIL once the repository drops support for Python < 3.14
UUID_NIL = getattr(uuid, "NIL", uuid.UUID(int=0))

DEFAULT_PROVABLY_API_URL = "https://api.provably.ai"
DEFAULT_PROVABLY_APP_URL = "https://app.provably.ai"
DEFAULT_PROVABLY_MCP_URL = "https://mcp.provably.ai"


APP_NAME = "sourcerykit"
CONFIG_DIR = Path(typer.get_app_dir(APP_NAME))
CONFIG_FILE = CONFIG_DIR / "config.json"

LOCAL_ENV_FILE = Path(".env")


@dataclass(frozen=True)
class Settings:
    """All environment variables consumed by sourcerykit."""

    api_key: str
    """PROVABLY_API_KEY — Provably API key."""

    org_id: uuid.UUID
    """SOURCERYKIT_ORG_ID — Provably organisation ID."""

    postgres_url: str = ""
    """SOURCERYKIT_POSTGRES_URL — URL for the agent's Postgres database."""

    project_name: str = ""
    """SOURCERYKIT_PROJECT_NAME — Project name, used as the Provably collection name."""

    provably_app: str = DEFAULT_PROVABLY_APP_URL
    """SOURCERYKIT_PROVABLY_APP_URL — URL of the Provably APP."""

    provably_api: str = DEFAULT_PROVABLY_API_URL
    """SOURCERYKIT_PROVABLY_API_URL — URL of the Provably API."""

    provably_mcp: str = DEFAULT_PROVABLY_MCP_URL
    """SOURCERYKIT_PROVABLY_MCP_URL — URL of the Provably MCP server."""

    # Bootstrap resource IDs (resolved during init, cached in local .env)
    middleware_id: uuid.UUID | None = None
    database_id: uuid.UUID | None = None
    schema_id: uuid.UUID | None = None
    table_id: uuid.UUID | None = None
    collection_id: uuid.UUID | None = None
    integration_key: str | None = None

    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        missing = []
        if not self.api_key:
            missing.append("PROVABLY_API_KEY")
        if not self.org_id or self.org_id == UUID_NIL:
            missing.append("SOURCERYKIT_ORG_ID")

        if missing:
            raise SourceryKitConfigError(
                f"SourceryKit configuration error: Missing required values for {', '.join(missing)}. "
                "Run 'sourcerykit init' to configure."
            )

    @property
    def has_bootstrap_ids(self) -> bool:
        """Return True if all bootstrap resource IDs are present."""
        return all(
            getattr(self, f.name)
            for f in dataclasses.fields(self)
            if f.name.endswith("_id") or f.name == "integration_key"
        )


@functools.lru_cache(maxsize=1)
def load_app_dir_config() -> dict[str, Any]:
    """Read the JSON from the OS app directory."""
    if CONFIG_FILE.exists():
        try:
            data: dict[str, Any] = json.loads(CONFIG_FILE.read_text())
            return data
        except (json.JSONDecodeError, PermissionError):
            return {}
    return {}


# Global config file (user-level config)
def save_app_dir_config(
    api_key: str | None = None, org_id: str | None = None, token: str | None = None, email: str | None = None
) -> None:
    """Save global configuration (user-level) to the OS app directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = load_app_dir_config()

    if api_key is not None:
        payload["api_key"] = api_key
    if org_id is not None:
        payload["org_id"] = org_id
    if token is not None:
        payload["token"] = token
    if email is not None:
        payload["email"] = email

    CONFIG_FILE.write_text(json.dumps(payload))
    os.chmod(CONFIG_FILE, 0o600)

    load_app_dir_config.cache_clear()
    get_settings.cache_clear()


# Local .env file (project-level config)
@functools.lru_cache(maxsize=1)
def load_local_env() -> dict[str, str]:
    """Read the local .env file from the current working directory."""
    raw = dotenv_values(LOCAL_ENV_FILE)
    return {k: v for k, v in raw.items() if v is not None}


def save_local_env(**kwargs: str) -> None:
    """Write or update the local .env file with the given key-value pairs."""
    for key, value in kwargs.items():
        set_key(str(LOCAL_ENV_FILE), key, value)

    load_local_env.cache_clear()
    get_settings.cache_clear()


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance populated from environment variables.

    The result is cached after the first call so env vars are read only once per process.
    """
    file_config = load_app_dir_config()
    local_env = load_local_env()

    def _resolve(env_name: str, json_key: str) -> str:
        """Fallback chain resolution helper: Env -> JSON File -> Empty String"""
        val = os.getenv(env_name)
        if val is not None:
            return val.strip()

        # Fallback to get_app_dir JSON data
        return str(file_config.get(json_key, "")).strip()

    def _local_resolve(env_name: str, local_key: str) -> str:
        """Fallback chain: Env -> local .env -> Empty String"""
        val = os.getenv(env_name)
        if val is not None:
            return val.strip()
        return local_env.get(local_key, "").strip()

    def _url(env_name: str, json_key: str) -> str:
        return _resolve(env_name, json_key).rstrip("/")

    _raw_org_id = _resolve("SOURCERYKIT_ORG_ID", "org_id")
    if _raw_org_id:
        try:
            _org_id = uuid.UUID(_raw_org_id)
        except ValueError as e:
            raise SourceryKitConfigError(f"SOURCERYKIT_ORG_ID is not a valid UUID: {_raw_org_id!r}") from e
    else:
        _org_id = UUID_NIL

    def _opt_uuid(env_name: str, local_key: str) -> uuid.UUID | None:
        raw = _local_resolve(env_name, local_key)
        if not raw:
            return None
        try:
            return uuid.UUID(raw)
        except ValueError:
            return None

    return Settings(
        api_key=_url("PROVABLY_API_KEY", "api_key"),
        org_id=_org_id,
        postgres_url=_local_resolve("SOURCERYKIT_POSTGRES_URL", "SOURCERYKIT_POSTGRES_URL"),
        project_name=_local_resolve("SOURCERYKIT_PROJECT_NAME", "SOURCERYKIT_PROJECT_NAME"),
        provably_app=_url("SOURCERYKIT_PROVABLY_APP_URL", "provably_app") or DEFAULT_PROVABLY_APP_URL,
        provably_api=_url("SOURCERYKIT_PROVABLY_API_URL", "provably_api") or DEFAULT_PROVABLY_API_URL,
        provably_mcp=_url("SOURCERYKIT_PROVABLY_MCP_URL", "provably_mcp") or DEFAULT_PROVABLY_MCP_URL,
        middleware_id=_opt_uuid("SOURCERYKIT_MIDDLEWARE_ID", "SOURCERYKIT_MIDDLEWARE_ID"),
        database_id=_opt_uuid("SOURCERYKIT_DATABASE_ID", "SOURCERYKIT_DATABASE_ID"),
        schema_id=_opt_uuid("SOURCERYKIT_SCHEMA_ID", "SOURCERYKIT_SCHEMA_ID"),
        table_id=_opt_uuid("SOURCERYKIT_TABLE_ID", "SOURCERYKIT_TABLE_ID"),
        collection_id=_opt_uuid("SOURCERYKIT_COLLECTION_ID", "SOURCERYKIT_COLLECTION_ID"),
        integration_key=_local_resolve("SOURCERYKIT_INTEGRATION_KEY", "SOURCERYKIT_INTEGRATION_KEY") or None,
    )


def get_bootstrap_settings() -> str:
    """Return the Provably API URL without requiring full settings validation.

    Safe to call before ``api_key``, ``org_id``, or ``postgres_url`` are configured.
    """
    raw = (os.getenv("SOURCERYKIT_PROVABLY_API_URL") or "").strip().rstrip("/")
    if not raw:
        raw = load_app_dir_config().get("provably_api", "").strip().rstrip("/")
    return raw or DEFAULT_PROVABLY_API_URL
