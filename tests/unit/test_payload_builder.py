from __future__ import annotations

import pytest

from provably.handoff.payload_builder import DEFAULT_HANDOFF_TASK, build_handoff_payload


@pytest.fixture
def min_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVABLY_MCP_URL", "http://mcp.example")
    monkeypatch.setenv("POSTGRES_URL", "")
    monkeypatch.setenv("PROVABLY_ORG_ID", "org-1")


def test_build_empty_claims_minimal(
    min_env: None,
) -> None:
    hp = build_handoff_payload(
        None,
        run_id="run-1",
        provably_indexing=False,
    )
    assert hp.claims == []
    assert hp.run_id == "run-1"
    assert hp.task == DEFAULT_HANDOFF_TASK
    assert hp.handoff_evaluate_url == ""
    assert hp.handoff_field_guide
    assert "handoff_evaluate_url" in hp.handoff_field_guide
    assert hp.instructions
    assert "[NOTE] Provably intercept indexing was OFF" in hp.instructions


def test_build_claim_without_db_uses_claimed_value_as_response(
    min_env: None,
) -> None:
    hp = build_handoff_payload(
        {"claims": [{"action_name": "x", "claimed_value": {"ok": True}}], "reasoning": "r"},
        provably_indexing=False,
    )
    assert len(hp.claims) == 1
    c = hp.claims[0]
    assert c.action_name == "x"
    assert c.response_payload == {"ok": True}
    assert c.request_payload == {}
    assert hp.reasoning == "r"
