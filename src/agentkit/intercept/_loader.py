"""Read helpers for the ``provably_intercepts`` table."""

from __future__ import annotations

import json
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

_SELECT_LATEST_INTERCEPT_SQL = """
SELECT raw_response, request_payload FROM provably_intercepts
WHERE agent_id = %s AND action_name = %s
ORDER BY created_at DESC
LIMIT 1
"""


def load_latest_intercept_payload(
    pg_url: str,
    action_name: str,
    *,
    agent_id: str,
) -> tuple[dict[str, Any], Any]:
    """Return ``(request_payload, response_payload)`` for the most recent matching row.

    Both payloads are JSON-decoded when stored as strings; missing rows or empty ``pg_url``
    return ``({}, None)``.
    """
    if not pg_url:
        return {}, None
    conn = psycopg2.connect(pg_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(_SELECT_LATEST_INTERCEPT_SQL, (agent_id, action_name))
            row = cur.fetchone()
            if not row:
                return {}, None
            return (
                _parse_request_payload(row.get("request_payload")),
                _parse_json_maybe(row["raw_response"]),
            )
    finally:
        conn.close()


def _parse_json_maybe(raw: Any) -> Any:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def _parse_request_payload(raw_payload: Any) -> dict[str, Any]:
    if isinstance(raw_payload, str):
        try:
            return json.loads(raw_payload) if raw_payload else {}
        except json.JSONDecodeError:
            return {}
    if isinstance(raw_payload, dict):
        return raw_payload
    return {}
