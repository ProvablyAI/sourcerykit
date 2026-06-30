"""Tests for sourcerykit.evaluator._eval_modes."""

import uuid
from typing import Any

import pytest

from sourcerykit.evaluator._eval_modes import (
    _get_by_json_path,
    canonical_json,
    evaluate_claim,
)
from sourcerykit.schemas import HandoffClaim, VerificationMode
from sourcerykit.schemas.agent_response import ClaimedValue

_QID = uuid.uuid4()


# ---------------------------------------------------------------------------
# canonical_json
# ---------------------------------------------------------------------------


class TestCanonicalJson:
    def test_simple_dict_is_sorted(self) -> None:
        result = canonical_json({"b": 2, "a": 1})
        assert result == '{"a":1,"b":2}'

    def test_nested_dict_sorted(self) -> None:
        result = canonical_json({"z": {"y": 1, "x": 2}})
        assert result == '{"z":{"x":2,"y":1}}'

    def test_list_preserved(self) -> None:
        result = canonical_json([3, 1, 2])
        assert result == "[3,1,2]"

    def test_none_value(self) -> None:
        assert canonical_json(None) == "null"

    def test_string_value(self) -> None:
        assert canonical_json("hello") == '"hello"'

    def test_deterministic(self) -> None:
        d = {"c": 3, "a": 1, "b": 2}
        assert canonical_json(d) == canonical_json(d)


# ---------------------------------------------------------------------------
# _get_by_json_path
# ---------------------------------------------------------------------------


class TestGetByJsonPath:
    def test_root_path_returns_whole_object(self) -> None:
        obj = {"a": 1}
        assert _get_by_json_path(obj, "$") == {"a": 1}

    def test_empty_path_returns_whole_object(self) -> None:
        obj = {"a": 1}
        assert _get_by_json_path(obj, "") == {"a": 1}

    def test_dot_path(self) -> None:
        obj = {"response": {"field_x": "value"}}
        assert _get_by_json_path(obj, "$.response.field_x") == "value"

    def test_bare_dot_path_without_root(self) -> None:
        obj = {"user": {"id": 42}}
        assert _get_by_json_path(obj, "user.id") == 42

    def test_bracket_index(self) -> None:
        obj = {"items": [10, 20, 30]}
        assert _get_by_json_path(obj, "$.items[1]") == 20

    def test_nested_list_access(self) -> None:
        obj = {"data": [{"name": "alice"}, {"name": "bob"}]}
        assert _get_by_json_path(obj, "$.data[0].name") == "alice"

    def test_missing_key_raises(self) -> None:
        with pytest.raises((KeyError, TypeError)):
            _get_by_json_path({"a": 1}, "$.b")

    def test_out_of_range_index_raises(self) -> None:
        with pytest.raises((IndexError, TypeError)):
            _get_by_json_path({"items": [1, 2]}, "$.items[5]")


# ---------------------------------------------------------------------------
# evaluate_claim — FIELD_EXTRACTION
# ---------------------------------------------------------------------------


def _fe_claim(**kwargs: Any) -> HandoffClaim:
    """Build a FIELD_EXTRACTION HandoffClaim with sensible defaults."""
    return HandoffClaim(
        action_name=kwargs.get("action_name", "test_action"),
        query_id=_QID,
        verification_mode=VerificationMode.FIELD_EXTRACTION,
        json_path=kwargs.get("json_path", "$"),
        claimed_value=kwargs.get("claimed_value", []),
    )


