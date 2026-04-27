"""Pydantic models for handoff payloads (verifier, dashboard, etc.)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Outcome = Literal["PASS", "CAUGHT"]
"""Final verdict for a handoff: ``"PASS"`` if every claim verified, ``"CAUGHT"`` otherwise."""

VerificationMode = Literal["verbatim", "field_extraction", "schema_type", "range_threshold"]
"""How a claim's ``claimed_value`` is compared against the indexed query record.

- ``verbatim``: canonical-JSON equality of the entire indexed value.
- ``field_extraction``: equality at ``json_path`` only.
- ``schema_type``: JSON-Schema validation at ``json_path``.
- ``range_threshold``: numeric bounds (``range_min``/``range_max``) at ``json_path``.
"""


class HandoffClaim(BaseModel):
    """One outbound HTTP intercept claim; ground truth lives in the matching Provably query record."""

    model_config = ConfigDict(extra="ignore")

    action_name: str = Field(default="", description="Name of the action that produced this claim.")
    claimed_value: Any = Field(default=None, description="Value the agent claims it observed.")
    request_payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Outbound request snapshot (url/method/params/json/data) recorded by the interceptor.",
    )
    response_payload: Any = Field(
        default=None,
        description="Raw response the claim was extracted from; kept for debugging, not compared.",
    )
    query_record_id: str = Field(
        default="",
        description="Provably query record id used to fetch the canonical indexed value.",
    )
    verification_mode: VerificationMode = Field(
        default="verbatim",
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
    provably_org_id: str = Field(default="", description="Provably org id; scopes registry and query lookups.")
    integration_api_key: str = Field(
        default="",
        description="API key the verifier presents (header 'x-api-key') when fetching query records.",
    )
    handoff_evaluate_url: str = Field(
        default="",
        description="Handoff evaluation URL (MCP / evaluator) the consumer calls for this payload.",
    )
    handoff_contract_version: str = Field(default="2.0", description="Wire-contract version.")
    handoff_field_guide: dict[str, str] = Field(
        default_factory=dict,
        description="Free-form per-field notes surfaced in the dashboard.",
    )
    instructions: str = Field(default="", description="Human instructions shown alongside the run.")
    query_record_ids: list[str] = Field(
        default_factory=list,
        description="All query record ids referenced by claims (denormalized for batch fetch).",
    )
    trusted_endpoint_registry: list[str] = Field(
        default_factory=list,
        description="Snapshot of trusted endpoints at handoff time; verifier checks claim URLs against this.",
    )
    run_id: str | None = Field(default=None, description="Stable id correlating logs and dashboard rows.")
    claims: list[HandoffClaim] = Field(
        default_factory=list,
        description="Per-action claims to verify. Outcome is PASS only if every claim passes.",
    )
    verification_results: list[str] = Field(
        default_factory=list,
        description="Optional pre-computed verification strings.",
    )
    query_record_urls: list[str] = Field(
        default_factory=list,
        description="Dashboard deep-links, parallel to query_record_ids.",
    )
    task: str = Field(default="", description="Short task title.")
    reasoning: str = Field(default="", description="Agent's natural-language reasoning trace.")
    sdk_precheck: dict[str, Any] | None = Field(
        default=None,
        description="Optional SDK-side health/precheck output captured before handoff.",
    )


class BenchmarkRow(BaseModel):
    """One row in the dashboard's benchmark table (per-run summary metrics)."""

    model_config = ConfigDict(extra="ignore")

    outcome: Outcome | None = Field(default=None, description="Final verdict: PASS or CAUGHT.")
    body_edited: bool | None = Field(default=None, description="Whether a simulation hook mutated any response.")
    proof_url_count: int | None = Field(default=None, description="Distinct query record URLs proven.")
    proof_time_ms: float | None = Field(default=None, description="Wall-clock time generating proofs (ms).")
    verify_time_ms: float | None = Field(default=None, description="Wall-clock time verifying claims (ms).")
    endpoint_count: int | None = Field(default=None, description="Distinct upstream endpoints touched.")
    llm_model_id: str | None = Field(default=None, description="LLM that produced the agent output.")


class HandoffProofAction(BaseModel):
    """Per-action proof metadata produced by the Provably API during the sender's proof phase."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(default="", description="Action name; matches HandoffClaim.action_name.")
    source_url: str = Field(default="", description="Upstream URL whose response is being proven.")
    query_record_url: str = Field(default="", description="Dashboard URL for the proof record.")
    query_id: str = Field(default="", description="Provably query id; pair with org_id to fetch the record.")
    secret: str = Field(default="", description="Per-action secret required to retrieve the proof artifact.")


class HandoffProofBundle(BaseModel):
    """Aggregate proof artifact returned by the Provably API for a single run."""

    actions: list[HandoffProofAction] = Field(
        default_factory=list,
        description="One entry per proven action, in execution order.",
    )
    verified: bool = Field(
        default=True,
        description="True when proving finished cleanly; false signals a soft failure.",
    )
