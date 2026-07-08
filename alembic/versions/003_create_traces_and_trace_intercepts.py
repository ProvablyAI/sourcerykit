"""Create traces and trace_intercepts tables.

Revision ID: 003
Revises: 002
Create Date: 2026-06-26 12:13:24.189215
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | Sequence[str] | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS traces (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task       TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS trace_intercepts (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            trace_id         UUID NOT NULL REFERENCES traces(id),
            intercept_id     UUID NOT NULL REFERENCES intercepts(id),
            query_id         UUID NOT NULL,
            verification_mode VARCHAR(50) NOT NULL,
            claimed_value    TEXT,
            outcome          VARCHAR(20),
            details          TEXT,
            created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_trace_intercepts_trace_id
        ON trace_intercepts (trace_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_trace_intercepts_query_id
        ON trace_intercepts (query_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_trace_intercepts_query_id")
    op.execute("DROP INDEX IF EXISTS ix_trace_intercepts_trace_id")
    op.execute("DROP TABLE IF EXISTS trace_intercepts")
    op.execute("DROP TABLE IF EXISTS traces")
