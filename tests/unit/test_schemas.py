"""Tests for sourcerykit.schemas — HandoffClaim, HandoffPayload, VerificationMode, etc."""

import uuid

import pytest
from pydantic import ValidationError

from sourcerykit.schemas import (
    HandoffClaim,
    HandoffPayload,
    Outcome,
    SourceryKitAgentResponse,
    VerificationMode,
)
from sourcerykit.schemas.agent_response import ClaimedValue

_ORG = uuid.uuid4()
_QID = uuid.uuid4()


# ---------------------------------------------------------------------------
# VerificationMode
# ---------------------------------------------------------------------------


class TestVerificationMode:
    def test_has_field_extraction(self) -> None:
        assert VerificationMode.FIELD_EXTRACTION.value == "field_extraction"

    def test_has_range_threshold(self) -> None:
        assert VerificationMode.RANGE_THRESHOLD.value == "range_threshold"

    def test_only_two_modes(self) -> None:
        assert set(VerificationMode) == {VerificationMode.FIELD_EXTRACTION, VerificationMode.RANGE_THRESHOLD}


# ---------------------------------------------------------------------------
# Outcome
# ---------------------------------------------------------------------------


class TestOutcome:
    def test_has_pass(self) -> None:
        assert Outcome.PASS == "PASS"

    def test_has_caught(self) -> None:
        assert Outcome.CAUGHT == "CAUGHT"

    def test_has_error(self) -> None:
        assert Outcome.ERROR == "ERROR"


# ---------------------------------------------------------------------------
# HandoffClaim
# ---------------------------------------------------------------------------


class TestHandoffClaim:
    def test_default_construction(self) -> None:
        claim = HandoffClaim()
        assert claim.action_name == ""
        assert claim.claimed_value is None
        assert claim.verification_mode == VerificationMode.FIELD_EXTRACTION

    def test_custom_fields(self) -> None:
        claim = HandoffClaim(
            action_name="fetch_data",
            query_id=_QID,
            verification_mode=VerificationMode.RANGE_THRESHOLD,
            range_min=0,
            range_max=100,
        )
        assert claim.action_name == "fetch_data"
        assert claim.query_id == _QID
        assert claim.range_min == 0
        assert claim.range_max == 100

    def test_query_id_is_uuid_not_string(self) -> None:
        claim = HandoffClaim(query_id=_QID)
        assert isinstance(claim.query_id, uuid.UUID)

    def test_request_payload_defaults_to_empty_dict(self) -> None:
        assert HandoffClaim().request_payload == {}


# ---------------------------------------------------------------------------
# HandoffPayload
# ---------------------------------------------------------------------------


class TestHandoffPayload:
    def test_default_construction(self) -> None:
        payload = HandoffPayload()
        assert payload.evaluate_url == ""
        assert payload.contract_version == "2.0"
        assert payload.claims == []

    def test_custom_fields(self) -> None:
        claim = HandoffClaim(action_name="act")
        payload = HandoffPayload(
            provably_org_id=_ORG,
            integration_api_key="key",
            evaluate_url="https://eval.example.com",
            claims=[claim],
        )
        assert payload.provably_org_id == _ORG
        assert payload.integration_api_key == "key"
        assert len(payload.claims) == 1

    def test_query_ids_default_empty(self) -> None:
        assert HandoffPayload().query_ids == []

    def test_trusted_endpoint_registry_default_empty(self) -> None:
        assert HandoffPayload().trusted_endpoint_registry == []


# ---------------------------------------------------------------------------
# SourceryKitAgentResponse / ClaimedValue
# ---------------------------------------------------------------------------


class TestSourceryKitAgentResponse:
    def test_construction(self) -> None:
        resp = SourceryKitAgentResponse(
            reasoning="I found the value",
            claimed_values=[ClaimedValue(path="$.status", value="open")],
        )
        assert resp.reasoning == "I found the value"
        assert len(resp.claimed_values) == 1

    def test_claimed_value_path_and_value(self) -> None:
        cv = ClaimedValue(path="$.user.id", value="42")
        assert cv.path == "$.user.id"
        assert cv.value == "42"

    def test_missing_claimed_values_raises(self) -> None:
        with pytest.raises(ValidationError):
            SourceryKitAgentResponse(reasoning="ok")  # type: ignore[call-arg]
