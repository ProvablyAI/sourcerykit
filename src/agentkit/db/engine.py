"""SQLAlchemy engine"""

from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from agentkit.config import get_settings
from agentkit.errors import AgentKitStorageError
from agentkit.logger import get_logger

_log = get_logger(__name__)


@dataclass
class ConnectionInfo:
    name: str
    username: str
    password: str
    provider: str
    uri: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "username": self.username,
            "password": self.password,
            "provider": self.provider,
            "uri": self.uri,
        }


# Internal singleton to ensure we only ever create one engine per process
_ENGINE: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """
    Return a singleton SQLAlchemy engine for PostgreSQL.
    """

    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    url = get_settings().postgres_url

    if not url.startswith("postgresql"):
        raise ValueError(f"AGENTKIT_POSTGRES_URL must start with 'postgresql', got: {url!r}")

    # Ensure we use psycopg v3 (the +psycopg dialect)
    if "://+" not in url:
        if url.startswith("postgresql://"):
            dsn = url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql+psycopg2://"):
            dsn = url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
        else:
            dsn = url
    else:
        dsn = url

    try:
        _ENGINE = create_async_engine(
            dsn,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            json_serializer=None,
        )
    except Exception as e:
        _log.error("db_engine_creation_failed", error=str(e))
        raise AgentKitStorageError("Failed to create database engine") from e

    _log.info("db_engine_created", provider="postgresql")
    return _ENGINE


def get_connection_info() -> ConnectionInfo:
    """
    Return the parsed connection details of the configured PostgreSQL URL.
    """
    url = get_settings().postgres_url
    parsed = urlparse(url)

    provider = parsed.scheme.split("+", 1)[0]

    host = parsed.hostname or ""
    port = parsed.port
    uri = f"{host}:{port}" if port else host

    return ConnectionInfo(
        name=parsed.path.lstrip("/"),
        username=parsed.username or "",
        password=parsed.password or "",
        provider=provider,
        uri=uri,
    )
