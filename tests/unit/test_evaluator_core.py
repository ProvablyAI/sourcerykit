from __future__ import annotations

import json
from typing import Any
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
    resp = MagicMock()
    resp.status_code = 200
    resp.text = "{}"
    resp.json.return_value = stored
    resp.raise_for_status = MagicMock()
    inst = MagicMock()
    inst.get.return_value = resp
    cm = MagicMock()
    cm.__enter__.return_value = inst
    cm.__exit__.return_value = None
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


def test_extract_resultset_raw_response_matches_intercept_body() -> None:
    """Rust query list/GET return QueryAnswer resultset; indexed proof body lives in raw_response."""
    fact = {"fact": "x", "length": 1}
    rec = {
        "id": "q-1",
        "result": {
            "type": "resultset",
            "value": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "raw_response", "type": "string"},
                ],
                "rows": [[1, json.dumps(fact)]],
            },
        },
    }
    out = extract_indexed_from_query_record(rec)
    assert out == fact


def _mock_httpx_client(
    get_response_json: dict[str, Any] | list[dict[str, Any]],
    *,
    post_raises: Exception | None = None,
    post_status: int = 200,
) -> MagicMock:
    """Return an httpx.Client mock.

    ``get_response_json`` may be a single dict (returned for every GET) or a list of dicts
    (consumed in order, last value reused after exhaustion).
    ``post_raises`` lets a test simulate a verify rejection (raised by ``raise_for_status``).
    ``post_status`` lets a test simulate a transient server error status code (e.g. 503).
    """
    bodies = get_response_json if isinstance(get_response_json, list) else [get_response_json]
    responses = []
    for body in bodies:
        r = MagicMock()
        r.status_code = 200
        r.text = "{}"
        r.json.return_value = body
        r.raise_for_status = MagicMock()
        responses.append(r)

    fetch_idx = [0]

    def get_side_effect(*_a: Any, **_kw: Any) -> MagicMock:
        i = min(fetch_idx[0], len(responses) - 1)
        fetch_idx[0] += 1
        return responses[i]

    post_resp = MagicMock()
    post_resp.status_code = post_status
    post_resp.reason_phrase = "Service Unavailable" if post_status == 503 else "OK"
    post_resp.text = "{}"
    post_resp.json.return_value = {}
    if post_raises is not None:
        post_resp.raise_for_status.side_effect = post_raises
    else:
        post_resp.raise_for_status = MagicMock()

    client_inst = MagicMock()
    client_inst.get.side_effect = get_side_effect
    client_inst.post.return_value = post_resp

    cm = MagicMock()
    cm.__enter__.return_value = client_inst
    cm.__exit__.return_value = None
    return cm


@patch("provably.handoff.evaluator.httpx.Client")
def test_per_claim_includes_rust_timings_from_query_record(mock_client_cls: MagicMock) -> None:
    """Rust BE may expose generation/verify ms under alternate keys; we normalize for the dashboard."""
    stored = {
        "result": {"x": 1, "y": 2},
        "execution_time_ms": 12.5,
        "verification_time_ms": 3.0,
    }
    mock_client_cls.return_value = _mock_httpx_client(stored)
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[HandoffClaim(action_name="get", claimed_value={"y": 2, "x": 1}, query_record_id="q1")],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "PASS"
    c0 = r["per_claim"][0]
    assert c0["proof_time_ms"] == 12.5
    assert c0["verify_time_ms"] == 3.0


@patch("provably.handoff.evaluator.httpx.Client")
def test_per_claim_includes_rust_timings_nested_under_proof(mock_client_cls: MagicMock) -> None:
    """Current Rust BE returns timings under ``record.proof.{execution,verification}_time_ms``."""
    stored = {
        "result": {"x": 1, "y": 2},
        "proof": {
            "status": "completed",
            "execution_time_ms": 21.7,
            "verification_time_ms": 4.2,
        },
    }
    mock_client_cls.return_value = _mock_httpx_client(stored)
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[HandoffClaim(action_name="get", claimed_value={"y": 2, "x": 1}, query_record_id="q1")],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "PASS"
    c0 = r["per_claim"][0]
    assert c0["proof_time_ms"] == 21.7
    assert c0["verify_time_ms"] == 4.2


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


def test_missing_query_record_id_is_error_not_caught() -> None:
    """A claim with no query_record_id is an evaluation ERROR, not evidence of tampering.

    Regression: previously the evaluator marked these claims ``CAUGHT``, which produced
    false-positive 'tampering caught' outcomes whenever the SDK failed to provision proofs.
    The honest answer is ERROR — we couldn't actually evaluate.
    """
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[HandoffClaim(action_name="get", claimed_value={"x": 1}, query_record_id="")],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "ERROR"
    assert r["per_claim"][0]["result"] == "ERROR"
    assert "missing query_record_id" in r["per_claim"][0]["detail"]
    assert any("missing query_record_id" in e for e in r["errors"])


