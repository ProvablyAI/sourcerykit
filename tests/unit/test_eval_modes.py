from __future__ import annotations

import pytest

from provably.handoff.eval_modes import _get_by_json_path, _normalize_json_path, evaluate_claim
from provably.handoff.types import HandoffClaim


def test_normalize_jsonpath_prefix() -> None:
    assert _normalize_json_path("") == ""
    assert _normalize_json_path("$") == ""
    assert _normalize_json_path("$.userId") == "userId"
    assert _normalize_json_path("$.a.b") == "a.b"
    assert _normalize_json_path("userId") == "userId"
    assert _normalize_json_path("response.field") == "response.field"


def test_get_by_path_jsonpath() -> None:
    obj = {"userId": 1, "nested": {"x": 2}}
    assert _get_by_json_path(obj, "$.userId") == 1
    assert _get_by_json_path(obj, "userId") == 1
    assert _get_by_json_path(obj, "$.nested.x") == 2
    assert _get_by_json_path(obj, "$") == obj


# ---------------------------------------------------------------------------
# Array indexing in json_path (#23): both bracket form and numeric fallback.
# ---------------------------------------------------------------------------


def test_normalize_jsonpath_lifts_brackets_into_segments() -> None:
    assert _normalize_json_path("items[0].subject") == "items.[0].subject"
    assert _normalize_json_path("items[0][1]") == "items.[0].[1]"
    assert _normalize_json_path("[0].status") == "[0].status"
    assert _normalize_json_path("$.items[2].quantity") == "items.[2].quantity"


def test_get_by_path_bracket_indexing_at_root() -> None:
    assert _get_by_json_path([{"status": "open"}], "[0].status") == "open"
    assert _get_by_json_path([10, 20, 30], "[1]") == 20


def test_get_by_path_bracket_indexing_inside_dict() -> None:
    obj = {"items": [{"a": 1}, {"a": 2}, {"a": 3}]}
    assert _get_by_json_path(obj, "items[0].a") == 1
    assert _get_by_json_path(obj, "items[2].a") == 3
    assert _get_by_json_path(obj, "$.items[1].a") == 2


def test_get_by_path_numeric_segment_fallback_for_lists() -> None:
    """``items.0.a`` works when cursor is a list — easier shape for naive LLMs."""
    obj = {"items": [{"a": 1}, {"a": 2}]}
    assert _get_by_json_path(obj, "items.0.a") == 1
    assert _get_by_json_path(obj, "items.1.a") == 2


def test_get_by_path_nested_lists() -> None:
    """Bracket form chains: list of lists of dicts."""
    obj = {"matrix": [[{"v": "a"}, {"v": "b"}], [{"v": "c"}]]}
    assert _get_by_json_path(obj, "matrix[0][1].v") == "b"
    assert _get_by_json_path(obj, "matrix[1][0].v") == "c"


def test_get_by_path_index_out_of_range_raises_indexerror() -> None:
    with pytest.raises(IndexError, match="out of range"):
        _get_by_json_path([{"a": 1}], "[5].a")
    with pytest.raises(IndexError, match="out of range"):
        _get_by_json_path({"items": [1, 2]}, "items[5]")


def test_get_by_path_dict_segment_against_list_still_raises_keyerror() -> None:
    """If the path expects a dict-like step but cursor is a list (and the segment isn't
    numeric or bracket form), we still raise — old error class preserved."""
    with pytest.raises(KeyError):
        _get_by_json_path({"a": [1, 2]}, "a.b")


def test_get_by_path_existing_dict_paths_still_work() -> None:
    """Regression: nothing about pure-dict walks should change."""
    assert _get_by_json_path({"plan": "Enterprise"}, "plan") == "Enterprise"
    assert _get_by_json_path({"a": {"b": 1}}, "a.b") == 1


def test_field_extraction_pass_with_array_index() -> None:
    """End-to-end via the real evaluator: list-shaped indexed value, claim against ``[0].status``."""
    claim = HandoffClaim(
        action_name="list_open_tickets",
        claimed_value="open",
        query_record_id="q1",
        verification_mode="field_extraction",
        json_path="[0].status",
    )
    indexed = [{"status": "open", "id": 42}, {"status": "closed", "id": 41}]
    v = evaluate_claim(claim, indexed)
    assert v["result"] == "PASS", v


def test_field_extraction_error_when_index_out_of_range() -> None:
    claim = HandoffClaim(
        action_name="list_open_tickets",
        claimed_value="open",
        query_record_id="q1",
        verification_mode="field_extraction",
        json_path="[7].status",
    )
    v = evaluate_claim(claim, [{"status": "open"}])
    assert v["result"] == "ERROR"
    assert "out of range" in v["detail"]


def test_schema_type_passes_with_dollar_path() -> None:
    """Regression: LLM emits JSONPath ``$.userId``; we must not index ``['$']``."""
    claim = HandoffClaim(
        action_name="endpoint_0",
        claimed_value="ignored in schema",
        query_record_id="q1",
        verification_mode="schema_type",
        json_path="$.userId",
        expected_json_schema={"type": "integer"},
    )
    indexed = {"userId": 1, "id": 1, "title": "t", "completed": False}
    v = evaluate_claim(claim, indexed)
    assert v["result"] == "PASS"
    assert v["json_path"] == "$.userId"
    assert v["indexed_at_path"] == "1"


def test_schema_type_missing_path_is_error() -> None:
    claim = HandoffClaim(
        action_name="endpoint_0",
        claimed_value=None,
        query_record_id="q1",
        verification_mode="schema_type",
        json_path="$.also",
        expected_json_schema={"type": "boolean"},
    )
    v = evaluate_claim(claim, {"id": 1})
    assert v["result"] == "ERROR"
