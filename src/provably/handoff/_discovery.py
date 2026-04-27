"""Discovery and resolution of Provably middleware / database / table / collection ids."""

from __future__ import annotations

from typing import Any

from provably.handoff._http import get_json
from provably.handoff._resources import (
    DEFAULT_INTERCEPT_COLUMNS,
    INTERCEPTS_TABLE,
    extract_id,
    extract_items,
    find_first_id,
    find_named_table,
)


def discover_intercepts_table(org_id: str, middleware_id: str, database_id: str) -> dict[str, Any]:
    """Find exact schema/table/columns for ``provably_intercepts`` under the chosen DB."""
    found = _walk_schemas_for_intercepts(org_id, middleware_id, database_id)
    if found:
        return found
    data = get_json(f"/api/v1/organizations/{org_id}/data")
    node = find_named_table(data, INTERCEPTS_TABLE)
    if node is None:
        raise RuntimeError("Could not find provably_intercepts in middleware/database resources")
    return _node_to_bundle(node)


def resolve_existing_database_id(org_id: str, middleware_id: str, db_name: str) -> str:
    for path in (
        f"/api/v1/organizations/{org_id}/middlewares/{middleware_id}/databases",
        f"/api/v1/organizations/{org_id}/databases",
    ):
        try:
            payload = get_json(path)
        except Exception:  # noqa: BLE001
            continue
        for item in extract_items(payload, plural_key="databases"):
            name = str(item.get("name") or "").strip().lower()
            if name == db_name.strip().lower() or not name:
                try:
                    db_id = extract_id(item, ["id", "database_id"])
                except ValueError:
                    continue
                if db_id:
                    return db_id
    try:
        data = get_json(f"/api/v1/organizations/{org_id}/data")
        return find_first_id(data, ("database_id",))
    except Exception:  # noqa: BLE001
        return ""


def resolve_existing_collection_id(org_id: str, middleware_id: str, database_id: str, table_id: str) -> str:
    try:
        payload = get_json(f"/api/v1/organizations/{org_id}/collections")
    except Exception:  # noqa: BLE001
        return ""
    for item in extract_items(payload, plural_key="collections"):
        if str(item.get("name") or "").strip().lower() != INTERCEPTS_TABLE:
            continue
        if not _collection_matches(item, middleware_id, database_id, table_id):
            continue
        try:
            return extract_id(item, ["id", "collection_id"])
        except ValueError:
            continue
    return ""


def resolve_intercepts_collection_uuid(org_id: str, collection_id: str, table_id: str) -> str:
    """Prefer a GET /collections row whose table is ``provably_intercepts``; fall back to cached id."""
    try:
        payload = get_json(f"/api/v1/organizations/{org_id}/collections")
    except Exception:  # noqa: BLE001
        return collection_id
    for item in extract_items(payload, plural_key="collections"):
        tid = str(item.get("table_id") or item.get("tableId") or "").strip()
        name = str(item.get("name") or (item.get("table") or {}).get("name") or "").strip().lower()
        if name != INTERCEPTS_TABLE and str(item.get("id") or "") != collection_id:
            continue
        if table_id and tid and tid != table_id:
            continue
        uid = str(item.get("id") or item.get("collection_id") or "").strip()
        if uid:
            return uid
    return collection_id


def _walk_schemas_for_intercepts(org_id: str, middleware_id: str, database_id: str) -> dict[str, Any] | None:
    base = f"/api/v1/organizations/{org_id}/middlewares/{middleware_id}/databases/{database_id}"
    try:
        schemas = extract_items(get_json(f"{base}/schemas"), plural_key="schemas")
    except Exception:  # noqa: BLE001
        return None
    for schema in schemas:
        schema_id = str(schema.get("id") or schema.get("schema_id") or "").strip()
        if not schema_id:
            continue
        tables = extract_items(get_json(f"{base}/schemas/{schema_id}/tables"), plural_key="tables")
        for table in tables:
            if str(table.get("name") or "").strip().lower() != INTERCEPTS_TABLE:
                continue
            table_id = str(table.get("id") or table.get("table_id") or "").strip()
            if not table_id:
                continue
            columns = extract_items(
                get_json(f"{base}/schemas/{schema_id}/tables/{table_id}/columns"),
                plural_key="columns",
            )
            return {
                "schema_id": schema_id,
                "table_id": table_id,
                "enabled_columns": _columns_to_bundle(columns) or DEFAULT_INTERCEPT_COLUMNS,
            }
    return None


def _columns_to_bundle(columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enabled: list[dict[str, Any]] = []
    for col in columns:
        col_id = str(col.get("id") or col.get("column_id") or "").strip()
        col_name = str(col.get("name") or "").strip()
        if col_id:
            enabled.append({"id": col_id})
        elif col_name:
            enabled.append({"name": col_name})
    return enabled


def _node_to_bundle(node: dict[str, Any]) -> dict[str, Any]:
    schema_id = str(node.get("schema_id") or node.get("schemaId") or "")
    table_id = str(node.get("id") or node.get("table_id") or node.get("tableId") or "")
    if not table_id:
        table_id = extract_id(node, ["id", "table_id"])
    cols = node.get("enabled_columns") or node.get("columns") or []
    if isinstance(cols, list) and cols and isinstance(cols[0], str):
        enabled_columns = [{"name": c} for c in cols]
    elif isinstance(cols, list):
        enabled_columns = cols
    else:
        enabled_columns = DEFAULT_INTERCEPT_COLUMNS
    return {"schema_id": schema_id, "table_id": table_id, "enabled_columns": enabled_columns}


def _collection_matches(item: dict[str, Any], middleware_id: str, database_id: str, table_id: str) -> bool:
    item_mw = str(item.get("middleware_id") or item.get("middlewareId") or "").strip()
    item_db = str(item.get("database_id") or item.get("databaseId") or "").strip()
    item_table = str(item.get("table_id") or item.get("tableId") or "").strip()
    if table_id and item_table and item_table != table_id:
        return False
    if item_mw and middleware_id and item_mw != middleware_id:
        return False
    if item_db and database_id and item_db != database_id:
        return False
    return True