def test_missing_base_url_is_error() -> None:
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[HandoffClaim(action_name="get", claimed_value={}, query_record_id="q1")],
    )
    r = evaluate_handoff(hp, provably_base_url="")
    assert r["outcome"] == "ERROR"


def test_missing_creds_is_pass_nothing_to_verify() -> None:
    """No org / api key on the payload ⇒ Provably indexing was off ⇒ trivial PASS.

    This is *not* the same as ``missing query_record_id`` (which is ERROR): here the entire
    payload is opt-out of Provably evaluation, so there's nothing the evaluator could check.
    """
    hp = HandoffPayload(
        provably_org_id="",
        integration_api_key="",
        claims=[HandoffClaim(action_name="get", claimed_value={}, query_record_id="q1")],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "PASS"
    assert r["errors"] and "nothing to verify" in r["errors"][0]


@patch("provably.handoff.evaluator.httpx.Client")
def test_final_verify_step_called_once_per_unique_qrid(mock_client_cls: MagicMock) -> None:
    """Final ``/verify`` runs exactly once per unique ``query_record_id`` after compares."""
    stored = {"result": {"x": 1}, "proof": {"execution_time_ms": 10}}
    mock = _mock_httpx_client(stored)
    mock_client_cls.return_value = mock
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[
            HandoffClaim(action_name="a", claimed_value={"x": 1}, query_record_id="q1"),
            HandoffClaim(action_name="b", claimed_value={"x": 1}, query_record_id="q1"),
            HandoffClaim(action_name="c", claimed_value={"x": 1}, query_record_id="q2"),
        ],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "PASS"

    client_inst = mock.__enter__.return_value
    verify_paths = [call.args[0] for call in client_inst.post.call_args_list if "/verify" in call.args[0]]
    assert len(verify_paths) == 2
    assert any(p.endswith("/queries/q1/verify") for p in verify_paths)
    assert any(p.endswith("/queries/q2/verify") for p in verify_paths)


@patch("provably.handoff.evaluator.httpx.Client")
@patch("provably.handoff.evaluator.time.sleep")
def test_final_verify_failure_marks_caught(mock_sleep: MagicMock, mock_client_cls: MagicMock) -> None:
    """If ``/verify`` returns a 4xx (proof rejected), the proof did not validate ⇒ CAUGHT."""
    stored = {"result": {"x": 1}, "proof": {"execution_time_ms": 10}}
    mock_client_cls.return_value = _mock_httpx_client(stored, post_raises=RuntimeError("verify rejected"))
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[HandoffClaim(action_name="a", claimed_value={"x": 1}, query_record_id="q1")],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "CAUGHT"
    assert r["per_claim"][0]["result"] == "CAUGHT"
    assert "proof verify failed" in r["per_claim"][0]["detail"]
    assert any("proof verify failed for q1" in e for e in r["errors"])


@patch("provably.handoff.evaluator.httpx.Client")
@patch("provably.handoff.evaluator.time.sleep")
def test_verify_503_marks_error_not_caught(mock_sleep: MagicMock, mock_client_cls: MagicMock) -> None:
    """A 503 from ``/verify`` is a server outage — result is ERROR, not CAUGHT (no tampering signal)."""
    stored = {"result": {"x": 1}, "proof": {"execution_time_ms": 10}}
    mock_client_cls.return_value = _mock_httpx_client(stored, post_status=503)
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[HandoffClaim(action_name="a", claimed_value={"x": 1}, query_record_id="q1")],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "ERROR"
    assert r["per_claim"][0]["result"] == "ERROR"
    assert "unavailable" in r["per_claim"][0]["detail"]
    assert any("proof verify unavailable" in e for e in r["errors"])


@patch("provably.handoff.evaluator.httpx.Client")
def test_verify_then_refresh_populates_tvt(mock_client_cls: MagicMock) -> None:
    """Verify-then-refresh: TPT comes from the first GET, TVT from the post-verify GET."""
    pre_verify = {"result": {"x": 1}, "proof": {"execution_time_ms": 7.0}}
    post_verify = {
        "result": {"x": 1},
        "proof": {"execution_time_ms": 7.0, "verification_time_ms": 2.5},
    }
    mock_client_cls.return_value = _mock_httpx_client([pre_verify, post_verify])
    hp = HandoffPayload(
        provably_org_id="org",
        integration_api_key="k",
        claims=[HandoffClaim(action_name="a", claimed_value={"x": 1}, query_record_id="q1")],
    )
    r = evaluate_handoff(hp, provably_base_url="http://api.test")
    assert r["outcome"] == "PASS"
    entry = r["per_claim"][0]
    assert entry["proof_time_ms"] == 7.0
    assert entry["verify_time_ms"] == 2.5
