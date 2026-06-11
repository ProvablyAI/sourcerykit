"""End-to-end tests for evaluate_handoff.

Spins up a real loopback HTTP server that mimics the Provably API and wires a
real ProvablyHTTPClient to it. Only the DB layer (verify_claim_endpoints) is
mocked, because it requires a live Postgres connection.

What is NOT mocked:
  - httpx.AsyncClient calls — real TCP server
  - JSON serialisation / deserialisation pipeline
  - evaluate_claim logic
  - QueryAnswer.flatten() response unwrapping

Scenarios:
  A — PASS: stored aggregate value matches the claim
  B — CAUGHT: stored value differs from the claim
  C — CAUGHT: verify_claim_endpoints raises SourceryKitTrustError
  D — ERROR: proof verification polling returns "Failed"
"""

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest

from sourcerykit.config import Settings
from sourcerykit.errors import SourceryKitTrustError
from sourcerykit.evaluator.evaluator import evaluate_handoff
from sourcerykit.provably._api import ProvablyAPI
from sourcerykit.provably._http import ProvablyHTTPClient
from sourcerykit.schemas import HandoffClaim, HandoffPayload, Outcome, VerificationMode
from sourcerykit.schemas.agent_response import ClaimedValue
from tests.e2e.conftest import FakeHttpServer

_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")
_ORG_PATH = f"/api/v1/organizations/{_ORG}"


# ---------------------------------------------------------------------------
# Helpers — canned Provably API responses
# ---------------------------------------------------------------------------


def _verified_response(result_value: Any) -> dict[str, Any]:
    """Provably query response with a completed, verified proof."""
    return {
        "result": {"type": "aggregate", "value": str(result_value)},
        "proof": {
            "verification_status": "Verified",
            "execution_time_ms": 12.0,
            "verification_time_ms": 7.0,
        },
    }


