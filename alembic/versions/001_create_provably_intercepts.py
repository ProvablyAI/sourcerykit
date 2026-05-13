"""Create provably_intercepts table.

Revision ID: 001
Revises:
Create Date: 2026-05-13 18:43:24.189215
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS provably_intercepts (
            id          SERIAL PRIMARY KEY,
            agent_id    TEXT NOT NULL,
            action_name TEXT NOT NULL,
            source_url  TEXT NOT NULL,
            request_payload TEXT NOT NULL DEFAULT '{}',
            raw_response    TEXT NOT NULL,
            response_hash   TEXT NOT NULL,
            created_at  TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT timezone('utc', now())
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS provably_intercepts")
