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
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id             UUID NOT NULL,
            entry_type         VARCHAR(50) NOT NULL DEFAULT 'endpoint',
            normalized_url     TEXT NOT NULL,
            display_label      VARCHAR(255),
            policy_version     VARCHAR(20) DEFAULT 'v1',
            created_at         TIMESTAMP DEFAULT NOW(),
            revoked_at         TIMESTAMP,
            created_by         VARCHAR(255)
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uix_trusted_endpoints_org_url_active
        ON trusted_endpoints (org_id, normalized_url)
        WHERE revoked_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS trusted_endpoints")
