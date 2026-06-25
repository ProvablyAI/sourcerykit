"""SQLAlchemy Core table definitions."""

from sqlalchemy import (
    VARCHAR,
    Column,
    Index,
    MetaData,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.ext.asyncio import AsyncEngine

metadata = MetaData()


async def ensure_schema(engine: AsyncEngine) -> None:
    """Idempotent: create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


PROVABLY_INTERCEPTS_TABLE = "provably_intercepts"

provably_intercepts = Table(
    PROVABLY_INTERCEPTS_TABLE,
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column("agent_id", VARCHAR(255), nullable=False),
    Column("action_name", VARCHAR(255), nullable=False),
    Column("source_url", Text, nullable=False),
    Column("request_payload", Text, nullable=False, server_default=text("'{}'")),
    Column("raw_response", Text, nullable=False),
    Column("response_hash", VARCHAR(64), nullable=False),
    Column(
        "created_at",
        TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("NOW()"),
    ),
)

Index(
    "ix_provably_intercepts_agent_action",
    provably_intercepts.c.agent_id,
    provably_intercepts.c.action_name,
)

TRUSTED_ENDPOINTS_TABLE = "trusted_endpoints"

trusted_endpoints = Table(
    TRUSTED_ENDPOINTS_TABLE,
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column("org_id", UUID(as_uuid=True), nullable=False),
    Column("entry_type", VARCHAR(50), nullable=False, server_default=text("'endpoint'")),
    Column("normalized_url", Text, nullable=False),
    Column("display_label", VARCHAR(255)),
    Column("policy_version", VARCHAR(20), server_default=text("'v1'")),
    Column("created_at", TIMESTAMP(timezone=False), server_default=text("NOW()")),
    Column("revoked_at", TIMESTAMP(timezone=False)),
    Column("created_by", VARCHAR(255)),
)

Index(
    "uix_trusted_endpoints_org_url_active",
    trusted_endpoints.c.org_id,
    trusted_endpoints.c.normalized_url,
    postgresql_where=trusted_endpoints.c.revoked_at.is_(None),
    unique=True,
)
