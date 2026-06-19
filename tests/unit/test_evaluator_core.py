"""Tests for sourcerykit.evaluator.evaluator."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from sourcerykit.evaluator.evaluator import (
    _coerce_query_result_to_indexed_value,
    _extract_timings,
    _resolve_outcome,
    evaluate_handoff,
)
from sourcerykit.schemas import HandoffClaim, HandoffPayload, Outcome, VerificationMode
from sourcerykit.schemas.agent_response import ClaimedValue

_ORG = uuid.uuid4()
_QID = uuid.uuid4()


def _make_payload(claims: list[HandoffClaim] | None = None) -> HandoffPayload:
    return HandoffPayload(
        provably_org_id=_ORG,
        integration_api_key="test-key",
        claims=claims or [],
    )


def _make_claim(query_id: uuid.UUID = _QID) -> HandoffClaim:
    return HandoffClaim(
        action_name="test_action",
        query_id=query_id,
        verification_mode=VerificationMode.FIELD_EXTRACTION,
        claimed_value=[ClaimedValue(path="$.status", value="ok")],
        request_payload={"url": "https://api.example.com"},
    )


# ---------------------------------------------------------------------------
# _resolve_outcome
# ---------------------------------------------------------------------------


class TestResolveOutcome:
    def test_pass_when_all_pass(self) -> None:
        per_claim = [{"result": "PASS"}, {"result": "PASS"}]
        assert _resolve_outcome(per_claim, []) == Outcome.PASS

    def test_caught_when_any_caught(self) -> None:
        per_claim = [{"result": "PASS"}, {"result": "CAUGHT"}]
        assert _resolve_outcome(per_claim, []) == Outcome.CAUGHT

    def test_error_when_errors_list_non_empty(self) -> None:
        per_claim = [{"result": "PASS"}]
        assert _resolve_outcome(per_claim, ["something went wrong"]) == Outcome.ERROR

    def test_error_when_claim_has_error_result(self) -> None:
        per_claim = [{"result": "ERROR"}]
        assert _resolve_outcome(per_claim, []) == Outcome.ERROR

    def test_pass_when_no_claims_and_no_errors(self) -> None:
        assert _resolve_outcome([], []) == Outcome.PASS


# ---------------------------------------------------------------------------
# _coerce_query_result_to_indexed_value
# ---------------------------------------------------------------------------


class TestCoerceQueryResultToIndexedValue:
    def test_tabular_data_is_flattened(self) -> None:
        value = {
            "type": "resultset",
            "value": {
                "columns": [{"name": "raw_response"}],
                "rows": [['{"status": "ok"}']],
            },
        }
        result = _coerce_query_result_to_indexed_value(value)
        assert result == {"status": "ok"}

    def test_aggregate_answer_flattened(self) -> None:
        value = {"type": "aggregate", "value": "42"}
        result = _coerce_query_result_to_indexed_value(value)
        assert result == "42"

    def test_plain_dict_returned_as_is(self) -> None:
        value = {"foo": "bar"}
        result = _coerce_query_result_to_indexed_value(value)
        assert result == {"foo": "bar"}

    def test_none_returned_as_none(self) -> None:
        result = _coerce_query_result_to_indexed_value(None)
        assert result is None


# ---------------------------------------------------------------------------
# _extract_timings
# ---------------------------------------------------------------------------


class TestExtractTimings:
    def test_extracts_proof_and_verify_times(self) -> None:
        record = {"proof": {"execution_time_ms": 100.0, "verification_time_ms": 50.0}}
        timings = _extract_timings(record)
        assert timings["proof_time_ms"] == 100.0
        assert timings["verify_time_ms"] == 50.0

    def test_defaults_to_zero_when_missing(self) -> None:
        timings = _extract_timings({})
        assert timings["proof_time_ms"] == 0.0
        assert timings["verify_time_ms"] == 0.0

    def test_handles_none_record(self) -> None:
        timings = _extract_timings(None)  # type: ignore[arg-type]
        assert timings["proof_time_ms"] == 0.0
        assert timings["verify_time_ms"] == 0.0


# ---------------------------------------------------------------------------
# evaluate_handoff
# ---------------------------------------------------------------------------


class TestEvaluateHandoff:
    async def test_returns_pass_when_all_verifications_succeed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        claim = _make_claim()
        payload = _make_payload([claim])

        verify_result = {
            "result": {
                "type": "resultset",
                "value": {
                    "columns": [{"name": "raw_response"}],
                    "rows": [['{"status": "ok"}']],
                },
            },
            "proof": {"execution_time_ms": 10.0, "verification_time_ms": 5.0},
        }

        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.verify_claim_endpoints",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.service.verify_proof",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.service.wait_for_proof_verification",
            AsyncMock(return_value=verify_result),
        )
        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.get_settings",
            MagicMock(return_value=MagicMock(api_key="test-key")),
        )

        result = await evaluate_handoff(payload=payload)
        assert result["outcome"] == Outcome.PASS
        assert result["errors"] == []
        assert len(result["per_claim"]) == 1

    async def test_returns_caught_when_trust_gate_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = _make_payload([_make_claim()])

        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.verify_claim_endpoints",
            AsyncMock(side_effect=ValueError("untrusted endpoint")),
        )
        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.service.verify_proof",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.get_settings",
            MagicMock(return_value=MagicMock(api_key="test-key")),
        )

        result = await evaluate_handoff(payload=payload)
        assert result["outcome"] == Outcome.CAUGHT
        assert any("trust gate" in e for e in result["errors"])

    async def test_returns_error_when_verification_raises_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = _make_payload([_make_claim()])

        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.verify_claim_endpoints",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.service.verify_proof",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.service.wait_for_proof_verification",
            AsyncMock(side_effect=RuntimeError("proof failed")),
        )
        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.get_settings",
            MagicMock(return_value=MagicMock(api_key="test-key")),
        )

        result = await evaluate_handoff(payload=payload)
        assert result["outcome"] == Outcome.ERROR
        assert len(result["errors"]) == 1

    async def test_empty_claims_payload_returns_pass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = _make_payload([])

        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.verify_claim_endpoints",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.get_settings",
            MagicMock(return_value=MagicMock(api_key="test-key")),
        )

        result = await evaluate_handoff(payload=payload)
        assert result["outcome"] == Outcome.PASS
        assert result["per_claim"] == []
        assert result["errors"] == []
