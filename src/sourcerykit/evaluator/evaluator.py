import asyncio
import uuid
from typing import Any

from sourcerykit.config import get_settings
from sourcerykit.db._engine import get_engine
from sourcerykit.db._traces import update_trace_intercept_outcome
from sourcerykit.errors import SourceryKitError, SourceryKitStorageError
from sourcerykit.evaluator._eval_modes import evaluate_claim
from sourcerykit.intercept._self_egress import provably_self_egress
from sourcerykit.logger import get_logger
from sourcerykit.provably._answer_model import QueryAnswer
from sourcerykit.provably.service import service
from sourcerykit.schemas import HandoffPayload, Outcome
from sourcerykit.trusted_endpoints.service import verify_claim_endpoints

_log = get_logger(__name__)


async def evaluate_handoff(*, payload: HandoffPayload) -> dict[str, Any]:
    """Validates trusted endpoints and verifies cryptographic proof loops for all payload claims."""

    # TODO: Refactor.
    # Not a good idea to pass the API key via the payload (api_key = payload.integration_api_key)
    # Use a new generated integration apikey with limited access
    api_key = get_settings().api_key

    query_ids = [claim.query_id for claim in payload.claims]

    try:
        with provably_self_egress():
            # Overlap the endpoint trust check (DB) with proof verification submission (HTTP)
            await asyncio.gather(
                verify_claim_endpoints(payload),
                asyncio.gather(*(service.verify_proof(qid, api_key) for qid in query_ids)),
            )
    except (ValueError, SourceryKitError) as e:
        return {"outcome": Outcome.CAUGHT, "per_claim": [], "errors": [f"trust gate: {e}"]}

    per_claim: list[dict[str, Any]] = []
    errors: list[str] = []

    with provably_self_egress():
        # Wait for all proof verifications concurrently
        verification_results = await asyncio.gather(
            *(service.wait_for_proof_verification(qid, api_key) for qid in query_ids),
            return_exceptions=True,
        )

    for claim, result in zip(payload.claims, verification_results):
        if isinstance(result, BaseException):
            _log.exception("failed_to_verify_claim_proof", query_id=claim.query_id)
            error = f"verification_failed: {str(result)}"
            errors.append(error)
            await update_trace(claim.trace_intercept_id, Outcome.CAUGHT, error)
            continue

        coerced_val = _coerce_query_result_to_indexed_value(result.get("result"))
        eval_result = evaluate_claim(claim, coerced_val)

        await update_trace(
            trace_intercept_id=claim.trace_intercept_id,
            outcome=Outcome(eval_result.get("result") or Outcome.ERROR),
            detail=str(eval_result.get("detail") or ""),
        )

        verdict = {
            **eval_result,
            "query_id": str(claim.query_id),
            **_extract_timings(result),
        }
        per_claim.append(verdict)

    # Claims dropped while building the payload never reach the verifier above. Surface those
    # reasons — otherwise a payload that arrives with zero claims is an ERROR with no
    # explanation of what went wrong.
    errors = list(payload.build_errors) + errors

    outcome = _resolve_outcome(per_claim, errors)

    if outcome == Outcome.ERROR and not per_claim and not errors:
        errors = [
            f"no claims were verified: the handoff payload contained {len(payload.claims)} "
            "claim(s), and none resolved to a recorded intercept. Check that each claimed "
            "value carries a sourcerykit_ref matching a recorded tool call."
        ]

    return {"outcome": outcome, "per_claim": per_claim, "errors": errors}


def _resolve_outcome(per_claim: list[dict[str, Any]], errors: list[str]) -> str:
    """Computes the overall payload resolution state based on individual claim verdicts."""
    if errors:
        return Outcome.ERROR
    if not per_claim:
        # Nothing was verified — no claim reached the verifier. Verifying ZERO claims must
        # never be reported as PASS; that would silently rubber-stamp an unverified handoff.
        return Outcome.ERROR
    results = {str(c.get("result") or "").upper() for c in per_claim}
    if Outcome.CAUGHT in results:
        return Outcome.CAUGHT
    if Outcome.ERROR in results:
        return Outcome.ERROR
    return Outcome.PASS


def _coerce_query_result_to_indexed_value(value: Any) -> Any:
    """Flattens QueryAnswer structure via deserialization."""
    try:
        return QueryAnswer.model_validate(value).flatten()
    except Exception as e:
        _log.debug("coerce_query_result_fallback", error=str(e))
        return value


def _extract_timings(record: dict[str, Any]) -> dict[str, float]:
    """Extracts performance metrics from the direct proof envelope."""
    proof = (record or {}).get("proof") or {}

    return {
        "proof_time_ms": float(proof.get("execution_time_ms") or 0.0),
        "verify_time_ms": float(proof.get("verification_time_ms") or 0.0),
    }


async def update_trace(trace_intercept_id: uuid.UUID, outcome: Outcome, detail: str) -> None:
    try:
        async with get_engine().begin() as conn:
            await conn.execute(update_trace_intercept_outcome(trace_intercept_id, outcome, detail))
    except Exception as e:
        _log.error("_resolve_claim", error=str(e))
        raise SourceryKitStorageError("Failed to store agent trace_intercept") from e
