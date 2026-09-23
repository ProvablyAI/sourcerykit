"""SQLAlchemy engine"""

from provably import ConnectionInfo
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sourcerykit.config import get_settings
from sourcerykit.errors import SourceryKitConfigError, SourceryKitStorageError
from sourcerykit.logger import get_logger

_log = get_logger(__name__)


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
        raise SourceryKitConfigError(f"SOURCERYKIT_POSTGRES_URL must start with 'postgresql', got: {url!r}")

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
        raise SourceryKitStorageError("Failed to create database engine") from e

    _log.info("db_engine_created", provider="postgresql")
    return _ENGINE


def get_connection_info() -> ConnectionInfo:
    """
    Return the parsed connection details of the configured PostgreSQL URL.
    """
    return ConnectionInfo.from_url(get_settings().postgres_url)
