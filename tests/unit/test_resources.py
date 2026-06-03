from __future__ import annotations

import pytest

from provably.handoff._resources import (
    DEFAULT_INTERCEPT_COLUMNS,
    extract_id,
    extract_items,
    find_first_id,
    find_named_table,
    provably_database_host_field,
)


class TestProvablyDatabaseHostField:
    def test_returns_bare_host_for_default_port(self) -> None:
        url = "postgresql://user:pw@db.internal:5432/app"
        assert provably_database_host_field(url) == "db.internal"

    def test_returns_bare_host_when_no_port(self) -> None:
        url = "postgresql://user:pw@db.internal/app"
        assert provably_database_host_field(url) == "db.internal"

    def test_appends_non_default_port(self) -> None:
        url = "postgresql://user:pw@db.internal:6543/app"
        assert provably_database_host_field(url) == "db.internal:6543"

    def test_raises_when_host_missing(self) -> None:
        with pytest.raises(ValueError, match="must include a host"):
            provably_database_host_field("postgresql:///app")


class TestExtractId:
    def test_returns_first_present_non_blank_key(self) -> None:
        data = {"id": "  ", "database_id": "db-1"}
        assert extract_id(data, ["id", "database_id"]) == "db-1"

    def test_coerces_non_string_values(self) -> None:
        assert extract_id({"id": 42}, ["id"]) == "42"

    def test_raises_when_no_key_yields_value(self) -> None:
        with pytest.raises(ValueError, match="Could not extract id"):
            extract_id({"id": None, "other": ""}, ["id", "missing"])


class TestFindFirstId:
    def test_finds_top_level_key(self) -> None:
        assert find_first_id({"id": "x"}) == "x"

    def test_prefers_key_order(self) -> None:
        assert find_first_id({"database_id": "d", "id": "i"}) == "i"

    def test_recurses_into_nested_dicts_and_lists(self) -> None:
        obj = {"outer": [{"noise": 1}, {"inner": {"database_id": "deep"}}]}
        assert find_first_id(obj, ("database_id",)) == "deep"

    def test_returns_empty_string_when_absent(self) -> None:
        assert find_first_id({"a": {"b": 1}}, ("id",)) == ""

    def test_ignores_blank_values_and_continues(self) -> None:
        assert find_first_id({"id": "   ", "child": {"id": "real"}}) == "real"


class TestFindNamedTable:
    def test_matches_on_name_case_insensitively(self) -> None:
        node = {"name": "Provably_Intercepts", "table_id": "t1"}
        assert find_named_table(node, "provably_intercepts") is node

    def test_matches_on_table_name_key(self) -> None:
        node = {"table_name": "provably_intercepts"}
        assert find_named_table({"wrap": [node]}, "provably_intercepts") is node

    def test_returns_none_when_absent(self) -> None:
        assert find_named_table({"name": "other"}, "provably_intercepts") is None


class TestExtractItems:
    def test_filters_non_dicts_from_list_payload(self) -> None:
        payload = [{"a": 1}, "skip", {"b": 2}]
        assert extract_items(payload, plural_key="databases") == [{"a": 1}, {"b": 2}]

    def test_reads_plural_key_from_dict(self) -> None:
        payload = {"databases": [{"id": "1"}, 5, {"id": "2"}]}
        assert extract_items(payload, plural_key="databases") == [{"id": "1"}, {"id": "2"}]

    def test_wraps_bare_dict_when_no_plural_key(self) -> None:
        payload = {"id": "solo"}
        assert extract_items(payload, plural_key="databases") == [{"id": "solo"}]

    def test_returns_empty_for_scalar(self) -> None:
        assert extract_items("nope", plural_key="databases") == []


def test_default_intercept_columns_shape() -> None:
    names = {c["name"] for c in DEFAULT_INTERCEPT_COLUMNS}
    assert {"agent_id", "action_name", "source_url", "response_hash"} <= names
