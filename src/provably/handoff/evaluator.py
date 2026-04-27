"""Deterministic evaluation of a HandoffPayload against Provably query records."""

from __future__ import annotations

from typing import Any

import httpx

from provably.handoff.eval_modes import evaluate_claim
from provably.handoff.json_utils import canonical_json
from provably.handoff.types import HandoffClaim, HandoffPayload

__all__ = ["evaluate_handoff", "extract_indexed_from_query_record"]


_INDEXED_VALUE_KEYS = ("result", "indexed_value", "response", "raw_response", "data", "output")


def evaluate_handoff(
    payload: HandoffPayload,
    *,
    provably_base_url: str,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """Verify each claim in ``payload`` against its Provably query record.

    For each claim this fetches the canonical indexed value from Provably and runs the
    mode-specific check (see :func:`provably.handoff.eval_modes.evaluate_claim`). Network
    failures are recorded per-claim (not raised) and force ``outcome="CAUGHT"``; missing
    ``provably_org_id`` / ``integration_api_key`` short-circuits to a no-op ``PASS``.

    Args:
        payload: Handoff payload to verify.
        provably_base_url: Base URL of the Provably backend.
        timeout_s: HTTP timeout per query record fetch.

    Returns:
        ``{"outcome": "PASS"|"CAUGHT", "per_claim": [...], "errors": [...]}``.
    """
    org = payload.provably_org_id
    api_key = payload.integration_api_key
    if not org or not api_key:
        return {
            "outcome": "PASS",
            "per_claim": [],
            "errors": ["missing provably_org_id or integration_api_key - nothing to verify"],
        }

    base_url = provably_base_url.rstrip("/")
    per_claim: list[dict[str, Any]] = []
    errors: list[str] = []

    with httpx.Client(timeout=timeout_s) as client:
        for claim in payload.claims:
            query_record_id = (claim.query_record_id or "").strip()
            if not query_record_id:
                per_claim.append(_caught(claim, "missing query_record_id"))
                continue
            try:
                record = _fetch_query_record(client, base_url, org, query_record_id, api_key)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{claim.action_name}: {exc}")
                per_claim.append(_caught(claim, str(exc)))
                continue
            per_claim.append(evaluate_claim(claim, extract_indexed_from_query_record(record)))

    outcome = "CAUGHT" if any(entry.get("result") == "CAUGHT" for entry in per_claim) else "PASS"
    return {"outcome": outcome, "per_claim": per_claim, "errors": errors}


def extract_indexed_from_query_record(record: dict[str, Any]) -> Any:
    """Return the indexed value from a Provably query-record JSON regardless of envelope shape.

    Tries known wrapper keys (``result`` / ``indexed_value`` / ``response`` / ``raw_response`` /
    ``data`` / ``output``), recurses through a nested ``query`` envelope, and falls back to the
    entire record so callers can still attempt a verbatim compare.
    """
    for key in _INDEXED_VALUE_KEYS:
        value = record.get(key)
        if value is not None:
            return value
    inner = record.get("query")
    if isinstance(inner, dict):
        return extract_indexed_from_query_record(inner)
    return record


def _fetch_query_record(
    client: httpx.Client,
    base_url: str,
    org_id: str,
    query_record_id: str,
    api_key: str,
) -> dict[str, Any]:
    url = f"{base_url}/api/v1/organizations/{org_id}/queries/{query_record_id}"
    response = client.get(url, headers={"x-api-key": api_key, "Content-Type": "application/json"})
    response.raise_for_status()
    data = response.json() if response.text else {}
    return data if isinstance(data, dict) else {}


def _caught(claim: HandoffClaim, detail: str) -> dict[str, Any]:
    return {
        "action_name": claim.action_name,
        "verification_mode": claim.verification_mode,
        "result": "CAUGHT",
        "claimed": canonical_json(claim.claimed_value),
        "indexed": "",
        "detail": detail,
    }
