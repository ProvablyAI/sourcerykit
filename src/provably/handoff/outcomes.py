from __future__ import annotations

from typing import Any, cast

from provably.handoff.types import HandoffPayload, Outcome

__all__ = ["aggregate_outcome", "outcome_from_trace"]


def outcome_from_trace(trace: dict[str, Any] | None) -> Outcome | None:
    if not trace:
        return None
    value = trace.get("outcome")
    if value in ("PASS", "CAUGHT"):
        return cast(Outcome, value)
    return None


def aggregate_outcome(payload: HandoffPayload) -> Outcome:
    if payload.verification_results and any(x == "CAUGHT" for x in payload.verification_results):
        return "CAUGHT"
    return "PASS"
