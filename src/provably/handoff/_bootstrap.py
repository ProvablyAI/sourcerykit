"""One-time Provably bootstrap: middleware + database + collection + integration caching."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from provably.handoff._discovery import (
    discover_intercepts_table,
    resolve_existing_collection_id,
    resolve_existing_database_id,
    resolve_intercepts_collection_uuid,
)
from provably.handoff._http import get_json, log_failed_response, org_id, post_json, post_raw
from provably.handoff._resources import extract_id, provably_database_host_field

_CACHE: dict[str, str] = {}


def cache() -> dict[str, str]:
    """Return the live process-wide bootstrap cache."""
    return _CACHE


def runtime_ready() -> bool:
    """Return whether :func:`initialize_runtime` has populated middleware id and integration key."""
    return bool(_CACHE.get("middleware_id") and _CACHE.get("integration_api_key"))


def cached_integration_api_key() -> str:
    """Return the cached integration API key, or ``""`` if bootstrap has not run yet."""
    return str(_CACHE.get("integration_api_key") or "")


def ensure_bootstrap_cached() -> None:
    if _CACHE.get("middleware_id"):
        return

    current_org = org_id()
    postgres_url = os.getenv("POSTGRES_URL", "").strip()
    if not postgres_url:
        raise ValueError("Missing POSTGRES_URL")

    print("[HANDOFF] Bootstrapping Provably...")
    middleware_id = _create_middleware(current_org)
    database_id = _onboard_database(current_org, middleware_id, postgres_url)
    table_bundle = discover_intercepts_table(current_org, middleware_id, database_id)
    collection_id = _ensure_collection(current_org, middleware_id, database_id, table_bundle)

    _CACHE.update(
        {
            "org_id": current_org,
            "middleware_id": middleware_id,
            "database_id": database_id,
            "collection_id": collection_id,
            "table_id": table_bundle["table_id"],
        }
    )
    _ensure_integration_cached()


def _create_middleware(current_org: str) -> str:
    mw = post_json(f"/api/v1/organizations/{current_org}/middlewares/provably", {})
    middleware_id = extract_id(mw, ["id", "middleware_id"])
    print(f"[HANDOFF] Middleware created: {middleware_id}")
    return middleware_id


def _onboard_database(current_org: str, middleware_id: str, postgres_url: str) -> str:
    parsed = urlparse(postgres_url)
    db_name = parsed.path.lstrip("/") or "postgres"
    body: dict[str, Any] = {
        "name": db_name,
        "username": parsed.username or "postgres",
        "password": parsed.password or "",
        "provider": "postgresql",
        "uri": provably_database_host_field(postgres_url),
    }
    resp = post_raw(f"/api/v1/organizations/{current_org}/middlewares/{middleware_id}/databases", body)
    if resp.ok:
        data = resp.json() if resp.text else {}
        database_id = extract_id(data if isinstance(data, dict) else {}, ["id", "database_id"])
    elif resp.status_code == 400 and _already_exists(resp.text):
        print("[HANDOFF] Database already exists; attempting to reuse existing registration...")
        database_id = resolve_existing_database_id(current_org, middleware_id, db_name)
        if not database_id:
            log_failed_response(resp)
            raise RuntimeError("Database exists but could not resolve existing database_id")
    else:
        log_failed_response(resp)
        resp.raise_for_status()
        database_id = ""
    print(f"[HANDOFF] Database onboarded: {database_id}")
    return database_id


def _already_exists(body: str) -> bool:
    text = (body or "").lower()
    return "already exists" in text and "database" in text


def _ensure_collection(
    current_org: str,
    middleware_id: str,
    database_id: str,
    table_bundle: dict[str, Any],
) -> str:
    table_id = table_bundle["table_id"]
    existing = resolve_existing_collection_id(current_org, middleware_id, database_id, table_id)
    if existing:
        print(f"[HANDOFF] Reusing existing collection: {existing}")
        return existing
    payload: dict[str, Any] = {
        "name": "provably_intercepts",
        "publicity_status": "private",
        "middleware_id": middleware_id,
        "database_id": database_id,
        "is_descriptions_generated": False,
        "entities": [],
        "integrations": [],
        "query_price": 0,
        "is_general_sql_queries_enabled": True,
        "schema_id": table_bundle["schema_id"],
        "table_id": table_id,
        "enabled_columns": table_bundle["enabled_columns"],
    }
    resp = post_raw(f"/api/v1/organizations/{current_org}/collections", payload)
    if resp.status_code >= 400:
        log_failed_response(resp)
        resp.raise_for_status()
    coll = resp.json() if resp.text else {}
    collection_id = extract_id(coll if isinstance(coll, dict) else {}, ["id", "collection_id"])
    print(f"[HANDOFF] Collection created: {collection_id}")
    return collection_id


def _ensure_integration_cached() -> None:
    if _CACHE.get("integration_api_key"):
        return
    current_org = _CACHE["org_id"]
    collection_uuid = resolve_intercepts_collection_uuid(
        current_org,
        _CACHE["collection_id"],
        _CACHE["table_id"],
    )
    body: dict[str, Any] = {
        "name": f"langraph-handoff-{current_org[:12]}",
        "type": "agent",
        "role": "developer",
        "collections": [collection_uuid],
        "is_enabled": True,
    }
    try:
        resp = post_json(f"/api/v1/organizations/{current_org}/integrations", body)
    except Exception as exc:  # noqa: BLE001
        print(f"[HANDOFF] Integration create failed ({exc}); attempting to reuse existing integrations...")
        if _reuse_any_existing_integration(current_org):
            return
        raise
    _CACHE["integration_id"] = extract_id(resp, ["id", "integration_id"])
    _CACHE["integration_api_key"] = str(resp.get("api_key") or "")


def _reuse_any_existing_integration(current_org: str) -> bool:
    try:
        raw = get_json(f"/api/v1/organizations/{current_org}/integrations")
    except Exception:  # noqa: BLE001
        return False
    items = raw if isinstance(raw, list) else raw.get("integrations") if isinstance(raw, dict) else []
    if not isinstance(items, list):
        return False
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("api_key") or "").strip()
        if not key:
            continue
        _CACHE["integration_id"] = extract_id(item, ["id", "integration_id"])
        _CACHE["integration_api_key"] = key
        print("[HANDOFF] Reusing existing integration from API list")
        return True
    return False
