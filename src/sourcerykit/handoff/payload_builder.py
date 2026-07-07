import asyncio
import uuid
from collections.abc import Mapping
from typing import Any

from sourcerykit.bootstrap.bootstrap import get_bootstrap
from sourcerykit.config import get_settings
from sourcerykit.db._engine import get_engine
from sourcerykit.db._traces import insert_trace, insert_trace_intercept
from sourcerykit.errors import SourceryKitStorageError
from sourcerykit.handoff._guide import default_instructions, field_descriptions
from sourcerykit.handoff._query_records import create_query_record_for_intercept
from sourcerykit.intercept._loader import load_intercept_payload_by_call_ref
from sourcerykit.logger import get_logger
from sourcerykit.schemas.handoff import HandoffClaim, HandoffPayload
from sourcerykit.schemas.verification_mode import VerificationMode
from sourcerykit.trusted_endpoints.service import list_all_trusted_endpoints

_log = get_logger(__name__)

DEFAULT_HANDOFF_TASK: str = "Handoff verification via evaluate_url."


async def build_handoff_payload(
    fetch_and_claim: Mapping[str, Any] | dict[str, Any] | None,
    *,
    run_id: uuid.UUID | None = None,
    prompt: str,
    task: str = DEFAULT_HANDOFF_TASK,
    intercept_agent_id: str = "fetch_and_claim",
    field_guide: dict[str, str] | None = None,
    instructions: str | None = None,
) -> HandoffPayload:
    """Builds the complete signed metadata payload container for external verification runs."""

    _log.info("build_handoff_payload_started")
    # Verify that Provably bootstrapping sequence successfully cleared
    provably = get_bootstrap()
    if not provably.integration_key:
        raise RuntimeError("Provably infrastructure bootstrapping incomplete or uninitialized.")

    # insert trace
    try:
        async with get_engine().begin() as conn:
            result = await conn.execute(insert_trace(prompt))
            trace_id: uuid.UUID | None = result.scalar()

            if trace_id is None:
                raise SourceryKitStorageError("Database did not return a valid UUID")
    except Exception as e:
        _log.error("build_handoff_payload", error=str(e))
        raise SourceryKitStorageError("Failed to store agent trace") from e

    blob: dict[str, Any] = dict(fetch_and_claim) if fetch_and_claim else {}

    reasoning = str(blob.get("reasoning") or "")
    settings = get_settings()

    # Determine guide structures cleanly using ternary operators
    guide = field_guide if field_guide is not None else field_descriptions()
    instr = instructions if instructions is not None else default_instructions()

    # Run claim resolution and trusted-endpoint fetch concurrently
    (claims, query_urls, query_ids), trusted_endpoint_registry = await asyncio.gather(
        _build_claims(trace_id, blob, intercept_agent_id),
        list_all_trusted_endpoints(),
    )

    _log.info("build_handoff_payload_completed", claim_count=len(claims))

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
    trace_id: uuid.UUID,
    fetch_and_claim_json: Any,
    intercept_agent_id: str,
) -> tuple[list[HandoffClaim], list[str], list[uuid.UUID]]:
    """Aggregates, resolves intercept IDs, and emits tracking metadata."""

    if not isinstance(fetch_and_claim_json, dict):
        return [], [], []

    raw_claims = fetch_and_claim_json.get("claims")
    if not isinstance(raw_claims, list):
        return [], [], []

    # Filter to valid claim dicts up-front
    valid_raws = [raw for raw in raw_claims if isinstance(raw, dict) and str(raw.get("action_name") or "").strip()]

    results = await asyncio.gather(
        *[_resolve_claim(trace_id, raw, intercept_agent_id) for raw in valid_raws],
        return_exceptions=True,
    )

    claims = []
    urls = []
    ids = []
    for raw, r in zip(valid_raws, results):
        if isinstance(r, BaseException):
            _log.warning(
                "claim_resolution_failed",
                action_name=raw.get("action_name"),
                error=str(r),
            )
            continue
        claims.append(r[0])
        urls.append(r[1])
        ids.append(r[2])

    return claims, urls, ids


async def _resolve_claim(
    trace_id: uuid.UUID,
    raw: dict[str, Any],
    intercept_agent_id: str,
) -> tuple[HandoffClaim, str, uuid.UUID]:
    """Resolves a single raw claim dict into a HandoffClaim plus its tracking handles."""
    action_name = str(raw.get("action_name") or "").strip()
    call_ref_str = str(raw.get("call_ref") or "").strip()

    if not call_ref_str:
        raise SourceryKitStorageError("claim missing required call_ref")

    call_ref = uuid.UUID(call_ref_str)
    (request_payload, response_payload, row_id), (qid, qurl) = await asyncio.gather(
        load_intercept_payload_by_call_ref(call_ref),
        create_query_record_for_intercept(action_name, agent_id=intercept_agent_id, call_ref=call_ref),
    )

    # Coerce verification mode dynamically using Enum
    mode_raw = str(raw.get("verification_mode") or "").strip()
    try:
        verification_mode = VerificationMode(mode_raw)
    except ValueError:
        verification_mode = VerificationMode.FIELD_EXTRACTION

    schema = raw.get("expected_json_schema") if isinstance(raw.get("expected_json_schema"), dict) else None

    claimed_value = raw.get("claimed_value")

    # insert trace_intercept
    try:
        async with get_engine().begin() as conn:
            result = await conn.execute(insert_trace_intercept(trace_id, row_id, qid, verification_mode, claimed_value))
            trace_intercept_id: uuid.UUID | None = result.scalar()

            if trace_intercept_id is None:
                raise SourceryKitStorageError("Database did not return a valid UUID")
    except Exception as e:
        _log.error("_resolve_claim", error=str(e))
        raise SourceryKitStorageError("Failed to store agent trace_intercept") from e

    claim = HandoffClaim(
        trace_intercept_id=trace_intercept_id,
        action_name=action_name,
        call_ref=call_ref_str,
        claimed_value=claimed_value,
        request_payload=request_payload,
        response_payload=response_payload,
        query_id=qid,
        verification_mode=verification_mode,
        json_path=str(raw.get("json_path") or ""),
        expected_json_schema=schema,
        range_min=raw.get("range_min"),
        range_max=raw.get("range_max"),
    )
    return claim, qurl, qid
