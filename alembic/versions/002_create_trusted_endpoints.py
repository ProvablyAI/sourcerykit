"""Create trusted_endpoints table.

Revision ID: 002
Revises: 001
Create Date: 2026-05-13 18:43:24.189215
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | Sequence[str] | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS trusted_endpoints (
            id             SERIAL PRIMARY KEY,
            org_id         TEXT NOT NULL,
            entry_type     TEXT NOT NULL DEFAULT 'endpoint',
            normalized_url TEXT NOT NULL,
            display_label  TEXT,
            policy_version TEXT DEFAULT 'v1',
            created_at     TIMESTAMPTZ DEFAULT NOW(),
            revoked_at     TIMESTAMPTZ,
            created_by     TEXT
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS trusted_endpoints")
