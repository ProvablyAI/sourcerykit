import asyncio
from typing import Any

from agentkit.config import get_settings
from agentkit.errors import AgentKitError
from agentkit.evaluator.eval_modes import evaluate_claim
from agentkit.intercept._self_egress import provably_self_egress
from agentkit.logger import get_logger
from agentkit.provably.answer_model import QueryAnswer
from agentkit.provably.service import service
from agentkit.schemas import HandoffPayload, Outcome
from agentkit.trusted_endpoints.service import verify_claim_endpoints

_log = get_logger(__name__)


async def evaluate_handoff(payload: HandoffPayload) -> dict[str, Any]:
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
    except (ValueError, AgentKitError) as e:
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
            errors.append(f"verification_failed: {str(result)}")
            continue

        coerced_val = _coerce_query_result_to_indexed_value(result.get("result"))
        verdict = {
            **evaluate_claim(claim, coerced_val),
            "query_id": str(claim.query_id),
            **_extract_timings(result),
        }
        per_claim.append(verdict)

    return {"outcome": _resolve_outcome(per_claim, errors), "per_claim": per_claim, "errors": errors}


def _resolve_outcome(per_claim: list[dict[str, Any]], errors: list[str]) -> str:
    """Computes the overall payload resolution state based on individual claim verdicts."""
    if errors:
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
