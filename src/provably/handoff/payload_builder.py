from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from provably.common.env import get_env_str
from provably.handoff import client as handoff_client
from provably.handoff.guide import default_instructions, field_descriptions
from provably.handoff.types import HandoffClaim, HandoffPayload, VerificationMode
from provably.intercept import is_enabled, load_latest_intercept_payload
from provably.trusted_endpoints import load_trusted_endpoint_urls

_VERIFICATION_MODES: frozenset[VerificationMode] = frozenset(
    ("verbatim", "field_extraction", "schema_type", "range_threshold")
)

DEFAULT_HANDOFF_TASK = "Handoff verification via handoff_evaluate_url."


def build_handoff_payload(
    fetch_and_claim: Mapping[str, Any] | dict[str, Any] | None,
    *,
    run_id: str | None = None,
    task: str = DEFAULT_HANDOFF_TASK,
    intercept_agent_id: str = "fetch_and_claim",
    handoff_field_guide: dict[str, str] | None = None,
    instructions: str | None = None,
    provably_indexing: bool | None = None,
) -> HandoffPayload:
    blob: dict[str, Any] = dict(fetch_and_claim) if fetch_and_claim else {}
    provably_on = is_enabled() if provably_indexing is None else provably_indexing
    env = _resolve_env(provably_on)

    claims, query_record_urls, query_record_ids = _build_claims(
        blob,
        pg_url=env["postgres_url"],
        intercept_agent_id=intercept_agent_id,
    )

    reasoning = str(blob.get("reasoning") or "")

    if handoff_field_guide is not None:
        guide = handoff_field_guide
    else:
        guide = field_descriptions(provably_indexing=provably_on)
    if instructions is not None:
        instr = instructions
    else:
        instr = default_instructions(provably_indexing=provably_on)

    return HandoffPayload(
        provably_mcp_url=env["mcp_url"],
        provably_org_id=env["org_id"],
        integration_api_key=env["integration_key"],
        handoff_evaluate_url=env["evaluate_url"],
        handoff_contract_version="2.0",
        handoff_field_guide=guide,
        instructions=instr,
        query_record_ids=query_record_ids,
        trusted_endpoint_registry=env["trusted_registry_urls"],
        run_id=run_id,
        claims=claims,
        verification_results=[],
        query_record_urls=query_record_urls,
        task=task,
        reasoning=reasoning,
    )


def _resolve_env(provably_on: bool) -> dict[str, Any]:
    mcp_url = get_env_str("PROVABLY_MCP_URL")
    pg = get_env_str("POSTGRES_URL")
    org_id = get_env_str("PROVABLY_ORG_ID")
    integration_key = ""
    trusted_registry_urls: list[str] = []
    if provably_on:
        integration_key = handoff_client.cached_integration_api_key()
        if not integration_key:
            raise RuntimeError(
                "Provably runtime not initialized: missing integration_api_key. "
                "Call initialize_runtime() before enabling intercepts."
            )
        trusted_registry_urls = load_trusted_endpoint_urls(pg, org_id)
    return {
        "mcp_url": mcp_url,
        "postgres_url": pg,
        "org_id": org_id,
        "integration_key": integration_key,
        "evaluate_url": mcp_url if provably_on else "",
        "trusted_registry_urls": trusted_registry_urls,
    }


def _build_claims(
    fetch_and_claim_json: Any,
    *,
    pg_url: str,
    intercept_agent_id: str,
) -> tuple[list[HandoffClaim], list[str], list[str]]:
    raw_claims = (
        fetch_and_claim_json.get("claims") if isinstance(fetch_and_claim_json, dict) else None
    )
    if not isinstance(raw_claims, list):
        return [], [], []

    claims: list[HandoffClaim] = []
    urls: list[str] = []
    ids: list[str] = []

    for raw in raw_claims:
        if not isinstance(raw, dict):
            continue
        action_name = str(raw.get("action_name") or "")
        if not action_name:
            continue

        claimed_value = raw.get("claimed_value")
        request_payload, response_payload = load_latest_intercept_payload(
            pg_url, action_name, agent_id=intercept_agent_id
        )
        if not pg_url:
            response_payload = claimed_value

        urls.append("")
        ids.append("")
        claims.append(_build_claim(raw, action_name, claimed_value, request_payload, response_payload, ""))

    return claims, urls, ids


def _build_claim(
    raw: dict[str, Any],
    action_name: str,
    claimed_value: Any,
    request_payload: dict[str, Any],
    response_payload: Any,
    query_id: str,
) -> HandoffClaim:
    schema = raw.get("expected_json_schema") if isinstance(raw.get("expected_json_schema"), dict) else None
    return HandoffClaim(
        action_name=action_name,
        claimed_value=claimed_value,
        request_payload=request_payload,
        response_payload=response_payload,
        query_record_id=str(query_id) if query_id else "",
        verification_mode=_coerce_verification_mode(raw.get("verification_mode")),
        json_path=str(raw.get("json_path") or ""),
        expected_json_schema=schema,
        range_min=raw.get("range_min"),
        range_max=raw.get("range_max"),
    )


def _coerce_verification_mode(raw: Any) -> VerificationMode:
    mode = str(raw or "verbatim").strip()
    if mode in _VERIFICATION_MODES:
        return cast(VerificationMode, mode)
    return "verbatim"


__all__ = ["DEFAULT_HANDOFF_TASK", "build_handoff_payload"]
