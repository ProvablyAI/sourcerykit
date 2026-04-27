"""HTTP wrapper around the Provably backend API (env + retry)."""

from __future__ import annotations

import os
import re
import time
from typing import Any
from urllib.parse import urlparse, urlunparse

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


_PROVABLY_CLOUD_HOST_SUFFIX = ".provably.ai"


def _infer_app_ui_base_from_rust_api_url(rust_url: str) -> str:
    """Map ``api[-*].*.provably.ai`` → ``app[-*].*.provably.ai`` when ``PROVABLY_APP_UI_URL`` is unset.

    Keeps demos working without a second env var as long as ``PROVABLY_RUST_BE_URL`` targets
    Provably SaaS (e.g. ``https://api-dev.provably.ai`` → ``https://app-dev.provably.ai``).
    Unknown / non-Provably hosts → ``""`` (caller uses API fallback).
    """
    raw = (rust_url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    scheme = (parsed.scheme or "https").strip() or "https"
    host = (parsed.hostname or "").lower()
    if not host.endswith(_PROVABLY_CLOUD_HOST_SUFFIX) and host != "provably.ai":
        return ""
    first, *rest = host.split(".")
    if first.startswith("api-"):
        first = "app-" + first[4:]
    elif first == "api":
        first = "app"
    elif re.match(r"^api\d+", first):  # e.g. api0 edge case
        first = "app" + first[3:]
    else:
        return ""
    new_host = ".".join([first, *rest])
    rebuilt = urlunparse((scheme, new_host, "", "", "", ""))
    return rebuilt.rstrip("/")


def _resolved_app_ui_base() -> str:
    explicit = os.getenv("PROVABLY_APP_UI_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    inferred = _infer_app_ui_base_from_rust_api_url(os.getenv("PROVABLY_RUST_BE_URL", "").strip())
    return inferred.rstrip("/") if inferred else ""


def query_record_page_url(org_id: str, query_record_id: str) -> str:
    """Human-facing Provably app URL for a query record (admin / dashboard deep-link).

    Pattern: ``{PROVABLY_APP_UI_URL}/org/{org_id}/query-record/{query_record_id}`` (e.g.
    ``https://app-dev.provably.ai/org/.../query-record/...``).

    Resolution order:

    #. ``PROVABLY_APP_UI_URL`` when set.

    #. Else, if ``PROVABLY_RUST_BE_URL`` is a Provably SaaS API host (``*.provably.ai``),
       infer ``app-…`` from ``api-…`` (see :func:`_infer_app_ui_base_from_rust_api_url`).

    #. Else fallback to the JSON API record URL under ``PROVABLY_RUST_BE_URL`` for tests and custom deployments.
    """
    oid = (org_id or "").strip()
    qid = (query_record_id or "").strip()
    app = _resolved_app_ui_base()
    if app and oid and qid:
        return f"{app}/org/{oid}/query-record/{qid}"
    return f"{base_url()}/api/v1/organizations/{oid}/queries/{qid}"


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


def get_json_params(path: str, params: dict[str, Any], *, timeout_s: float = 60.0) -> Any:
    """GET with query-string parameters (e.g. list queries filtered by ``collection_ids``)."""
    resp = _SESSION.get(
        f"{base_url()}{path}", headers=headers(), params=params, timeout=timeout_s
    )
    if not resp.ok:
        log_failed_response(resp)
        resp.raise_for_status()
    if not resp.text:
        return []
    data = resp.json()
    return data


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
    """Retry POST on 429/5xx transient statuses; the eval service occasionally returns 503."""
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
