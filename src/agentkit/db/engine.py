"""SQLAlchemy engine"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from agentkit.config import get_settings

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

    _ENGINE = create_async_engine(
        dsn,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        json_serializer=None,
    )

    return _ENGINE
