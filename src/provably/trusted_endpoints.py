"""Trusted-endpoint registry: per-org allowlist used to gate outbound GETs and verify claims."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

import psycopg2

if TYPE_CHECKING:
    from provably.handoff.types import HandoffPayload

_DDL_DONE = False


def normalize_url_for_trust(url: str) -> str:
    """Return the canonical form of ``url`` used for trust look-ups.

    Lowercases scheme and host, drops the default port for http/https, and strips a single
    trailing slash from the path so equivalent URLs collapse to the same key. Empty / whitespace
    input returns an empty string.
    """
    raw = (url or "").strip()
    if not raw:
        return ""
    p = urlparse(raw)
    scheme = (p.scheme or "https").lower()
    host = (p.hostname or "").lower()
    if not host:
        return raw.lower()
    port = p.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    else:
        netloc = host
    path = (p.path or "").rstrip("/")
    return f"{scheme}://{netloc}{path}"


def _ensure_trusted_table(conn: psycopg2.extensions.connection) -> None:
    global _DDL_DONE
    if _DDL_DONE:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trusted_endpoints (
              id SERIAL PRIMARY KEY,
              org_id TEXT NOT NULL,
              entry_type TEXT NOT NULL DEFAULT 'endpoint',
              normalized_url TEXT NOT NULL,
              display_label TEXT,
              policy_version TEXT DEFAULT 'v1',
              created_at TIMESTAMPTZ DEFAULT NOW(),
              revoked_at TIMESTAMPTZ,
              created_by TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS trusted_endpoints_org_url
            ON trusted_endpoints(org_id, normalized_url)
            WHERE revoked_at IS NULL;
            """
        )
    conn.commit()
    _DDL_DONE = True


def ensure_trusted_endpoints_table(conn: psycopg2.extensions.connection) -> None:
    """Create the ``trusted_endpoints`` table and uniqueness index if absent (idempotent, commits)."""
    _ensure_trusted_table(conn)


def is_trusted_endpoint(url: str, org_id: str, conn: psycopg2.extensions.connection) -> bool:
    """Return whether ``url`` is currently allowlisted for ``org_id``; normalizes URL before look-up."""
    if not url or not org_id:
        return False
    norm = normalize_url_for_trust(url)
    if not norm:
        return False
    _ensure_trusted_table(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM trusted_endpoints
            WHERE org_id = %s AND normalized_url = %s AND entry_type = 'endpoint' AND revoked_at IS NULL
            LIMIT 1
            """,
            (org_id, norm),
        )
        return cur.fetchone() is not None


def list_trusted_endpoints(
    conn: psycopg2.extensions.connection,
    org_id: str,
    *,
    excluded_urls: set[str] | None = None,
    metadata_seeds: list[dict] | None = None,
) -> list[dict[str, str]]:
    """Return active trusted endpoints for ``org_id`` ordered most-recent-first.

    Each result row is a flat ``dict`` with stable keys (``url``, ``label``, ``category``,
    ``risk_level``, ``description``, ``expected_response``) so it can be serialized straight to
    a UI without further wrangling. Revoked rows are filtered out by the underlying query.

    Args:
        conn: Live psycopg2 connection (will not be closed).
        org_id: Provably org id to scope the query to. Empty returns ``[]``.
        excluded_urls: Normalized URLs the caller wants hidden — typically internal services
            auto-allowed by the deployment that should not appear in the user-facing list.
        metadata_seeds: Optional list of seed dicts (``url``, ``category``, ``risk_level``,
            ``description``, ``expected_response``) used to enrich rows when the seed's
            normalized URL matches a registry row.
    """
    if not org_id:
        return []
    _ensure_trusted_table(conn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT normalized_url, COALESCE(display_label, normalized_url)
            FROM trusted_endpoints
            WHERE org_id = %s AND entry_type = 'endpoint' AND revoked_at IS NULL
            ORDER BY created_at DESC, id DESC
            """,
            (org_id,),
        )
        rows = cur.fetchall()
    blocked = excluded_urls or set()
    metadata_by_url: dict[str, dict] = {}
    if metadata_seeds:
        metadata_by_url = {
            normalize_url_for_trust(str(seed.get("url", ""))): seed for seed in metadata_seeds
        }
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for normalized_url, display_label in rows:
        url = str(normalized_url or "").strip()
        if not url or url in blocked or url in seen:
            continue
        seen.add(url)
        seed = metadata_by_url.get(url, {})
        result.append(
            {
                "url": url,
                "label": str(display_label or url),
                "category": str(seed.get("category", "custom")),
                "risk_level": str(seed.get("risk_level", "unknown")),
                "description": str(seed.get("description", "")),
                "expected_response": str(seed.get("expected_response", "")),
            }
        )
    return result


def check_claim_endpoints_are_trusted(
    hp: HandoffPayload,
    *,
    postgres_url: str,
    org_id_fallback: str = "",
) -> None:
    """Verify every claim's source URL is in the trusted registry; raise on violation.

    Performs two checks: (1) every claim URL must appear in the immutable
    ``hp.trusted_endpoint_registry`` snapshot embedded in the handoff (catches tampering after
    the snapshot was built); (2) every claim URL must still be a non-revoked row in the live DB
    for the relevant org (catches use of stale endpoints). Opens and closes its own psycopg2
    connection.

    Args:
        hp: Handoff payload whose claims and snapshot are being audited.
        postgres_url: DSN for the live registry DB. Required.
        org_id_fallback: Used when ``hp.provably_org_id`` is empty.

    Raises:
        ValueError: A claim references a URL not in the snapshot, not in the live DB, or
            ``provably_org_id`` is missing.
        RuntimeError: ``postgres_url`` was not provided.
    """
    claim_urls: list[str] = []
    for claim in hp.claims:
        req = claim.request_payload if isinstance(claim.request_payload, dict) else {}
        if n := normalize_url_for_trust(str(req.get("url") or "").strip()):
            claim_urls.append(n)

    if not claim_urls:
        return

    registry = {n for url in hp.trusted_endpoint_registry if (n := normalize_url_for_trust(str(url)))}
    if registry:
        missing = list(dict.fromkeys(u for u in claim_urls if u not in registry))
        if missing:
            raise ValueError(f"handoff has endpoints missing from trusted snapshot: {', '.join(missing)}")

    org_id = (hp.provably_org_id or "").strip() or org_id_fallback
    if not postgres_url:
        raise RuntimeError("postgres_url is required for trusted endpoint check")
    if not org_id:
        raise ValueError("provably_org_id missing in handoff payload")

    conn = psycopg2.connect(postgres_url)
    try:
        untrusted = list(dict.fromkeys(u for u in claim_urls if not is_trusted_endpoint(u, org_id, conn)))
    finally:
        conn.close()

    if untrusted:
        raise ValueError(f"handoff has untrusted endpoints: {', '.join(untrusted)}")
