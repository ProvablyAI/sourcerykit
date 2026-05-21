"""Pydantic models for handoff payloads (verifier, dashboard, etc.)."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agentkit.schemas.verification_mode import VerificationMode


class HandoffClaim(BaseModel):
    """One outbound HTTP intercept claim; ground truth lives in the matching Provably query record."""

    model_config = ConfigDict(extra="ignore")

    action_name: str = Field(default="", description="Name of the action that produced this claim.")
    claimed_value: Any = Field(default=None, description="Value the agent claims it observed.")
    request_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Outbound request snapshot (url/method/params/json/data) recorded by the interceptor.",
    )
    response_payload: dict[str, Any] | None = Field(
        default=None,
        description="Raw response the claim was extracted from; kept for debugging, not compared.",
    )
    query_id: uuid.UUID = Field(
        default=uuid.NIL,
        description="Provably query record UUID used to fetch the canonical indexed value.",
    )
    verification_mode: VerificationMode = Field(
        default=VerificationMode.VERBATIM,
        description="How claimed_value is compared to the indexed payload.",
    )
    json_path: str = Field(
        default="",
        description=(
            "Path into the indexed JSON: dot form (e.g. 'response.field_x') or JSONPath root "
            "style '$.userId' / '$.' (empty or '$' = full payload)."
        ),
    )
    expected_json_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema applied at json_path; required for verification_mode='schema_type'.",
    )
    range_min: float | int | None = Field(
        default=None,
        description="Inclusive lower bound for verification_mode='range_threshold'.",
    )
    range_max: float | int | None = Field(
        default=None,
        description="Inclusive upper bound for verification_mode='range_threshold'.",
    )


class HandoffPayload(BaseModel):
    """Handoff contract v2 — assembled by deterministic sender-side code (never by the LLM)."""

    model_config = ConfigDict(extra="ignore")

    provably_mcp_url: str = Field(default="", description="Base URL of the Provably MCP server.")
    provably_org_id: uuid.UUID = Field(
        default=uuid.NIL, description="Provably org id; scopes registry and query lookups."
    )
    integration_api_key: str = Field(
        default="",
        description="API key the verifier presents (header 'x-api-key') when fetching query records.",
    )
    evaluate_url: str = Field(
        default="",
        description="Evaluation URL (MCP / evaluator) the consumer calls for this payload.",
    )
    contract_version: str = Field(default="2.0", description="Wire-contract version.")
    field_guide: dict[str, str] = Field(
        default_factory=dict,
        description="Free-form per-field notes surfaced in the dashboard.",
    )
    instructions: str = Field(default="", description="Human instructions shown alongside the run.")
    query_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="All query ids referenced by claims (denormalized for batch fetch).",
    )
    trusted_endpoint_registry: list[str] = Field(
        default_factory=list,
        description="Snapshot of trusted endpoints at handoff time; verifier checks claim URLs against this.",
    )
    run_id: uuid.UUID | None = Field(default=None, description="Stable id correlating logs and dashboard rows.")
    claims: list[HandoffClaim] = Field(
        default_factory=list,
        description="Per-action claims to verify. Outcome is PASS only if every claim passes.",
    )
    verification_results: list[str] = Field(
        default_factory=list,
        description="Optional pre-computed verification strings.",
    )
    query_urls: list[str] = Field(
        default_factory=list,
        description="Dashboard deep-links, parallel to query_ids.",
    )
    task: str = Field(default="", description="Short task title.")
    reasoning: str = Field(default="", description="Agent's natural-language reasoning trace.")
    sdk_precheck: dict[str, Any] | None = Field(
        default=None,
        description="Optional SDK-side health/precheck output captured before handoff.",
    )
