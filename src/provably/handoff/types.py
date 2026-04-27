"""Pydantic models for handoff payloads (Cluster A → B, dashboard)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Outcome = Literal["PASS", "CAUGHT"]

VerificationMode = Literal["verbatim", "field_extraction", "schema_type", "range_threshold"]


class HandoffClaim(BaseModel):
    """One outbound HTTP intercept claim; ground truth for compare lives in Provably query records."""

    model_config = ConfigDict(extra="ignore")

    action_name: str = ""
    claimed_value: Any = None
    request_payload: dict[str, Any] = Field(default_factory=dict)
    response_payload: Any = None
    query_record_id: str = ""
    # How to compare claimed_value against the indexed query record (default: full canonical match).
    verification_mode: VerificationMode = "verbatim"
    # Dot path into the indexed payload (e.g. "response.field_x"). Empty = root of extracted indexed value.
    json_path: str = ""
    # For verification_mode == "schema_type": JSON Schema for the value at json_path (or whole indexed if path empty).
    expected_json_schema: dict[str, Any] | None = None
    # For verification_mode == "range_threshold": inclusive bounds on the numeric at json_path (or scalar indexed root).
    range_min: float | int | None = None
    range_max: float | int | None = None


class HandoffPayload(BaseModel):
    """Handoff contract v2 — assembled by Cluster A deterministic code only."""

    model_config = ConfigDict(extra="ignore")

    provably_mcp_url: str = ""
    provably_org_id: str = ""
    integration_api_key: str = ""
    handoff_evaluate_url: str = ""
    handoff_contract_version: str = "2.0"
    handoff_field_guide: dict[str, str] = Field(default_factory=dict)
    instructions: str = ""
    query_record_ids: list[str] = Field(default_factory=list)
    trusted_endpoint_registry: list[str] = Field(default_factory=list)
    run_id: str | None = None
    claims: list[HandoffClaim] = Field(default_factory=list)
    verification_results: list[str] = Field(default_factory=list)
    query_record_urls: list[str] = Field(default_factory=list)
    task: str = ""
    reasoning: str = ""
    sdk_precheck: dict[str, Any] | None = None


class BenchmarkRow(BaseModel):
    """Dashboard benchmark row."""

    model_config = ConfigDict(extra="ignore")

    outcome: Outcome | None = None
    body_edited: bool | None = None
    proof_url_count: int | None = None
    proof_time_ms: float | None = None
    verify_time_ms: float | None = None
    endpoint_count: int | None = None
    llm_model_id: str | None = None


class HandoffProofAction(BaseModel):
    """Per-action proof metadata from Provably API (Cluster A)."""

    model_config = ConfigDict(extra="ignore")

    name: str = ""
    source_url: str = ""
    query_record_url: str = ""
    query_id: str = ""
    secret: str = ""


class HandoffProofBundle(BaseModel):
    actions: list[HandoffProofAction] = Field(default_factory=list)
    verified: bool = True