def _failed_proof_response() -> dict[str, Any]:
    return {
        "result": {"type": "aggregate", "value": "some-value"},
        "proof": {
            "verification_status": "Failed",
            "execution_time_ms": 5.0,
            "verification_time_ms": 0.0,
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def _provably_settings(fake_server: FakeHttpServer) -> Settings:
    """Settings object whose provably_api URL points at the loopback fake server."""
    return Settings(
        api_key="int-test-key",
        org_id=_ORG,
        postgres_url="postgresql://test/db",
        provably_api=fake_server.base_url,
        provably_app="http://localhost",
        provably_mcp="http://localhost",
    )


@pytest.fixture
def _wired_service(_provably_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the Provably service layer to use a real HTTP client pointed at the fake server.

    The evaluator imports ``service`` from ``sourcerykit.provably.service`` and calls
    ``service.verify_proof`` and ``service.wait_for_proof_verification``.
    Those methods call ``get_api()`` which calls ``get_http()``.

    We patch:
      - ``sourcerykit.provably._api.get_http`` to return our ProvablyHTTPClient
      - ``sourcerykit.provably.service.get_api`` to return our ProvablyAPI
      - ``sourcerykit.evaluator.evaluator.get_settings`` to return fake_settings
    """
    http_client = ProvablyHTTPClient(settings=_provably_settings)
    api = ProvablyAPI(settings=_provably_settings)

    monkeypatch.setattr("sourcerykit.provably._api.get_http", lambda: http_client)
    monkeypatch.setattr("sourcerykit.provably.service.get_api", lambda: api)
    monkeypatch.setattr(
        "sourcerykit.evaluator.evaluator.get_settings",
        lambda: _provably_settings,
    )


def _mock_trust_gate_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sourcerykit.evaluator.evaluator.verify_claim_endpoints",
        AsyncMock(return_value=None),
    )


def _make_claim(qid: uuid.UUID, claimed: str = "open") -> HandoffClaim:
    return HandoffClaim(
        action_name="get_status",
        query_id=qid,
        verification_mode=VerificationMode.FIELD_EXTRACTION,
        claimed_value=[ClaimedValue(path="$", value=claimed)],
        json_path="$",
        request_payload={"url": "https://api.trusted.example.com"},
    )


def _make_payload(*claims: HandoffClaim) -> HandoffPayload:
    return HandoffPayload(
        provably_org_id=_ORG,
        integration_api_key="int-test-key",
        claims=list(claims),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestEvaluateHandoffE2E:
    async def test_pass_when_stored_value_matches_claim(
        self,
        fake_server: FakeHttpServer,
        _wired_service: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """PASS: the Provably API returns a value that equals the claimed value."""
        qid = uuid.uuid4()
        fake_server.respond("POST", f"{_ORG_PATH}/queries/{qid}/verify", status=200, body={})
        fake_server.respond("GET", f"{_ORG_PATH}/queries/{qid}", status=200, body=_verified_response("open"))

        _mock_trust_gate_pass(monkeypatch)
        payload = _make_payload(_make_claim(qid, claimed="open"))

        result = await evaluate_handoff(payload)

        assert result["outcome"] == Outcome.PASS
        assert result["errors"] == []
        assert len(result["per_claim"]) == 1
        assert result["per_claim"][0]["result"] == Outcome.PASS

    async def test_caught_when_stored_value_differs_from_claim(
        self,
        fake_server: FakeHttpServer,
        _wired_service: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """CAUGHT: the Provably API returns a value that does NOT match the claim."""
        qid = uuid.uuid4()
        fake_server.respond("POST", f"{_ORG_PATH}/queries/{qid}/verify", status=200, body={})
        # Server stores "closed" but the claim says "open"
        fake_server.respond("GET", f"{_ORG_PATH}/queries/{qid}", status=200, body=_verified_response("closed"))

        _mock_trust_gate_pass(monkeypatch)
        payload = _make_payload(_make_claim(qid, claimed="open"))

        result = await evaluate_handoff(payload)

        assert result["outcome"] == Outcome.CAUGHT
        assert result["per_claim"][0]["result"] == Outcome.CAUGHT

    async def test_caught_when_trust_gate_raises(
        self,
        fake_server: FakeHttpServer,
        _wired_service: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """CAUGHT: trust gate fires before any HTTP calls are made."""
        qid = uuid.uuid4()
        monkeypatch.setattr(
            "sourcerykit.evaluator.evaluator.verify_claim_endpoints",
            AsyncMock(side_effect=SourceryKitTrustError("untrusted endpoint")),
        )
        payload = _make_payload(_make_claim(qid))

        result = await evaluate_handoff(payload)

        assert result["outcome"] == Outcome.CAUGHT
        assert any("trust gate" in e for e in result["errors"])
        # No HTTP calls should have been made to the fake server
        assert len(fake_server.requests) == 0

    async def test_error_when_proof_verification_fails(
        self,
        fake_server: FakeHttpServer,
        _wired_service: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """ERROR: the Provably API returns a Failed verification_status."""
        qid = uuid.uuid4()
        fake_server.respond("POST", f"{_ORG_PATH}/queries/{qid}/verify", status=200, body={})
        fake_server.respond("GET", f"{_ORG_PATH}/queries/{qid}", status=200, body=_failed_proof_response())

        _mock_trust_gate_pass(monkeypatch)
        payload = _make_payload(_make_claim(qid))

        result = await evaluate_handoff(payload)

        assert result["outcome"] == Outcome.ERROR
        assert len(result["errors"]) == 1

    async def test_timings_extracted_from_proof_envelope(
        self,
        fake_server: FakeHttpServer,
        _wired_service: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """per_claim verdict should include proof and verify timing fields."""
        qid = uuid.uuid4()
        fake_server.respond("POST", f"{_ORG_PATH}/queries/{qid}/verify", status=200, body={})
        fake_server.respond("GET", f"{_ORG_PATH}/queries/{qid}", status=200, body=_verified_response("open"))

        _mock_trust_gate_pass(monkeypatch)
        payload = _make_payload(_make_claim(qid, claimed="open"))

        result = await evaluate_handoff(payload)

        verdict = result["per_claim"][0]
        assert "proof_time_ms" in verdict
        assert "verify_time_ms" in verdict
        assert verdict["proof_time_ms"] == 12.0
        assert verdict["verify_time_ms"] == 7.0

    async def test_multiple_claims_evaluated_independently(
        self,
        fake_server: FakeHttpServer,
        _wired_service: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Multiple claims: one PASS, one CAUGHT → overall outcome is CAUGHT."""
        qid_a = uuid.uuid4()
        qid_b = uuid.uuid4()
        fake_server.respond("POST", f"{_ORG_PATH}/queries/{qid_a}/verify", status=200, body={})
        fake_server.respond("GET", f"{_ORG_PATH}/queries/{qid_a}", status=200, body=_verified_response("yes"))
        fake_server.respond("POST", f"{_ORG_PATH}/queries/{qid_b}/verify", status=200, body={})
        # qid_b claim says "yes" but server stores "no"
        fake_server.respond("GET", f"{_ORG_PATH}/queries/{qid_b}", status=200, body=_verified_response("no"))

        _mock_trust_gate_pass(monkeypatch)
        payload = _make_payload(
            _make_claim(qid_a, claimed="yes"),
            _make_claim(qid_b, claimed="yes"),
        )

        result = await evaluate_handoff(payload)

        assert result["outcome"] == Outcome.CAUGHT
        assert len(result["per_claim"]) == 2
        outcomes = {c["result"] for c in result["per_claim"]}
        assert Outcome.PASS in outcomes
        assert Outcome.CAUGHT in outcomes

    async def test_verify_proof_uses_integration_api_key_header(
        self,
        fake_server: FakeHttpServer,
        _wired_service: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The x-api-key header on proof verification must come from get_settings().api_key."""
        qid = uuid.uuid4()
        fake_server.respond("POST", f"{_ORG_PATH}/queries/{qid}/verify", status=200, body={})
        fake_server.respond("GET", f"{_ORG_PATH}/queries/{qid}", status=200, body=_verified_response("open"))

        _mock_trust_gate_pass(monkeypatch)
        payload = _make_payload(_make_claim(qid, claimed="open"))

        await evaluate_handoff(payload)

        # All requests to the fake server should carry the configured API key
        for req in fake_server.requests:
            assert req.headers.get("x-api-key") == "int-test-key", (
                f"request to {req.path} missing or wrong x-api-key header"
            )
