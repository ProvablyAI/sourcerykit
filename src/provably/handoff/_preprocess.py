"""Provably preprocess: ≥2-row padding on ``provably_intercepts`` + preprocess polling + proof wait."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

import psycopg2

from provably.handoff._http import get_json, post_json
from provably.log import get_logger

_log = get_logger(__name__)

_preprocess_after_insert_lock = threading.Lock()

_PAD_AGENT = "__provably_preprocess_pad"
_PAD_ACTION = "__dummy_row"
_PAD_URL = "https://internal.invalid/provably-preprocess-padding"
_PAD_PAYLOAD: dict[str, Any] = {"_provably_preprocess_padding": True}

_CREATE_INTERCEPTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS provably_intercepts (
  id SERIAL PRIMARY KEY,
  agent_id TEXT NOT NULL,
  action_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  request_payload TEXT NOT NULL DEFAULT '{}',
  raw_response TEXT NOT NULL,
  response_hash TEXT NOT NULL,
  created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT timezone('utc', now())
)
"""
_COUNT_INTERCEPTS_SQL = "SELECT COUNT(*) FROM provably_intercepts"
_INSERT_PADDING_SQL = """
INSERT INTO provably_intercepts
  (agent_id, action_name, source_url, request_payload, raw_response, response_hash)
VALUES (%s, %s, %s, %s, %s, %s)
"""


def ensure_preprocess_intercept_padding(postgres_url: str) -> None:
    """Insert dummy intercept rows so the table has ≥2 rows.

    Provably preprocess can fail with only one row ("g1 setup" / key not found in storage);
    padding uses reserved agent/action names that proof SQL never selects.
    """
    if not postgres_url.strip():
        return
    conn = psycopg2.connect(postgres_url)
    try:
        with conn.cursor() as cur:
            cur.execute(_CREATE_INTERCEPTS_TABLE_SQL)
            cur.execute(_COUNT_INTERCEPTS_SQL)
            row = cur.fetchone()
            row_count = int(row[0]) if row and row[0] is not None else 0
            payload_json = json.dumps(_PAD_PAYLOAD)
            payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()
            while row_count < 2:
                cur.execute(_INSERT_PADDING_SQL, (_PAD_AGENT, _PAD_ACTION, _PAD_URL, "{}", payload_json, payload_hash))
                row_count += 1
        conn.commit()
    finally:
        conn.close()


def preprocess_after_intercept_write() -> None:
    """Run full-table preprocess after a new intercept row (serialized across threads).

    No-op when bootstrap has not finished (no cached middleware / integration key).
    """
    from provably.handoff._bootstrap import cache, runtime_ready

    if not runtime_ready():
        return
    c = cache()
    with _preprocess_after_insert_lock:
        run_preprocess(str(c["org_id"]), str(c["middleware_id"]), str(c["table_id"]))


def run_preprocess(org_id: str, middleware_id: str, table_id: str) -> None:
    """Kick preprocess for the intercepts table and poll until it completes."""
    path = f"/api/v1/organizations/{org_id}/middlewares/{middleware_id}/tables/{table_id}/preprocess"
    _log.info("preprocess_started")
    post_json(path, {})
    retried_force = False
    while True:
        status = _preprocess_status(get_json(path))
        if status == "completed":
            _log.info("preprocess_completed")
            return
        if status in {"failed", "error"}:
            if retried_force:
                raise RuntimeError(f"Preprocess failed (status={status})")
            _log.warning("preprocess_error_retrying_with_force")
            post_json(path, {"force": True})
            retried_force = True
            continue
        time.sleep(2)


def wait_for_proof_completed(org_id: str, query_id: str, timeout_s: float = 180.0) -> None:
    """Poll the query record until the proof is ``completed`` (or raise on failure/timeout)."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        rec = get_json(f"/api/v1/organizations/{org_id}/queries/{query_id}")
        proof = rec.get("proof") if isinstance(rec, dict) else None
        if isinstance(proof, dict):
            status = str(proof.get("status") or "").lower()
            if status == "completed":
                return
            if status == "failed":
                raise RuntimeError(f"Proof generation failed: {proof}")
        time.sleep(1.5)
    raise TimeoutError(f"Proof still not Completed for query {query_id} after {timeout_s}s")


def _preprocess_status(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("status") or "").lower()
