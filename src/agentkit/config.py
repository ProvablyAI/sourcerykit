"""Settings — all env vars used by agentkit."""

import functools
import os
import uuid
from dataclasses import dataclass

from agentkit.errors import AgentKitConfigError


@dataclass(frozen=True)
class Settings:
    """All environment variables consumed by agentkit."""

    api_key: str
    """AGENTKIT_API_KEY — Provably API key."""

    org_id: uuid.UUID
    """AGENTKIT_ORG_ID — Provably organisation ID."""

    postgres_url: str
    """AGENTKIT_POSTGRES_URL — URL for the agent's Postgres database."""

    provably_app: str = "https://app.provably.ai"
    """AGENTKIT_PROVABLY_APP_URL — URL of the Provably APP."""

    provably_api: str = "https://api.provably.ai"
    """AGENTKIT_PROVABLY_API_URL — URL of the Provably API."""

    provably_mcp: str = "https://mcp.provably.ai"
    """AGENTKIT_PROVABLY_MCP_URL — URL of the Provably MCP server."""

    def __post_init__(self):
        """Validate required fields after initialization."""
        missing = []
        if not self.api_key:
            missing.append("AGENTKIT_API_KEY")
        if not self.org_id or self.org_id == uuid.NIL:
            missing.append("AGENTKIT_ORG_ID")
        if not self.postgres_url:
            missing.append("AGENTKIT_POSTGRES_URL")

        if missing:
            raise AgentKitConfigError(
                f"AgentKit configuration error: Missing required values for {', '.join(missing)}. "
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

    _raw_org_id = _s("AGENTKIT_ORG_ID")
    if _raw_org_id:
        try:
            _org_id = uuid.UUID(_raw_org_id)
        except ValueError as e:
            raise AgentKitConfigError(f"AGENTKIT_ORG_ID is not a valid UUID: {_raw_org_id!r}") from e
    else:
        _org_id = uuid.NIL

    return Settings(
        api_key=_url("AGENTKIT_API_KEY"),
        org_id=_org_id,
        postgres_url=_url("AGENTKIT_POSTGRES_URL"),
        provably_app=_url("AGENTKIT_PROVABLY_APP_URL") or "https://app.provably.ai",
        provably_api=_url("AGENTKIT_PROVABLY_API_URL") or "https://api.provably.ai",
        provably_mcp=_url("AGENTKIT_PROVABLY_MCP_URL") or "https://mcp.provably.ai",
    )
