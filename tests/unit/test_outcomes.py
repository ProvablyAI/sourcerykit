from __future__ import annotations

from provably.handoff.outcomes import aggregate_outcome, outcome_from_trace
from provably.handoff.types import HandoffPayload


def test_outcome_from_trace_pass() -> None:
    assert outcome_from_trace({"outcome": "PASS"}) == "PASS"


def test_outcome_from_trace_caught() -> None:
    assert outcome_from_trace({"outcome": "CAUGHT"}) == "CAUGHT"


def test_outcome_from_trace_unknown_outcome() -> None:
    assert outcome_from_trace({"outcome": "weird"}) is None


def test_outcome_from_trace_falsy_trace() -> None:
    assert outcome_from_trace(None) is None
    assert outcome_from_trace({}) is None


def test_aggregate_outcome_verification_results() -> None:
    assert (
        aggregate_outcome(HandoffPayload(verification_results=["PASS", "CAUGHT"]))
        == "CAUGHT"
    )
    assert aggregate_outcome(HandoffPayload(verification_results=["PASS", "PASS"])) == "PASS"
    assert aggregate_outcome(HandoffPayload(verification_results=[])) == "PASS"
    assert aggregate_outcome(HandoffPayload()) == "PASS"
