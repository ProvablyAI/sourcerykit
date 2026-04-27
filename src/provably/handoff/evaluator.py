"""Deterministic evaluation of a HandoffPayload against Provably query records."""

from __future__ import annotations

from typing import Any

import httpx

from provably.handoff.eval_modes import evaluate_claim
from provably.handoff.json_utils import canonical_json
from provably.handoff.types import HandoffClaim, HandoffPayload
from provably.trusted_endpoints import check_claim_endpoints_are_trusted

__all__ = ["evaluate_handoff", "extract_indexed_from_query_record"]


_INDEXED_VALUE_KEYS = ("result", "indexed_value", "response", "raw_response", "data", "output")


def evaluate_handoff(
    payload: HandoffPayload,
    *,
    provably_base_url: str = "",
    postgres_url: str = "",
    org_id_fallback: str = "",
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """Run the trusted-endpoint gate, then verify each claim against its Provably query record.

    The trust gate runs first and trips the whole handoff to ``CAUGHT`` if any claim's
    ``request_payload.url`` is missing from the active registry; payloads with no URLs skip it.
    Past the gate, each claim is checked per its ``verification_mode`` against the canonical
    indexed value fetched from Provably. Config errors (missing base URL / org / credentials,
    trust-gate failure) are returned as structured results, never raised — callers can treat
    this as a total function and route on ``outcome``.

    Args:
        payload: Handoff payload to verify.
        provably_base_url: Base URL of the Provably backend; empty short-circuits to CAUGHT.
        postgres_url: DSN for the trust-gate lookup; required when any claim carries a URL.
        org_id_fallback: Used only when ``payload.provably_org_id`` is empty.
        timeout_s: HTTP timeout per query record fetch.

    Returns:
        ``{"outcome": "PASS"|"CAUGHT", "per_claim": [...], "errors": [...]}``. On a trust-gate
        trip ``per_claim`` is empty and ``errors[0]`` carries the reason.
    """
    try:
        check_claim_endpoints_are_trusted(
            payload,
            postgres_url=postgres_url,
            org_id_fallback=org_id_fallback,
        )
    except (ValueError, RuntimeError) as exc:
        return {
            "outcome": "CAUGHT",
            "per_claim": [],
            "errors": [f"trust gate: {exc}"],
        }

    if not provably_base_url:
        return {
            "outcome": "CAUGHT",
            "per_claim": [],
            "errors": ["provably_base_url not set"],
        }

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
    """Return the indexed value out of a Provably query-record JSON, regardless of envelope shape.

    The Provably API has historically wrapped the indexed value under several names
    (``result`` / ``indexed_value`` / ``response`` / ``raw_response`` / ``data`` / ``output``),
    sometimes nested under a ``query`` key. This helper picks the first known field present and
    recurses through the ``query`` envelope; if nothing matches, the entire record is returned
    so the caller can still attempt a verbatim compare.
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
