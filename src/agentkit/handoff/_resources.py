"""Small helpers for reading Provably resource payloads."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

INTERCEPTS_TABLE = "provably_intercepts"

DEFAULT_INTERCEPT_COLUMNS: list[dict[str, Any]] = [
    {"name": "agent_id"},
    {"name": "action_name"},
    {"name": "source_url"},
    {"name": "request_payload"},
    {"name": "raw_response"},
    {"name": "response_hash"},
    {"name": "created_at"},
]


def provably_database_host_field(postgres_url: str) -> str:
    parsed = urlparse(postgres_url)
    host = parsed.hostname or ""
    if not host:
        raise ValueError("POSTGRES_URL must include a host")
    if parsed.port and parsed.port != 5432:
        return f"{host}:{parsed.port}"
    return host


def extract_id(data: dict[str, Any], fallback_keys: list[str]) -> str:
    for key in fallback_keys:
        value = data.get(key)
        if value is None:
            continue
        s = str(value).strip()
        if s:
            return s
    raise ValueError(f"Could not extract id from keys {fallback_keys}: {data}")


def find_first_id(obj: Any, keys: tuple[str, ...] = ("id", "database_id")) -> str:
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        for v in obj.values():
            found = find_first_id(v, keys)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_first_id(item, keys)
            if found:
                return found
    return ""


def find_named_table(obj: Any, name: str) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        node_name = (obj.get("name") or obj.get("table_name") or "").lower()
        if node_name == name.lower():
            return obj
        for v in obj.values():
            r = find_named_table(v, name)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for item in obj:
            r = find_named_table(item, name)
            if r is not None:
                return r
    return None


def extract_items(payload: Any, *, plural_key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        maybe = payload.get(plural_key)
        if isinstance(maybe, list):
            return [x for x in maybe if isinstance(x, dict)]
        return [payload]
    return []
