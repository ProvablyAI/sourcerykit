"""Add reasoning column to traces table.

Revision ID: 005
Revises: 004
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "005"
down_revision: str | Sequence[str] | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE traces
        ADD COLUMN IF NOT EXISTS reasoning TEXT NOT NULL DEFAULT ''
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE traces
        DROP COLUMN IF EXISTS reasoning
    """)
