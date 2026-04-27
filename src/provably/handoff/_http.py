"""HTTP wrapper around the Provably backend API (env + retry)."""

from __future__ import annotations

import os
import time
from typing import Any

import requests

_SESSION = requests.Session()

_TRANSIENT_STATUS = {429, 502, 503, 504}


def base_url() -> str:
    env_url = os.getenv("PROVABLY_RUST_BE_URL", "").strip()
    if not env_url:
        raise ValueError("Missing PROVABLY_RUST_BE_URL")
    return env_url.rstrip("/")


def headers() -> dict[str, str]:
    return {
        "x-api-key": os.getenv("PROVABLY_API_KEY", ""),
        "Content-Type": "application/json",
    }


def org_id() -> str:
    oid = os.getenv("PROVABLY_ORG_ID", "").strip()
    if not oid:
        raise ValueError("Missing PROVABLY_ORG_ID")
    return oid


def log_failed_response(resp: requests.Response) -> None:
    try:
        print(f"[HANDOFF] HTTP {resp.status_code} body: {resp.text[:2000]}")
    except Exception:  # noqa: BLE001
        pass


def get_json(path: str) -> Any:
    resp = _SESSION.get(f"{base_url()}{path}", headers=headers(), timeout=60)
    if not resp.ok:
        log_failed_response(resp)
        resp.raise_for_status()
    return resp.json() if resp.text else {}


def post_json(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = _SESSION.post(
        f"{base_url()}{path}",
        headers=headers(),
        json=payload or {},
        timeout=60,
    )
    if not resp.ok:
        log_failed_response(resp)
        resp.raise_for_status()
    return resp.json() if resp.text else {}


def post_raw(path: str, payload: dict[str, Any]) -> requests.Response:
    """Post without raising so callers can inspect error bodies (e.g. 'already exists')."""
    return _SESSION.post(f"{base_url()}{path}", headers=headers(), json=payload, timeout=60)


def post_json_with_transient_retry(
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    max_attempts: int = 12,
) -> dict[str, Any]:
    """Retry POST on 429/5xx transient statuses; the verifier occasionally returns 503."""
    payload = payload or {}
    last: requests.Response | None = None
    for attempt in range(max_attempts):
        last = _SESSION.post(
            f"{base_url()}{path}",
            headers=headers(),
            json=payload,
            timeout=120,
        )
        if last.status_code in _TRANSIENT_STATUS:
            log_failed_response(last)
            time.sleep(min(3.0 * (attempt + 1), 45))
            continue
        if not last.ok:
            log_failed_response(last)
            last.raise_for_status()
        text = (last.text or "").strip()
        if not text:
            return {}
        try:
            return last.json()
        except ValueError:
            return {}
    assert last is not None
    last.raise_for_status()
    return {}