class TestEvaluateClaimFieldExtraction:
    def test_passes_when_all_claimed_values_match(self) -> None:
        claim = _fe_claim(
            claimed_value=[ClaimedValue(path="$.status", value="open")],
        )
        row = {"status": "open"}
        result = evaluate_claim(claim, row)
        assert result["result"] == "PASS"

    def test_caught_when_value_does_not_match(self) -> None:
        claim = _fe_claim(
            claimed_value=[ClaimedValue(path="$.status", value="open")],
        )
        row = {"status": "closed"}
        result = evaluate_claim(claim, row)
        assert result["result"] == "CAUGHT"

    def test_multiple_values_all_must_match(self) -> None:
        claim = _fe_claim(
            claimed_value=[
                ClaimedValue(path="$.a", value="1"),
                ClaimedValue(path="$.b", value="2"),
            ],
        )
        row = {"a": "1", "b": "2"}
        result = evaluate_claim(claim, row)
        assert result["result"] == "PASS"

    def test_caught_if_one_of_multiple_fails(self) -> None:
        claim = _fe_claim(
            claimed_value=[
                ClaimedValue(path="$.a", value="1"),
                ClaimedValue(path="$.b", value="wrong"),
            ],
        )
        row = {"a": "1", "b": "2"}
        result = evaluate_claim(claim, row)
        assert result["result"] == "CAUGHT"

    def test_numeric_value_coerced_to_string_for_comparison(self) -> None:
        claim = _fe_claim(
            claimed_value=[ClaimedValue(path="$.count", value="42")],
        )
        row = {"count": 42}
        result = evaluate_claim(claim, row)
        assert result["result"] == "PASS"

    def test_bad_json_path_raises_key_error(self) -> None:
        """Per-entry path errors in FIELD_EXTRACTION propagate as KeyError."""
        claim = _fe_claim(
            claimed_value=[ClaimedValue(path="$.missing.deep.key", value="x")],
        )
        with pytest.raises(KeyError):
            evaluate_claim(claim, {"other": "value"})

    def test_base_contains_action_name(self) -> None:
        claim = _fe_claim(action_name="my_action")
        result = evaluate_claim(claim, {})
        assert result["action_name"] == "my_action"

    def test_base_contains_verification_mode(self) -> None:
        claim = _fe_claim()
        result = evaluate_claim(claim, {})
        assert result["verification_mode"] == VerificationMode.FIELD_EXTRACTION


# ---------------------------------------------------------------------------
# evaluate_claim — RANGE_THRESHOLD
# ---------------------------------------------------------------------------


def _rt_claim(**kwargs: Any) -> HandoffClaim:
    return HandoffClaim(
        action_name="range_action",
        query_id=_QID,
        verification_mode=VerificationMode.RANGE_THRESHOLD,
        json_path=kwargs.get("json_path", "$.value"),
        claimed_value=kwargs.get("claimed_value", 50),
        range_min=kwargs.get("range_min", None),
        range_max=kwargs.get("range_max", None),
    )


class TestEvaluateClaimRangeThreshold:
    def test_passes_when_value_within_bounds(self) -> None:
        claim = _rt_claim(claimed_value=50, range_min=0, range_max=100)
        result = evaluate_claim(claim, {"value": 50})
        assert result["result"] == "PASS"

    def test_caught_below_range_min(self) -> None:
        claim = _rt_claim(claimed_value=5, range_min=10, range_max=100)
        result = evaluate_claim(claim, {"value": 5})
        assert result["result"] == "CAUGHT"

    def test_caught_above_range_max(self) -> None:
        claim = _rt_claim(claimed_value=150, range_min=0, range_max=100)
        result = evaluate_claim(claim, {"value": 150})
        assert result["result"] == "CAUGHT"

    def test_boundary_min_passes(self) -> None:
        claim = _rt_claim(claimed_value=10, range_min=10, range_max=100)
        result = evaluate_claim(claim, {"value": 10})
        assert result["result"] == "PASS"

    def test_boundary_max_passes(self) -> None:
        claim = _rt_claim(claimed_value=100, range_min=0, range_max=100)
        result = evaluate_claim(claim, {"value": 100})
        assert result["result"] == "PASS"

    def test_caught_when_no_bounds_provided(self) -> None:
        claim = _rt_claim(claimed_value=50)
        result = evaluate_claim(claim, {"value": 50})
        assert result["result"] == "CAUGHT"
        assert "range_min" in result.get("detail", "")

    def test_caught_when_indexed_value_not_numeric(self) -> None:
        claim = _rt_claim(claimed_value=50, range_min=0, range_max=100)
        result = evaluate_claim(claim, {"value": "not_a_number"})
        assert result["result"] == "CAUGHT"

    def test_list_average_used_when_indexed_is_list(self) -> None:
        # Average of [10, 20, 30] = 20; claimed 20; bounds [0, 100]
        claim = _rt_claim(claimed_value=20.0, range_min=0, range_max=100)
        result = evaluate_claim(claim, {"value": [10, 20, 30]})
        assert result["result"] == "PASS"

    def test_caught_when_claimed_value_does_not_match_indexed(self) -> None:
        claim = _rt_claim(claimed_value=99, range_min=0, range_max=100)
        result = evaluate_claim(claim, {"value": 50})
        assert result["result"] == "CAUGHT"
