from __future__ import annotations

from typing import get_args

from agentkit.handoff.contract import claim_contract
from agentkit.handoff.types import HandoffClaim, VerificationMode


def test_contract_includes_every_verification_mode() -> None:
    text = claim_contract()
    for mode in get_args(VerificationMode):
        assert mode in text


def test_contract_lists_only_llm_facing_claim_fields() -> None:
    text = claim_contract()
    expected_in = {
        "action_name",
        "claimed_value",
        "verification_mode",
        "json_path",
        "expected_json_schema",
        "range_min",
        "range_max",
    }
    for field in expected_in:
        assert f'"{field}"' in text
    for sdk_only in ("query_record_id", "request_payload", "response_payload"):
        assert f'"{sdk_only}":' not in text


def test_contract_marks_sdk_managed_fields_as_excluded() -> None:
    text = claim_contract()
    assert "query_record_id" in text
    assert "added by the system" in text


def test_contract_action_names_become_allowlist_rule() -> None:
    text = claim_contract(action_names=["endpoint_0", "endpoint_1"])
    assert "action_name must be one of: endpoint_0, endpoint_1." in text


def test_contract_omits_action_name_rule_when_unspecified() -> None:
    text = claim_contract()
    assert "action_name must be one of" not in text


def test_contract_wrapper_fields_appear_before_claims() -> None:
    text = claim_contract(wrapper_fields={"reasoning": "string"})
    head = text.split('"claims"')[0]
    assert '"reasoning": string' in head


def test_contract_extra_rules_appended_at_end() -> None:
    text = claim_contract(extra_rules=["Keep claims minimal and high-signal."])
    assert text.rstrip().endswith("- Keep claims minimal and high-signal.")


def test_contract_is_neutral_no_named_agents() -> None:
    """SDK contract must not name Cluster A / Cluster B; consumers add personas."""
    text = claim_contract()
    assert "Cluster A" not in text
    assert "Cluster B" not in text


def test_contract_field_set_matches_handoff_claim_model() -> None:
    """Drift guard: every LLM-facing field must exist on HandoffClaim."""
    llm_fields = {"action_name", "claimed_value", "verification_mode", "json_path",
                  "expected_json_schema", "range_min", "range_max"}
    assert llm_fields.issubset(HandoffClaim.model_fields.keys())
