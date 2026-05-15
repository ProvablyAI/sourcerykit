"""SQLAlchemy Core DML statements for the ``trusted_endpoints`` table."""

from sqlalchemy import and_, exists, func, select

from agentkit.db.schema import trusted_endpoints

_ACTIVE = and_(
    trusted_endpoints.c.entry_type == "endpoint",
    trusted_endpoints.c.revoked_at.is_(None),
)


def select_trusted_endpoint_exact(org_id: str, normalized_url: str):
    """Fast-path existence check: scalar result is a boolean.

    Equivalent raw SQL::

        SELECT EXISTS (
          SELECT 1 FROM trusted_endpoints
          WHERE org_id = :org_id
            AND normalized_url = :normalized_url
            AND entry_type = 'endpoint'
            AND revoked_at IS NULL
        )
    """
    return select(
        exists().where(
            and_(
                trusted_endpoints.c.org_id == org_id,
                trusted_endpoints.c.normalized_url == normalized_url,
                _ACTIVE,
            )
        )
    )


def select_trusted_endpoint_patterns(org_id: str):
    """Slow-path lookup: return a SELECT for all active pattern entries (those containing ``{``).

    Equivalent raw SQL::

        SELECT normalized_url FROM trusted_endpoints
        WHERE org_id = :org_id
          AND entry_type = 'endpoint'
          AND revoked_at IS NULL
          AND normalized_url LIKE '%{%'
    """
    return select(trusted_endpoints.c.normalized_url).where(
        and_(
            trusted_endpoints.c.org_id == org_id,
            _ACTIVE,
            trusted_endpoints.c.normalized_url.like("%{%"),
        )
    )


def select_active_trusted_endpoints(org_id: str):
    """Return a SELECT for all active endpoints for ``org_id``, most-recent first.

    Equivalent raw SQL::

        SELECT normalized_url, COALESCE(display_label, normalized_url)
        FROM trusted_endpoints
        WHERE org_id = :org_id
          AND entry_type = 'endpoint'
          AND revoked_at IS NULL
        ORDER BY created_at DESC, id DESC
    """
    return (
        select(
            trusted_endpoints.c.normalized_url,
            func.coalesce(
                trusted_endpoints.c.display_label,
                trusted_endpoints.c.normalized_url,
            ).label("display_label"),
        )
        .where(
            and_(
                trusted_endpoints.c.org_id == org_id,
                _ACTIVE,
            )
        )
        .order_by(trusted_endpoints.c.created_at.desc(), trusted_endpoints.c.id.desc())
    )
