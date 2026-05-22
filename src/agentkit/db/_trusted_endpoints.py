"""SQLAlchemy Core DML statements for the ``trusted_endpoints`` table."""

import uuid

from sqlalchemy import and_, exists, literal, select
from sqlalchemy.dialects.postgresql import insert

from agentkit.db._schema import trusted_endpoints

_ACTIVE = and_(
    trusted_endpoints.c.entry_type == "endpoint",
    trusted_endpoints.c.revoked_at.is_(None),
)


def select_trusted_endpoint_prefix(org_id: uuid.UUID, incoming_url: str):
    """Fast-path existence check: scalar result is a boolean.

    Equivalent raw SQL::

        SELECT EXISTS (
            SELECT 1 FROM trusted_endpoints
            WHERE org_id = :org_id
              AND :incoming_url LIKE (normalized_url || '%')
              AND entry_type = 'endpoint'
              AND revoked_at IS NULL
        )
    """
    return select(
        exists().where(
            and_(
                trusted_endpoints.c.org_id == org_id,
                # Checks if the incoming_url starts with the stored normalized_url
                literal(incoming_url).like(trusted_endpoints.c.normalized_url + "%"),
                _ACTIVE,
            )
        )
    )


def select_active_trusted_endpoints(org_id: uuid.UUID):
    """Return a SELECT for all active endpoints for ``org_id``, most-recent first.

    Equivalent raw SQL::

        SELECT normalized_url, display_label
        FROM trusted_endpoints
        WHERE org_id = :org_id
          AND entry_type = 'endpoint'
          AND revoked_at IS NULL
        ORDER BY created_at DESC, id DESC
    """
    return (
        select(
            trusted_endpoints.c.normalized_url,
            trusted_endpoints.c.display_label,
            trusted_endpoints.c.policy_version,
            trusted_endpoints.c.created_by,
        )
        .where(
            and_(
                trusted_endpoints.c.org_id == org_id,
                _ACTIVE,
            )
        )
        .order_by(trusted_endpoints.c.created_at.desc(), trusted_endpoints.c.id.desc())
    )


def insert_trusted_endpoint(org_id: uuid.UUID, normalized_url: str, display_label: str | None = None):
    """Insert a new active endpoint, ignoring conflicts with an existing non-revoked row.

    Equivalent raw SQL::

        INSERT INTO trusted_endpoints (org_id, normalized_url, display_label, entry_type)
        VALUES (:org_id, :normalized_url, :display_label, 'endpoint')
        ON CONFLICT (org_id, normalized_url) WHERE revoked_at IS NULL DO NOTHING
    """
    return (
        insert(trusted_endpoints)
        .values(
            org_id=org_id,
            normalized_url=normalized_url,
            display_label=display_label,
            entry_type="endpoint",
        )
        .on_conflict_do_nothing(
            index_elements=[trusted_endpoints.c.org_id, trusted_endpoints.c.normalized_url],
            index_where=trusted_endpoints.c.revoked_at.is_(None),
        )
    )
