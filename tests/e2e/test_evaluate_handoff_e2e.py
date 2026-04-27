"""End-to-end test for ``provably.handoff.evaluator.evaluate_handoff``.

Spins up a fake Provably backend on loopback that serves canned ``query_records``
responses, and drives the real evaluator (which uses ``httpx.Client`` internally)
against it. Verifies PASS / CAUGHT outcomes and that the per-org / per-record URL
contract is honored.
"""

from __future__ import annotations

import pytest

from provably.handoff.evaluator import evaluate_handoff
from provably.handoff.types import HandoffClaim, HandoffPayload
from tests.e2e.conftest import FakeHttpServer


def _stored(record: dict) -> dict:
    return {"result": record}


@pytest.mark.e2e
def test_evaluate_handoff_pass_against_real_server(fake_server: FakeHttpServer) -> None:
    fake_server.respond(
        "GET",
        "/api/v1/organizations/org-1/queries/q1",
        status=200,
        body=_stored({"x": 1, "y": 2}),
    )

    payload = HandoffPayload(
        provably_org_id="org-1",
        integration_api_key="key-abc",
        claims=[HandoffClaim(action_name="get", claimed_value={"y": 2, "x": 1}, query_record_id="q1")],
    )

    result = evaluate_handoff(payload, provably_base_url=fake_server.base_url)

    assert result["outcome"] == "PASS"
    assert result["per_claim"][0]["result"] == "PASS"
    assert fake_server.requests[0].headers.get("x-api-key") == "key-abc"


@pytest.mark.e2e
def test_evaluate_handoff_caught_on_mismatch(fake_server: FakeHttpServer) -> None:
    fake_server.respond(
        "GET",
        "/api/v1/organizations/org-1/queries/q1",
        status=200,
        body=_stored({"x": 1}),
    )

    payload = HandoffPayload(
        provably_org_id="org-1",
        integration_api_key="key-abc",
        claims=[HandoffClaim(action_name="get", claimed_value={"x": 999}, query_record_id="q1")],
    )

    result = evaluate_handoff(payload, provably_base_url=fake_server.base_url)

    assert result["outcome"] == "CAUGHT"
    assert result["per_claim"][0]["result"] == "CAUGHT"


@pytest.mark.e2e
def test_evaluate_handoff_caught_when_record_missing(fake_server: FakeHttpServer) -> None:
    payload = HandoffPayload(
        provably_org_id="org-1",
        integration_api_key="key-abc",
        claims=[HandoffClaim(action_name="get", claimed_value={"x": 1}, query_record_id="q-missing")],
    )

    result = evaluate_handoff(payload, provably_base_url=fake_server.base_url)

    assert result["outcome"] == "CAUGHT"
    assert result["errors"], "missing record should surface a transport error"
