import uuid
from collections.abc import Mapping
from typing import Any

from agentkit.bootstrap import get_bootstrap
from agentkit.config import get_settings
from agentkit.handoff._query_records import create_query_record_for_intercept
from agentkit.handoff.guide import default_instructions, field_descriptions
from agentkit.intercept import get_intercept_row_id, load_latest_intercept_payload
from agentkit.logger import get_logger
from agentkit.schemas.handoff import HandoffClaim, HandoffPayload, VerificationMode
from agentkit.trusted_endpoints.trusted_endpoints import list_all_trusted_endpoints

_log = get_logger(__name__)

DEFAULT_HANDOFF_TASK: str = "Handoff verification via evaluate_url."


async def build_handoff_payload(
    fetch_and_claim: Mapping[str, Any] | dict[str, Any] | None,
    *,
    run_id: uuid.UUID | None = None,
    task: str = DEFAULT_HANDOFF_TASK,
    intercept_agent_id: str = "fetch_and_claim",
    field_guide: dict[str, str] | None = None,
    instructions: str | None = None,
) -> HandoffPayload:
    """Builds the complete signed metadata payload container for external verification runs."""

    # Verify that Provably bootstrapping sequence successfully cleared
    provably = get_bootstrap()
    if not provably.integration_key:
        raise RuntimeError("Provably infrastructure bootstrapping incomplete or uninitialized.")

    blob: dict[str, Any] = dict(fetch_and_claim) if fetch_and_claim else {}

    # Extract and resolve claim arrays
    claims, query_urls, query_ids = await _build_claims(
        blob,
        intercept_agent_id,
    )

    reasoning = str(blob.get("reasoning") or "")
    settings = get_settings()

    # Determine guide structures cleanly using ternary operators
    guide = field_guide if field_guide is not None else field_descriptions()
    instr = instructions if instructions is not None else default_instructions()

    trusted_endpoint_registry = await list_all_trusted_endpoints()

    return HandoffPayload(
        provably_mcp_url=settings.provably_mcp,
        provably_org_id=settings.org_id,
        integration_api_key=provably.integration_key,
        evaluate_url="",  # TODO: to be added after a2a communication management
        field_guide=guide,
        instructions=instr,
        query_ids=query_ids,
        trusted_endpoint_registry=trusted_endpoint_registry,
        run_id=run_id,
        claims=claims,
        verification_results=[],
        query_urls=query_urls,
        task=task,
        reasoning=reasoning,
    )


async def _build_claims(
    fetch_and_claim_json: Any,
    intercept_agent_id: str,
) -> tuple[list[HandoffClaim], list[str], list[uuid.UUID]]:
    """Aggregates, resolves intercept IDs, and emits tracking metadata."""

    if not isinstance(fetch_and_claim_json, dict):
        return [], [], []

    raw_claims = fetch_and_claim_json.get("claims")
    if not isinstance(raw_claims, list):
        return [], [], []

    claims: list[HandoffClaim] = []
    urls: list[str] = []
    ids: list[uuid.UUID] = []

    for raw in raw_claims:
        if not isinstance(raw, dict):
            continue

        action_name = str(raw.get("action_name") or "").strip()
        if not action_name:
            continue

        # Fetch underlying response blobs
        request_payload, response_payload = await load_latest_intercept_payload(intercept_agent_id, action_name)
        row_id = get_intercept_row_id(intercept_agent_id, action_name)

        # Resolve tracking handles
        qid, qurl = await create_query_record_for_intercept(
            action_name,
            agent_id=intercept_agent_id,
            row_id=row_id,
        )

        ids.append(qid)
        urls.append(qurl)

        # Coerce verification mode dynamically using Enum
        mode_raw = str(raw.get("verification_mode") or "").strip()
        try:
            verification_mode = VerificationMode(mode_raw)
        except ValueError:
            verification_mode = VerificationMode.VERBATIM

        # Build and append model contract
        schema = raw.get("expected_json_schema") if isinstance(raw.get("expected_json_schema"), dict) else None

        claims.append(
            HandoffClaim(
                action_name=action_name,
                claimed_value=raw.get("claimed_value"),
                request_payload=request_payload,
                response_payload=response_payload,
                query_id=qid,
                verification_mode=verification_mode,
                json_path=str(raw.get("json_path") or ""),
                expected_json_schema=schema,
                range_min=raw.get("range_min"),
                range_max=raw.get("range_max"),
            )
        )

    return claims, urls, ids
