"""Settings — all env vars used by sourcerykit."""

import functools
import os
import uuid
from dataclasses import dataclass

from sourcerykit.errors import SourceryKitConfigError

# TODO: Replace with uuid.NIL once the repository drops support for Python < 3.14
UUID_NIL = getattr(uuid, "NIL", uuid.UUID(int=0))

DEFAULT_PROVABLY_API_URL = "https://api.provably.ai"
DEFAULT_PROVABLY_APP_URL = "https://app.provably.ai"
DEFAULT_PROVABLY_MCP_URL = "https://mcp.provably.ai"


@dataclass(frozen=True)
class Settings:
    """All environment variables consumed by sourcerykit."""

    api_key: str
    """SOURCERYKIT_API_KEY — Provably API key."""

    org_id: uuid.UUID
    """SOURCERYKIT_ORG_ID — Provably organisation ID."""

    postgres_url: str
    """SOURCERYKIT_POSTGRES_URL — URL for the agent's Postgres database."""

    provably_app: str = DEFAULT_PROVABLY_APP_URL
    """SOURCERYKIT_PROVABLY_APP_URL — URL of the Provably APP."""

    provably_api: str = DEFAULT_PROVABLY_API_URL
    """SOURCERYKIT_PROVABLY_API_URL — URL of the Provably API."""

    provably_mcp: str = DEFAULT_PROVABLY_MCP_URL
    """SOURCERYKIT_PROVABLY_MCP_URL — URL of the Provably MCP server."""

    def __post_init__(self) -> None:
        """Validate required fields after initialization."""
        missing = []
        if not self.api_key:
            missing.append("SOURCERYKIT_API_KEY")
        if not self.org_id or self.org_id == UUID_NIL:
            missing.append("SOURCERYKIT_ORG_ID")
        if not self.postgres_url:
            missing.append("SOURCERYKIT_POSTGRES_URL")

        if missing:
            raise SourceryKitConfigError(
                f"SourceryKit configuration error: Missing required values for {', '.join(missing)}. "
                "Set these environment variables."
            )


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance populated from environment variables.

    The result is cached after the first call so env vars are read only once per process.
    """

    def _s(name: str) -> str:
        return (os.getenv(name) or "").strip()

    def _url(name: str) -> str:
        return _s(name).rstrip("/")

    _raw_org_id = _s("SOURCERYKIT_ORG_ID")
    if _raw_org_id:
        try:
            _org_id = uuid.UUID(_raw_org_id)
        except ValueError as e:
            raise SourceryKitConfigError(f"SOURCERYKIT_ORG_ID is not a valid UUID: {_raw_org_id!r}") from e
    else:
        _org_id = UUID_NIL

    return Settings(
        api_key=_url("SOURCERYKIT_API_KEY"),
        org_id=_org_id,
        postgres_url=_url("SOURCERYKIT_POSTGRES_URL"),
        provably_app=_url("SOURCERYKIT_PROVABLY_APP_URL") or DEFAULT_PROVABLY_APP_URL,
        provably_api=_url("SOURCERYKIT_PROVABLY_API_URL") or DEFAULT_PROVABLY_API_URL,
        provably_mcp=_url("SOURCERYKIT_PROVABLY_MCP_URL") or DEFAULT_PROVABLY_MCP_URL,
    )


def get_bootstrap_settings() -> str:
    """Return the Provably API URL without requiring full settings validation.

    Safe to call before ``api_key``, ``org_id``, or ``postgres_url`` are configured.
    """
    raw = (os.getenv("SOURCERYKIT_PROVABLY_API_URL") or "").strip().rstrip("/")
    return raw or DEFAULT_PROVABLY_API_URL
