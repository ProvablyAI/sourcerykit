"""Default ``handoff_field_guide`` and ``instructions`` text configurations for HandoffPayload layers."""

from typing import Final

_FIELD_DESCRIPTIONS: Final[dict[str, str]] = {
    "provably_org_id": "Provably organization ID; use with integration_api_key for Provably API authentication.",
    "integration_api_key": "API key for Provably; pass as the x-api-key header.",
    "evaluate_url": (
        "URL of the Provably evaluator (handoff evaluation tool / MCP server) that the receiving "
        "agent should call. The run_id field enables full trace lookup in any dashboard."
    ),
    "contract_version": "Schema version of this HandoffPayload.",
    "run_id": "Optional caller-supplied identifier used to correlate a handoff across logs and traces.",
    "claims": (
        "List of claims about sender-agent actions; each claim carries claimed_value, action_name "
        "and query_record_id. The evaluator fetches ground truth from Provably using query_record_id."
    ),
    "provably_mcp_url": "Provably MCP endpoint; alternative verification path.",
    "reasoning": "Free-text reasoning from the sending agent; informational only, not verified.",
    "query_ids": "Parallel list of Provably query UUIDs aligned with claims.",
    "trusted_endpoint_registry": "Snapshot of trusted endpoint URLs for provably_org_id at handoff time.",
    "query_urls": "Human-readable query record URLs aligned with claims.",
    "task": "Task description for this handoff.",
    "verification_results": "Per-claim or aggregate verification labels (often filled after evaluation).",
    "field_guide": "Short descriptions of each top-level field for external agents.",
    "instructions": "Steps the receiving agent should follow.",
    "sdk_precheck": "Optional deterministic precheck from the sender (informational only).",
}


_DEFAULT_INSTRUCTIONS: Final[str] = (
    "You are receiving a Provably HandoffPayload. To verify it: 1) call the evaluator "
    "at evaluate_url with this payload, 2) parse the response for "
    "outcome (PASS or CAUGHT) and per_claim details, 3) report the verdict. You do "
    "not need any prior knowledge of Provably - all credentials and URLs are in this payload."
)


def field_descriptions() -> dict[str, str]:
    """Return the SDK's standard, neutral per-field descriptions."""
    return _FIELD_DESCRIPTIONS


def default_instructions() -> str:
    """Return neutral, default consumer instructions for receiving agents."""
    return _DEFAULT_INSTRUCTIONS
