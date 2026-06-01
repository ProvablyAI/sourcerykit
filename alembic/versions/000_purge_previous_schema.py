"""Drop old provably tables.

Revision ID: 000
Revises:
Create Date: 2026-05-13 18:43:24.189215
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "000"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS trusted_endpoints CASCADE;")
    op.execute("DROP TABLE IF EXISTS provably_intercepts CASCADE;")


def downgrade() -> None:
    pass
