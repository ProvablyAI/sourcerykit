"""Neutral, schema-level guide embedded in outgoing :class:`HandoffPayload` values.

The strings in this module are designed to be packed into a payload's
``handoff_field_guide`` and ``instructions`` fields so a downstream agent that has
never seen the SDK can still understand what each top-level field means and how to
verify the payload at inference time.

These descriptions are deliberately **neutral**: they don't name any specific
sender / receiver agent, deployment, or simulation. Consumers (e.g. the example
``cluster_a`` agent in this repo's sibling demo) are expected to merge their own
deployment-flavoured overrides on top via plain ``dict.update``.
"""

from __future__ import annotations

__all__ = [
    "DEFAULT_INSTRUCTIONS",
    "FIELD_DESCRIPTIONS",
    "FIELD_DESCRIPTIONS_OFF",
    "PROVABLY_OFF_NOTE",
    "default_instructions",
    "field_descriptions",
]


FIELD_DESCRIPTIONS: dict[str, str] = {
    "provably_org_id": (
        "Provably organization ID; use with integration_api_key for Provably API authentication."
    ),
    "integration_api_key": "API key for Provably; pass as the x-api-key header.",
    "handoff_evaluate_url": (
        "URL of the Provably evaluator (handoff evaluation tool / MCP server) that the receiving "
        "agent should call. The run_id field enables full trace lookup in any dashboard."
    ),
    "handoff_contract_version": "Schema version of this HandoffPayload.",
    "run_id": (
        "Optional caller-supplied identifier used to correlate a handoff across logs and traces."
    ),
    "claims": (
        "List of claims about sender-agent actions; each claim carries claimed_value, action_name "
        "and query_record_id. The evaluator fetches ground truth from Provably using query_record_id."
    ),
    "provably_mcp_url": "Provably MCP endpoint; alternative verification path.",
    "reasoning": "Free-text reasoning from the sending agent; informational only, not verified.",
    "query_record_ids": "Parallel list of Provably query UUIDs aligned with claims.",
    "trusted_endpoint_registry": (
        "Snapshot of trusted endpoint URLs for provably_org_id at handoff time."
    ),
    "query_record_urls": "Human-readable query record URLs aligned with claims.",
    "task": "Task description for this handoff.",
    "verification_results": (
        "Per-claim or aggregate verification labels (often filled after evaluation)."
    ),
    "handoff_field_guide": "Short descriptions of each top-level field for external agents.",
    "instructions": "Steps the receiving agent should follow.",
    "sdk_precheck": "Optional deterministic precheck from the sender (informational only).",
}


FIELD_DESCRIPTIONS_OFF: dict[str, str] = {
    "handoff_evaluate_url": (
        "Empty when Provably intercept indexing was disabled; no evaluator POST for this run."
    ),
    "integration_api_key": "Empty when Provably was off; not used for this run.",
    "query_record_ids": "Empty when Provably was off; no proof query IDs.",
    "trusted_endpoint_registry": (
        "Empty when Provably was off; trusted endpoint policy enforcement is skipped."
    ),
    "query_record_urls": "Empty when Provably was off; no query record URLs.",
}


DEFAULT_INSTRUCTIONS = (
    "You are receiving a Provably HandoffPayload. To verify it: 1) call the handoff "
    "evaluator at handoff_evaluate_url with this payload, 2) parse the response for "
    "outcome (PASS or CAUGHT) and per_claim details, 3) report the verdict. You do "
    "not need any prior knowledge of Provably - all credentials and URLs are in this payload."
)


PROVABLY_OFF_NOTE = (
    "\n\n[NOTE] Provably intercept indexing was OFF for this run: integration_api_key and "
    "per-claim query_record_id are empty by design; handoff_evaluate_url is empty. "
    "There is no server-side query-record verification for this payload."
)


def field_descriptions(*, provably_indexing: bool) -> dict[str, str]:
    """Return the SDK's neutral per-field descriptions, with off-mode overrides merged when applicable.

    Args:
        provably_indexing: When ``False``, :data:`FIELD_DESCRIPTIONS_OFF` is merged in
            to explain why several fields are empty for that run.

    Returns:
        A fresh dict (safe for the caller to mutate / further-update with deployment-specific text).
    """
    guide = dict(FIELD_DESCRIPTIONS)
    if not provably_indexing:
        guide.update(FIELD_DESCRIPTIONS_OFF)
    return guide


def default_instructions(*, provably_indexing: bool) -> str:
    """Return neutral SDK-default consumer instructions; appends :data:`PROVABLY_OFF_NOTE` when off."""
    return DEFAULT_INSTRUCTIONS if provably_indexing else DEFAULT_INSTRUCTIONS + PROVABLY_OFF_NOTE
