from __future__ import annotations

from typing import Any

import pytest

from provably.handoff import _discovery
from provably.handoff._discovery import (
    discover_intercepts_table,
    resolve_existing_collection_id,
    resolve_existing_database_id,
    resolve_intercepts_collection_uuid,
)

ORG = "org-1"
MW = "mw-1"
DB = "db-1"
SCHEMAS_BASE = f"/api/v1/organizations/{ORG}/middlewares/{MW}/databases/{DB}"


def install_router(monkeypatch: pytest.MonkeyPatch, routes: dict[str, Any]) -> list[str]:
    """Patch _discovery.get_json with a path->payload router; missing paths raise."""
    seen: list[str] = []

    def fake_get_json(path: str) -> Any:
        seen.append(path)
        if path not in routes:
            raise RuntimeError(f"unexpected GET {path}")
        value = routes[path]
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(_discovery, "get_json", fake_get_json)
    return seen


class TestDiscoverInterceptsTable:
    def test_walk_schemas_happy_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"{SCHEMAS_BASE}/schemas": {"schemas": [{"id": "sch-1"}]},
            f"{SCHEMAS_BASE}/schemas/sch-1/tables": {
                "tables": [{"name": "provably_intercepts", "id": "tbl-1"}]
            },
            f"{SCHEMAS_BASE}/schemas/sch-1/tables/tbl-1/columns": {
                "columns": [{"id": "col-1", "name": "agent_id"}, {"name": "source_url"}]
            },
        }
        install_router(monkeypatch, routes)

        bundle = discover_intercepts_table(ORG, MW, DB)

        assert bundle["schema_id"] == "sch-1"
        assert bundle["table_id"] == "tbl-1"
        # column with id -> {"id": ...}; column with only name -> {"name": ...}
        assert {"id": "col-1"} in bundle["enabled_columns"]
        assert {"name": "source_url"} in bundle["enabled_columns"]

    def test_walk_schemas_falls_back_to_default_columns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"{SCHEMAS_BASE}/schemas": {"schemas": [{"id": "sch-1"}]},
            f"{SCHEMAS_BASE}/schemas/sch-1/tables": {
                "tables": [{"name": "provably_intercepts", "table_id": "tbl-1"}]
            },
            f"{SCHEMAS_BASE}/schemas/sch-1/tables/tbl-1/columns": {"columns": []},
        }
        install_router(monkeypatch, routes)

        bundle = discover_intercepts_table(ORG, MW, DB)

        assert bundle["enabled_columns"] == _discovery.DEFAULT_INTERCEPT_COLUMNS

    def test_falls_back_to_org_data_when_schema_walk_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"{SCHEMAS_BASE}/schemas": {"schemas": []},
            f"/api/v1/organizations/{ORG}/data": {
                "tables": [
                    {"name": "other"},
                    {"name": "provably_intercepts", "id": "tbl-9", "schema_id": "sch-9", "columns": ["agent_id"]},
                ]
            },
        }
        install_router(monkeypatch, routes)

        bundle = discover_intercepts_table(ORG, MW, DB)

        assert bundle["table_id"] == "tbl-9"
        assert bundle["schema_id"] == "sch-9"
        assert bundle["enabled_columns"] == [{"name": "agent_id"}]

    def test_raises_when_table_not_found_anywhere(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"{SCHEMAS_BASE}/schemas": RuntimeError("boom"),
            f"/api/v1/organizations/{ORG}/data": {"tables": [{"name": "unrelated"}]},
        }
        install_router(monkeypatch, routes)

        with pytest.raises(RuntimeError, match="Could not find provably_intercepts"):
            discover_intercepts_table(ORG, MW, DB)


class TestResolveExistingDatabaseId:
    def test_matches_by_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"/api/v1/organizations/{ORG}/middlewares/{MW}/databases": {
                "databases": [{"name": "app", "id": "db-app"}]
            },
        }
        install_router(monkeypatch, routes)
        assert resolve_existing_database_id(ORG, MW, "app") == "db-app"

    def test_falls_back_to_org_data_first_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"/api/v1/organizations/{ORG}/middlewares/{MW}/databases": RuntimeError("x"),
            f"/api/v1/organizations/{ORG}/databases": RuntimeError("y"),
            f"/api/v1/organizations/{ORG}/data": {"nested": {"database_id": "db-deep"}},
        }
        install_router(monkeypatch, routes)
        assert resolve_existing_database_id(ORG, MW, "app") == "db-deep"

    def test_returns_empty_when_everything_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"/api/v1/organizations/{ORG}/middlewares/{MW}/databases": RuntimeError("x"),
            f"/api/v1/organizations/{ORG}/databases": RuntimeError("y"),
            f"/api/v1/organizations/{ORG}/data": RuntimeError("z"),
        }
        install_router(monkeypatch, routes)
        assert resolve_existing_database_id(ORG, MW, "app") == ""


class TestResolveExistingCollectionId:
    def test_matches_collection_for_intercepts_table(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"/api/v1/organizations/{ORG}/collections": {
                "collections": [
                    {"name": "other", "id": "c-x"},
                    {
                        "name": "provably_intercepts",
                        "id": "c-1",
                        "middleware_id": MW,
                        "database_id": DB,
                        "table_id": "tbl-1",
                    },
                ]
            },
        }
        install_router(monkeypatch, routes)
        assert resolve_existing_collection_id(ORG, MW, DB, "tbl-1") == "c-1"

    def test_skips_when_table_id_mismatches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"/api/v1/organizations/{ORG}/collections": {
                "collections": [
                    {"name": "provably_intercepts", "id": "c-1", "table_id": "other-tbl"}
                ]
            },
        }
        install_router(monkeypatch, routes)
        assert resolve_existing_collection_id(ORG, MW, DB, "tbl-1") == ""

    def test_returns_empty_on_http_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {f"/api/v1/organizations/{ORG}/collections": RuntimeError("down")}
        install_router(monkeypatch, routes)
        assert resolve_existing_collection_id(ORG, MW, DB, "tbl-1") == ""


class TestResolveInterceptsCollectionUuid:
    def test_prefers_matching_collection_row(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"/api/v1/organizations/{ORG}/collections": {
                "collections": [{"name": "provably_intercepts", "id": "uuid-1", "table_id": "tbl-1"}]
            },
        }
        install_router(monkeypatch, routes)
        assert resolve_intercepts_collection_uuid(ORG, "cached", "tbl-1") == "uuid-1"

    def test_falls_back_to_cached_id_on_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {f"/api/v1/organizations/{ORG}/collections": RuntimeError("down")}
        install_router(monkeypatch, routes)
        assert resolve_intercepts_collection_uuid(ORG, "cached", "tbl-1") == "cached"

    def test_falls_back_to_cached_id_when_no_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        routes = {
            f"/api/v1/organizations/{ORG}/collections": {
                "collections": [{"name": "unrelated", "id": "other", "table_id": "zzz"}]
            },
        }
        install_router(monkeypatch, routes)
        assert resolve_intercepts_collection_uuid(ORG, "cached", "tbl-1") == "cached"
