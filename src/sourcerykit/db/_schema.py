"""SQLAlchemy Core table definitions."""

from sqlalchemy import (
    VARCHAR,
    Column,
    ForeignKey,
    Index,
    MetaData,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.ext.asyncio import AsyncEngine

metadata = MetaData()


async def ensure_schema(engine: AsyncEngine) -> None:
    """Idempotent: create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)


INTERCEPTS_TABLE = "intercepts"

intercepts = Table(
    INTERCEPTS_TABLE,
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
    Column("call_ref", UUID(as_uuid=True)),
    Column(
        "created_at",
        TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("NOW()"),
    ),
)

Index(
    "ix_intercepts_agent_action",
    intercepts.c.agent_id,
    intercepts.c.action_name,
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

TRACES_TABLE = "traces"

traces = Table(
    TRACES_TABLE,
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column("task", Text, nullable=False, server_default=text("''")),
    Column(
        "created_at",
        TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("NOW()"),
    ),
)

TRACE_INTERCEPTS_TABLE = "trace_intercepts"

trace_intercepts = Table(
    TRACE_INTERCEPTS_TABLE,
    metadata,
    Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
    Column("trace_id", UUID(as_uuid=True), ForeignKey("traces.id"), nullable=False),
    Column("intercept_id", UUID(as_uuid=True), ForeignKey("intercepts.id"), nullable=False),
    Column("query_id", UUID(as_uuid=True), nullable=False),
    Column("verification_mode", VARCHAR(50), nullable=False),
    Column("claimed_value", Text),
    Column("outcome", VARCHAR(20)),
    Column("details", Text),
    Column(
        "created_at",
        TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("NOW()"),
    ),
    Column(
        "updated_at",
        TIMESTAMP(timezone=False),
        server_default=text("NOW()"),
        onupdate=func.now(),
    ),
)

Index("ix_trace_intercepts_trace_id", trace_intercepts.c.trace_id)
Index("ix_trace_intercepts_query_id", trace_intercepts.c.query_id)
