"""SQLAlchemy Core table definitions."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    MetaData,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP

metadata = MetaData()

provably_intercepts = Table(
    "provably_intercepts",
    metadata,
    Column("id", Text, primary_key=True, server_default=text("nextval('provably_intercepts_id_seq')")),
    Column("agent_id", Text, nullable=False),
    Column("action_name", Text, nullable=False),
    Column("source_url", Text, nullable=False),
    Column("request_payload", Text, nullable=False, server_default=text("'{}'")),
    Column("raw_response", Text, nullable=False),
    Column("response_hash", Text, nullable=False),
    Column(
        "created_at",
        TIMESTAMP(timezone=False),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    ),
)

trusted_endpoints = Table(
    "trusted_endpoints",
    metadata,
    Column("id", Text, primary_key=True, server_default=text("nextval('trusted_endpoints_id_seq')")),
    Column("org_id", Text, nullable=False),
    Column("entry_type", Text, nullable=False, server_default=text("'endpoint'")),
    Column("normalized_url", Text, nullable=False),
    Column("display_label", Text),
    Column("policy_version", Text, server_default=text("'v1'")),
    Column("created_at", TIMESTAMP(timezone=True), server_default=text("NOW()")),
    Column("revoked_at", TIMESTAMP(timezone=True)),
    Column("created_by", Text),
)
