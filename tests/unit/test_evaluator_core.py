from __future__ import annotations

from unittest.mock import MagicMock, patch

from provably.handoff.evaluator import (
    evaluate_handoff,
    extract_indexed_from_query_record,
)
from provably.handoff.types import HandoffClaim, HandoffPayload


def test_trust_gate_caught_when_url_untrusted() -> None:
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[
            HandoffClaim(
                action_name="get",
                claimed_value={},
                query_record_id="q1",
                request_payload={"url": "https://untrusted.example/api"},
            )
        ],
    )
    with patch(
        "provably.handoff.evaluator.check_claim_endpoints_are_trusted",
        side_effect=ValueError("handoff has untrusted endpoints: https://untrusted.example/api"),
    ):
        r = evaluate_handoff(hp, provably_base_url="http://api.test", postgres_url="x")
    assert r["outcome"] == "CAUGHT"
    assert r["per_claim"] == []
    assert r["errors"] and "trust gate" in r["errors"][0]


def test_trust_gate_caught_when_postgres_missing_with_urls() -> None:
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[
            HandoffClaim(
                action_name="get",
                claimed_value={},
                query_record_id="q1",
                request_payload={"url": "https://api.test/x"},
            )
        ],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "CAUGHT"
    assert r["errors"] and "trust gate" in r["errors"][0]


@patch("provably.handoff.evaluator.httpx.Client")
def test_trust_gate_skipped_when_no_urls(mock_client_cls: MagicMock) -> None:
    stored = {"result": {"x": 1}}
    resp = MagicMock(); resp.status_code = 200; resp.text = "{}"
    resp.json.return_value = stored; resp.raise_for_status = MagicMock()
    inst = MagicMock(); inst.get.return_value = resp
    cm = MagicMock(); cm.__enter__.return_value = inst; cm.__exit__.return_value = None
    mock_client_cls.return_value = cm
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[HandoffClaim(action_name="get", claimed_value={"x": 1}, query_record_id="q1")],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "PASS"


def test_extract_prefers_result_key() -> None:
    assert extract_indexed_from_query_record({"result": {"a": 1}}) == {"a": 1}


def test_extract_nested_query_dict() -> None:
    rec = {"query": {"raw_response": [1, 2]}}
    assert extract_indexed_from_query_record(rec) == [1, 2]


def _mock_httpx_client(get_response_json: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.text = "{}"
    resp.json.return_value = get_response_json
    resp.raise_for_status = MagicMock()

    client_inst = MagicMock()
    client_inst.get.return_value = resp

    cm = MagicMock()
    cm.__enter__.return_value = client_inst
    cm.__exit__.return_value = None
    return cm


@patch("provably.handoff.evaluator.httpx.Client")
def test_evaluate_handoff_pass_when_canonical_matches(mock_client_cls: MagicMock) -> None:
    stored = {"result": {"x": 1, "y": 2}}
    mock_client_cls.return_value = _mock_httpx_client(stored)
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[HandoffClaim(action_name="get", claimed_value={"y": 2, "x": 1}, query_record_id="q1")],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "PASS"
    assert all(c["result"] == "PASS" for c in r["per_claim"])


@patch("provably.handoff.evaluator.httpx.Client")
def test_evaluate_handoff_caught_when_mismatch(mock_client_cls: MagicMock) -> None:
    mock_client_cls.return_value = _mock_httpx_client({"result": {"x": 1}})
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[HandoffClaim(action_name="get", claimed_value={"x": 2}, query_record_id="q1")],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "CAUGHT"


@patch("provably.handoff.evaluator.httpx.Client")
def test_field_extraction_pass(mock_client_cls: MagicMock) -> None:
    stored = {"result": {"response": {"field_x": 42}}}
    mock_client_cls.return_value = _mock_httpx_client(stored)
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[
            HandoffClaim(
                action_name="get",
                claimed_value=42,
                query_record_id="q1",
                verification_mode="field_extraction",
                json_path="response.field_x",
            )
        ],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "PASS"


@patch("provably.handoff.evaluator.httpx.Client")
def test_schema_type_pass(mock_client_cls: MagicMock) -> None:
    stored = {"result": {"items": [1, 2]}}
    mock_client_cls.return_value = _mock_httpx_client(stored)
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[
            HandoffClaim(
                action_name="get",
                claimed_value=None,
                query_record_id="q1",
                verification_mode="schema_type",
                json_path="items",
                expected_json_schema={"type": "array", "items": {"type": "integer"}},
            )
        ],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "PASS"


@patch("provably.handoff.evaluator.httpx.Client")
def test_range_threshold_pass(mock_client_cls: MagicMock) -> None:
    stored = {"result": {"score": 0.5}}
    mock_client_cls.return_value = _mock_httpx_client(stored)
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[
            HandoffClaim(
                action_name="get",
                claimed_value=0.5,
                query_record_id="q1",
                verification_mode="range_threshold",
                json_path="score",
                range_min=0.0,
                range_max=1.0,
            )
        ],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "PASS"


@patch("provably.handoff.evaluator.httpx.Client")
def test_range_threshold_caught_when_claim_wrong(mock_client_cls: MagicMock) -> None:
    stored = {"result": {"score": 0.5}}
    mock_client_cls.return_value = _mock_httpx_client(stored)
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[
            HandoffClaim(
                action_name="get",
                claimed_value=0.9,
                query_record_id="q1",
                verification_mode="range_threshold",
                json_path="score",
                range_min=0.0,
                range_max=1.0,
            )
        ],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "CAUGHT"
