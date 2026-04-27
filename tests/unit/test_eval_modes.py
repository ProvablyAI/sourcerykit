from __future__ import annotations

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


def test_schema_type_missing_path_is_caught() -> None:
    claim = HandoffClaim(
        action_name="endpoint_0",
        claimed_value=None,
        query_record_id="q1",
        verification_mode="schema_type",
        json_path="$.also",
        expected_json_schema={"type": "boolean"},
    )
    v = evaluate_claim(claim, {"id": 1})
    assert v["result"] == "CAUGHT"
