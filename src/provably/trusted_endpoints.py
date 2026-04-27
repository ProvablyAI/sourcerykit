from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

import psycopg2

if TYPE_CHECKING:
    from provably.handoff.types import HandoffPayload

_DDL_DONE = False


def normalize_url_for_trust(url: str) -> str:
    """Canonical form: lowercase scheme + host, strip trailing slash on path (empty path → '')."""
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
    """Create trusted_endpoints + index if missing (idempotent)."""
    _ensure_trusted_table(conn)


def is_trusted_endpoint(url: str, org_id: str, conn: psycopg2.extensions.connection) -> bool:
    """Return True if normalized URL exists as a non-revoked endpoint row for org."""
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
    """Return trusted endpoints for ``org_id``.

    ``excluded_urls`` is a set of normalized URLs the caller wants hidden
    (typically internal service URLs auto-allowed by the caller's deployment).
    ``metadata_seeds`` enriches rows with category/risk/description when a seed's
    URL matches.
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
    """Raise ValueError / RuntimeError if any claim endpoint is outside the trusted registry.

    Checks ``hp.trusted_endpoint_registry`` (payload snapshot) first, then verifies against
    the live DB. Raises ``ValueError`` for policy violations and ``RuntimeError`` for
    missing configuration.
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
