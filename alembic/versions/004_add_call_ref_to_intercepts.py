"""Add call_ref column to intercepts table.

Revision ID: 004
Revises: 003
Create Date: 2026-07-07
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "004"
down_revision: str | Sequence[str] | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE intercepts
        ADD COLUMN IF NOT EXISTS call_ref UUID
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE intercepts
        DROP COLUMN IF EXISTS call_ref
    """)
