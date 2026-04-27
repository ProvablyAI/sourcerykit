"""DDL + INSERT for the ``provably_intercepts`` table."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import psycopg2

from provably.log import get_logger
from provably.trusted_endpoints import ensure_trusted_endpoints_table, is_trusted_endpoint

_log = get_logger(__name__)
_DDL_DONE = False

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS provably_intercepts (
  id SERIAL PRIMARY KEY,
  agent_id TEXT NOT NULL,
  action_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  request_payload TEXT NOT NULL DEFAULT '{}',
  raw_response TEXT NOT NULL,
  response_hash TEXT NOT NULL,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT timezone('utc', now())
);
"""

# Brings legacy ``raw_response jsonb`` / ``created_at timestamptz`` columns up to current schema.
_MIGRATE_LEGACY_TYPES_SQL = """
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'provably_intercepts'
      AND column_name = 'raw_response'
      AND udt_name = 'jsonb'
  ) THEN
    ALTER TABLE provably_intercepts
      ALTER COLUMN raw_response TYPE TEXT USING raw_response::text;
  END IF;
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'provably_intercepts'
      AND column_name = 'created_at'
      AND udt_name = 'timestamptz'
  ) THEN
    ALTER TABLE provably_intercepts
      ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE
      USING (created_at AT TIME ZONE 'UTC');
  END IF;
END $$;
"""

_HAS_REQUEST_PAYLOAD_SQL = """
SELECT 1 FROM information_schema.columns
WHERE table_schema = current_schema()
  AND table_name = 'provably_intercepts'
  AND column_name = 'request_payload'
"""

_ADD_REQUEST_PAYLOAD_SQL = """
ALTER TABLE provably_intercepts
  ADD COLUMN request_payload TEXT NOT NULL DEFAULT '{}'
"""

_INSERT_SQL = """
INSERT INTO provably_intercepts
  (agent_id, action_name, source_url, request_payload, raw_response, response_hash)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING id
"""


def hash_payload(raw: Any) -> str:
    return hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()


def request_payload_dict(url: str, method: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"url": url, "method": method}
    for k in ("params", "json", "data"):
        if k in kwargs and kwargs[k] is not None:
            out[k] = kwargs[k]
    return out


def ensure_intercepts_table(conn: psycopg2.extensions.connection) -> None:
    global _DDL_DONE
    if _DDL_DONE:
        return
    with conn.cursor() as cur:
        cur.execute(_CREATE_TABLE_SQL)
        cur.execute(_MIGRATE_LEGACY_TYPES_SQL)
        cur.execute(_HAS_REQUEST_PAYLOAD_SQL)
        if cur.fetchone() is None:
            cur.execute(_ADD_REQUEST_PAYLOAD_SQL)
    conn.commit()
    _DDL_DONE = True


def insert_intercept_row(
    *,
    url: str,
    method: str,
    request_payload: dict[str, Any],
    raw: Any,
    agent_id: str,
    action_name: str,
) -> int | None:
    """Insert a row and return its id; enforce trust on GET before storing."""
    postgres_url = os.getenv("POSTGRES_URL", "").strip()
    if not postgres_url:
        return None
    if method.upper() == "GET":
        _require_trusted_endpoint(postgres_url, url)
    return _write_row(postgres_url, url, method, request_payload, raw, agent_id, action_name)


def _require_trusted_endpoint(postgres_url: str, url: str) -> None:
    org_id = os.environ.get("PROVABLY_ORG_ID", "").strip()
    if not org_id:
        raise ValueError("Missing PROVABLY_ORG_ID — required for trusted_endpoints check on GET")
    conn = psycopg2.connect(postgres_url)
    try:
        ensure_trusted_endpoints_table(conn)
        if not is_trusted_endpoint(url, org_id, conn):
            raise RuntimeError(f"BLOCKED: endpoint {url} not in trusted index for org {org_id}")
    finally:
        conn.close()


def _write_row(
    postgres_url: str,
    url: str,
    method: str,
    request_payload: dict[str, Any],
    raw: Any,
    agent_id: str,
    action_name: str,
) -> int | None:
    conn = psycopg2.connect(postgres_url)
    try:
        ensure_intercepts_table(conn)
        row_id: int | None = None
        with conn.cursor() as cur:
            cur.execute(
                _INSERT_SQL,
                (
                    agent_id,
                    action_name,
                    url,
                    json.dumps(request_payload, sort_keys=True),
                    json.dumps(raw) if not isinstance(raw, str) else raw,
                    hash_payload(raw),
                ),
            )
            row = cur.fetchone()
            if row:
                row_id = int(row[0])
        conn.commit()
        _log.info("intercept_stored", agent_id=agent_id, action_name=action_name, url=url, method=method)
        return row_id
    finally:
        conn.close()
