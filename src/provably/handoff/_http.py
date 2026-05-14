"""HTTP wrapper around the Provably backend API (env + retry)."""

from __future__ import annotations

import os
import re
import time
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests

from provably.log import get_logger

_log = get_logger(__name__)
_SESSION = requests.Session()
_TRANSIENT_STATUS = {429, 502, 503, 504}


def _request(method: str, path: str, **kwargs: Any) -> requests.Response:
    """All outbound HTTP from this module funnels through here.

    Wraps every call in ``provably_self_egress()`` so the SDK's own backend traffic
    bypasses the trust gate and the intercept recorder. The ``provably_self_egress``
    import is deferred to avoid the circular import:
    ``provably.intercept`` → ``interceptor`` → ``_storage`` → ``handoff._preprocess``
    → ``handoff._http``.
    """
    from provably.intercept._self_egress import provably_self_egress  # noqa: PLC0415

    with provably_self_egress():
        return _SESSION.request(method, f"{base_url()}{path}", headers=headers(), **kwargs)


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
    """Derive the parallel **Provably Data Admin** origin from an **API** URL (hostname only).

    The query-record UI is always served from the **app** tier (e.g.
    ``https://app-dev.provably.ai``), never from the Rust JSON API base. Given a URL whose
    hostname uses the usual ``api-…`` labels on ``*.provably.ai``, returns the matching
    ``app-…`` origin (``https://api-dev.provably.ai`` → ``https://app-dev.provably.ai``).

    Rewrites the *first* matching DNS label left-to-right (e.g.
    ``https://eu.api-dev.provably.ai`` → ``https://eu.app-dev.provably.ai``).

    If the hostname does not match an API → app pattern, returns ``""``.
    """
    raw = (rust_url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    scheme = (parsed.scheme or "https").strip() or "https"
    host = (parsed.hostname or "").lower()
    if not host.endswith(_PROVABLY_CLOUD_HOST_SUFFIX) and host != "provably.ai":
        return ""
    labels = host.split(".")
    for i, seg in enumerate(labels):
        replacement: str | None = None
        if seg.startswith("api-"):
            replacement = "app-" + seg[4:]
        elif seg == "api":
            replacement = "app"
        elif re.fullmatch(r"api\d+", seg):
            replacement = "app" + seg[3:]
        if replacement is None:
            continue
        new_host = ".".join([*labels[:i], replacement, *labels[i + 1 :]])
        rebuilt = urlunparse((scheme, new_host, "", "", "", ""))
        return rebuilt.rstrip("/")

    return ""


def _resolved_app_ui_base() -> str:
    """Base URL of the **Admin / app** UI (query-record pages), never the Rust JSON API origin.

    Prefer ``PROVABLY_APP_UI_URL`` (the admin origin, e.g. ``https://app-dev.provably.ai`` in dev cloud).
    If that value mistakenly points at an ``api-…`` host, it is normalized to the app host.
    When unset, the app host is inferred from ``PROVABLY_RUST_BE_URL`` **only** via
    :func:`_infer_app_ui_base_from_rust_api_url` (api-dev → app-dev). The API base is never
    used as the prefix for human-facing query-record links.
    """
    explicit = os.getenv("PROVABLY_APP_UI_URL", "").strip().rstrip("/")
    if explicit:
        as_app = _infer_app_ui_base_from_rust_api_url(explicit)
        return as_app if as_app else explicit
    inferred = _infer_app_ui_base_from_rust_api_url(os.getenv("PROVABLY_RUST_BE_URL", "").strip())
    return inferred.rstrip("/") if inferred else ""


def query_record_page_url(org_id: str, query_record_id: str) -> str:
    """Human-facing **Provably Data Admin** URL for a query record (never the Rust API origin).

    Pattern: ``{admin_app_origin}/org/{org_id}/query-record/{query_record_id}``, e.g.
    ``https://app-dev.provably.ai/org/…/query-record/…`` (see Provably Data Admin).

    Resolution:

    #. ``PROVABLY_APP_UI_URL`` when set (canonical app origin; optional normalization if it points at ``api-…``).

    #. Else derive app admin host from ``PROVABLY_RUST_BE_URL`` hostname only
       (see :func:`_infer_app_ui_base_from_rust_api_url`)—never use the API base as the page URL.

    #. Else fallback to the JSON API record URL under ``PROVABLY_RUST_BE_URL`` (tests / non-cloud only).
    """
    oid = (org_id or "").strip()
    qid = (query_record_id or "").strip()
    app = _resolved_app_ui_base()
    if app and oid and qid:
        return f"{app}/org/{oid}/query-record/{qid}"
    return f"{base_url()}/api/v1/organizations/{oid}/queries/{qid}"


def log_failed_response(resp: requests.Response) -> None:
    try:
        _log.warning("http_error", status=resp.status_code, body=resp.text[:2000])
    except Exception:  # noqa: BLE001
        pass


def get_json(path: str) -> Any:
    resp = _request("GET", path, timeout=60)
    if not resp.ok:
        log_failed_response(resp)
        resp.raise_for_status()
    return resp.json() if resp.text else {}


def get_json_params(path: str, params: dict[str, Any], *, timeout_s: float = 60.0) -> Any:
    """GET with query-string parameters (e.g. list queries filtered by ``collection_ids``)."""
    resp = _request("GET", path, params=params, timeout=timeout_s)
    if not resp.ok:
        log_failed_response(resp)
        resp.raise_for_status()
    return resp.json() if resp.text else []


def post_json(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = _request("POST", path, json=payload or {}, timeout=60)
    if not resp.ok:
        log_failed_response(resp)
        resp.raise_for_status()
    return resp.json() if resp.text else {}


def post_raw(path: str, payload: dict[str, Any]) -> requests.Response:
    """Post without raising so callers can inspect error bodies (e.g. 'already exists')."""
    return _request("POST", path, json=payload, timeout=60)


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
        last = _request("POST", path, json=payload, timeout=120)
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
            parsed = last.json()
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    assert last is not None
    last.raise_for_status()
    return {}
