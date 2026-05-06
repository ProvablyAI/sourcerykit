"""Trusted-endpoint registry: per-org allowlist used to gate outbound GETs and verify claims."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import psycopg2

if TYPE_CHECKING:
    from provably.handoff.types import HandoffPayload

_DDL_DONE = False

# ---------------------------------------------------------------------------
# Pattern matching
#
# A registered URL may contain FastAPI/Express-style path placeholders so a single
# entry can authorize a family of concrete URLs:
#
#   {name}        — matches one path segment (no '/'). E.g. /customers/{id} matches
#                   /customers/123 but NOT /customers/123/orders.
#   {name:path}   — matches any subtree, including '/' separators. E.g.
#                   /customers/{rest:path} matches both /customers/123 and
#                   /customers/123/orders.
#
# Plain URLs (no '{' character) keep exact-match semantics — no behavior change for
# existing entries.
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{[^}/]+(?::path)?\}")


@lru_cache(maxsize=512)
def _compile_pattern(registered: str) -> re.Pattern[str] | None:
    """Compile a registered URL into a regex if it has placeholders, else return None.

    Cache keeps regex compilation off the hot per-request path.
    """
    if "{" not in registered:
        return None
    parts: list[str] = []
    cursor = 0
    has_placeholder = False
    for match in _PLACEHOLDER_RE.finditer(registered):
        parts.append(re.escape(registered[cursor : match.start()]))
        is_path = ":path" in match.group(0)
        parts.append(".+?" if is_path else "[^/]+?")
        cursor = match.end()
        has_placeholder = True
    if not has_placeholder:
        return None
    parts.append(re.escape(registered[cursor:]))
    try:
        return re.compile(f"^{''.join(parts)}$")
    except re.error:
        return None


def _matches_registered(claim_url: str, registered: str) -> bool:
    """``True`` when ``claim_url`` exactly matches ``registered`` or matches its pattern."""
    if claim_url == registered:
        return True
    pattern = _compile_pattern(registered)
    return pattern is not None and pattern.match(claim_url) is not None


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
    """Return whether ``url`` is currently allowlisted for ``org_id``.

    Two-phase lookup: exact match first (fast path, single indexed query), then a
    pattern-match scan over only the rows containing ``{`` in their ``normalized_url``.
    Plain URLs without placeholders never enter the slow path, so existing exact-match
    registries see no perf regression.
    """
    if not url or not org_id:
        return False
    norm = normalize_url_for_trust(url)
    if not norm:
        return False
    _ensure_trusted_table(conn)
    with conn.cursor() as cur:
        # Fast path: exact match.
        cur.execute(
            """
            SELECT 1 FROM trusted_endpoints
            WHERE org_id = %s AND normalized_url = %s AND entry_type = 'endpoint' AND revoked_at IS NULL
            LIMIT 1
            """,
            (org_id, norm),
        )
        if cur.fetchone() is not None:
            return True
        # Slow path: pattern entries only.
        cur.execute(
            """
            SELECT normalized_url FROM trusted_endpoints
            WHERE org_id = %s AND entry_type = 'endpoint' AND revoked_at IS NULL
              AND normalized_url LIKE '%%{%%'
            """,
            (org_id,),
        )
        for (registered,) in cur.fetchall():
            if _matches_registered(norm, str(registered or "")):
                return True
    return False


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


def load_trusted_endpoint_urls(pg_url: str, org_id: str) -> list[str]:
    """Return active trusted-endpoint URLs for ``org_id``; opens its own connection.

    Convenience wrapper around :func:`list_trusted_endpoints` for callers that just need the
    URL strings (e.g. to embed a registry snapshot in a handoff payload). Returns ``[]`` when
    ``pg_url`` or ``org_id`` is empty.
    """
    if not pg_url or not org_id:
        return []
    conn = psycopg2.connect(pg_url)
    try:
        rows = list_trusted_endpoints(conn, org_id)
    finally:
        conn.close()
    return [url for url in (str(r.get("url") or "").strip() for r in rows) if url]


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
        pattern_entries = [r for r in registry if "{" in r]
        missing: list[str] = []
        for claim_url in claim_urls:
            if claim_url in registry:
                continue
            if any(_matches_registered(claim_url, entry) for entry in pattern_entries):
                continue
            missing.append(claim_url)
        missing = list(dict.fromkeys(missing))
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
