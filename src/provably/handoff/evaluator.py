"""Deterministic evaluation of a HandoffPayload against Provably query records.

The evaluator (cluster B) is the *only* place ``POST /queries/{id}/verify`` is fired in the
system: cluster A merely provisions the proof (``/query`` + ``/generate_proof`` + wait).
This keeps the cryptographic verification at the receiving boundary, where it belongs.

Outcome semantics:

* ``PASS``   — every claim's content matches its proven indexed value *and* every proof
  verified end-to-end on Provably.
* ``CAUGHT`` — at least one claim's content disagrees with the proven indexed value, or a
  proof fails end-to-end verification (cryptographic mismatch).
* ``ERROR``  — the evaluator could not actually evaluate (missing ``query_record_id`` on a
  claim, missing infra config, network failures fetching a query record). This is *not*
  evidence of tampering and must not be conflated with ``CAUGHT``.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from provably.handoff.eval_modes import evaluate_claim
from provably.handoff.json_utils import canonical_json
from provably.handoff.types import HandoffClaim, HandoffPayload
from provably.intercept._self_egress import provably_self_egress
from provably.log import get_logger
from provably.trusted_endpoints import check_claim_endpoints_are_trusted

__all__ = ["evaluate_handoff", "extract_indexed_from_query_record"]

_log = get_logger(__name__)

_INDEXED_VALUE_KEYS = ("result", "indexed_value", "response", "raw_response", "data", "output")


def evaluate_handoff(
    payload: HandoffPayload,
    *,
    provably_base_url: str = "",
    postgres_url: str = "",
    org_id_fallback: str = "",
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """Run the trust gate, compare each claim, then verify each proof end-to-end.

    Phases (in order):

    1. **Trust gate** — any claim URL outside the registry trips the whole run to ``CAUGHT``.
    2. **Compare** — fetch each claim's query record, extract the indexed value, run
       ``verification_mode`` against the LLM's claim. Record TPT (``proof_time_ms``).
    3. **Verify** — final step, deduped per ``query_record_id``: ``POST /queries/{id}/verify``
       on the Rust BE; on success, refetch the record so TVT (``verify_time_ms``) is populated
       on every per-claim entry that referenced that ``query_record_id``.

    Outcome resolution: any ``CAUGHT`` per-claim ⇒ ``CAUGHT``; otherwise any ``ERROR``
    per-claim (or a verify failure) ⇒ ``ERROR``; otherwise ``PASS``.

    Config errors (missing base URL / org / credentials, trust-gate failure) are returned
    as structured results, never raised — callers can treat this as a total function and
    route on ``outcome``.

    Args:
        payload: Handoff payload to verify.
        provably_base_url: Base URL of the Provably backend; empty short-circuits to ``ERROR``.
        postgres_url: DSN for the trust-gate lookup; required when any claim carries a URL.
        org_id_fallback: Used only when ``payload.provably_org_id`` is empty.
        timeout_s: HTTP timeout for each fetch / verify call.

    Returns:
        ``{"outcome": "PASS"|"CAUGHT"|"ERROR", "per_claim": [...], "errors": [...]}``.
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
            "outcome": "ERROR",
            "per_claim": [],
            "errors": ["provably_base_url not set"],
        }

    org = payload.provably_org_id
    api_key = payload.integration_api_key
    if not org or not api_key:
        # Provably indexing was off for this payload — nothing to verify, not an infra error.
        return {
            "outcome": "PASS",
            "per_claim": [],
            "errors": ["missing provably_org_id or integration_api_key - nothing to verify"],
        }

    base_url = provably_base_url.rstrip("/")
    per_claim: list[dict[str, Any]] = []
    errors: list[str] = []

    with provably_self_egress():
        with httpx.Client(timeout=timeout_s) as client:
            # Phase 1+2: per-claim compare; capture TPT (TVT comes after verify in phase 3).
            for claim in payload.claims:
                query_record_id = (claim.query_record_id or "").strip()
                if not query_record_id:
                    err = "missing query_record_id"
                    errors.append(f"{claim.action_name}: {err}")
                    per_claim.append(_error(claim, err))
                    continue
                try:
                    record = _fetch_query_record(client, base_url, org, query_record_id, api_key)
                except Exception as exc:  # noqa: BLE001
                    # Record exists (we have a query_record_id) but can't be fetched — treat as
                    # unverifiable (suspicious), not a plain infra/setup error.
                    errors.append(f"{claim.action_name}: fetch failed: {exc}")
                    per_claim.append(_caught_verdict(claim, f"fetch failed: {exc}"))
                    continue
                verdict = evaluate_claim(claim, extract_indexed_from_query_record(record))
                verdict["query_record_id"] = query_record_id
                timing = _timing_from_query_record(record)
                if timing:
                    verdict = {**verdict, **timing}
                per_claim.append(verdict)

            # Phase 3 (final): /verify each unique query_record_id and refresh TVT timing.
            _verify_and_refresh_timings(
                client=client,
                base_url=base_url,
                org=org,
                api_key=api_key,
                payload=payload,
                per_claim=per_claim,
                errors=errors,
            )

    return {"outcome": _resolve_outcome(per_claim), "per_claim": per_claim, "errors": errors}


def _resolve_outcome(per_claim: list[dict[str, Any]]) -> str:
    results = [str(entry.get("result") or "").upper() for entry in per_claim]
    if any(r == "CAUGHT" for r in results):
        return "CAUGHT"
    if any(r == "ERROR" for r in results):
        return "ERROR"
    return "PASS"


def _verify_and_refresh_timings(
    *,
    client: httpx.Client,
    base_url: str,
    org: str,
    api_key: str,
    payload: HandoffPayload,
    per_claim: list[dict[str, Any]],
    errors: list[str],
) -> None:
    """End-to-end verify each unique ``query_record_id`` (final evaluation step).

    A verify failure flips every per-claim entry that referenced that ``query_record_id``
    to ``CAUGHT`` (proof did not validate ⇒ cannot trust the indexed value). On success we
    refetch the record once so ``verify_time_ms`` (TVT) propagates to those entries.
    """
    by_qrid: dict[str, list[int]] = {}
    for i, claim in enumerate(payload.claims):
        if i >= len(per_claim):
            break
        qrid = (claim.query_record_id or "").strip()
        if not qrid:
            continue
        by_qrid.setdefault(qrid, []).append(i)

    for qrid, indices in by_qrid.items():
        try:
            _verify_query_record(client, base_url, org, qrid, api_key)
        except _VerifyServerError as exc:
            # Transient 5xx from Provably backend (e.g. 503) — cannot conclude tampering.
            errors.append(f"proof verify unavailable for {qrid}: {exc}")
            for i in indices:
                entry = per_claim[i]
                entry["result"] = "ERROR"
                entry["detail"] = f"proof verify unavailable (server error): {exc}"
            continue
        except Exception as exc:  # noqa: BLE001
            # 4xx or proof rejection — proof did not validate, treat as tampering signal.
            errors.append(f"proof verify failed for {qrid}: {exc}")
            for i in indices:
                entry = per_claim[i]
                entry["result"] = "CAUGHT"
                entry["detail"] = f"proof verify failed: {exc}"
            continue
        try:
            refreshed = _fetch_query_record(client, base_url, org, qrid, api_key)
        except Exception as exc:  # noqa: BLE001
            _log.warning("timing_refresh_failed", query_record_id=qrid, error=str(exc))
            continue
        timing = _timing_from_query_record(refreshed)
        if not timing:
            continue
        for i in indices:
            entry = per_claim[i]
            for key, value in timing.items():
                entry[key] = value


_VERIFY_TRANSIENT_STATUS = {429, 500, 502, 503, 504}
_VERIFY_MAX_RETRIES = 3
_VERIFY_RETRY_BACKOFF = (2.0, 5.0, 10.0)


class _VerifyServerError(RuntimeError):
    """Raised when the /verify endpoint returns a transient 5xx after all retries."""


def _verify_query_record(
    client: httpx.Client,
    base_url: str,
    org_id: str,
    query_record_id: str,
    api_key: str,
) -> None:
    """POST /verify with retry on transient server errors.

    * **5xx / 429** after ``_VERIFY_MAX_RETRIES`` → raises :class:`_VerifyServerError`
      (treated as ``ERROR`` — cannot conclude tampering from a server outage).
    * **4xx** (proof rejection / not-found) → raises ``httpx.HTTPStatusError``
      (caller maps to ``CAUGHT`` — proof did not validate).
    """
    url = f"{base_url}/api/v1/organizations/{org_id}/queries/{query_record_id}/verify"
    last_exc: Exception | None = None
    for attempt, wait in enumerate((*_VERIFY_RETRY_BACKOFF, None)):
        response = client.post(url, headers={"x-api-key": api_key, "Content-Type": "application/json"}, json={})
        if response.status_code not in _VERIFY_TRANSIENT_STATUS:
            response.raise_for_status()
            return
        last_exc = httpx.HTTPStatusError(
            f"Server error '{response.status_code} {response.reason_phrase}' for url '{url}'",
            request=response.request,
            response=response,
        )
        _log.warning(
            "verify_transient_error",
            query_record_id=query_record_id,
            status=response.status_code,
            attempt=attempt + 1,
        )
        if wait is not None:
            time.sleep(wait)
    raise _VerifyServerError(str(last_exc)) from last_exc


def _coerce_query_result_to_indexed_value(value: Any) -> Any:
    """Unwrap ``QueryAnswer``-shaped results from the Rust API.

    For SQL over ``provably_intercepts``, the wire response is often a *resultset* whose
    ``raw_response`` cell holds the same JSON the HTTP interceptor stored. The public API
    still exposes the tabular shape; this pulls out the provably-intercept body so
    *verbatim* claims (and query-id resolution) can compare to ``provably_intercepts``."""
    if not isinstance(value, dict):
        return value
    t = str(value.get("type") or "").lower()
    if t == "resultset" and isinstance(value.get("value"), dict):
        table = value["value"]
        cols = table.get("columns")
        rowss = table.get("rows")
        if not isinstance(cols, list) or not isinstance(rowss, list) or not rowss:
            return value
        row0 = rowss[0]
        if not isinstance(row0, list):
            return value
        names: list[str] = []
        for c in cols:
            if isinstance(c, dict) and c.get("name") is not None:
                names.append(str(c.get("name", "")).lower())
            else:
                names.append("")
        for j, name in enumerate(names):
            if name == "raw_response" and j < len(row0):
                return _parse_jsonish_cell(row0[j])
        if len(cols) == 1 and len(row0) == 1:
            return _parse_jsonish_cell(row0[0])
        return value
    if t == "aggregate" and "value" in value:
        v = value.get("value")
        if isinstance(v, str) and v.strip()[:1] in "{[":
            try:
                return json.loads(v)
            except Exception:  # noqa: BLE001
                return v
        return v
    return value


def _parse_jsonish_cell(cell: Any) -> Any:
    if isinstance(cell, dict | list):
        return cell
    if isinstance(cell, str) and cell.strip()[:1] in "{[":
        try:
            return json.loads(cell)
        except Exception:  # noqa: BLE001
            return cell
    return cell


def extract_indexed_from_query_record(record: dict[str, Any]) -> Any:
    """Return the indexed value out of a Provably query-record JSON, regardless of envelope shape.

    The Provably API has historically wrapped the indexed value under several names
    (``result`` / ``indexed_value`` / ``response`` / ``raw_response`` / ``data`` / ``output``),
    sometimes nested under a ``query`` key. This helper picks the first known field present and
    recurses through the ``query`` envelope; if nothing matches, the entire record is returned
    so the caller can still attempt a verbatim compare.

    When the ``result`` is a Rust *resultset* over ``provably_intercepts`` (``type: resultset``),
    the HTTP body to verify is taken from the ``raw_response`` column (or a single cell), not the
    whole tabular wrapper.
    """
    for key in _INDEXED_VALUE_KEYS:
        v = record.get(key)
        if v is not None:
            return _coerce_query_result_to_indexed_value(v)
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


def _timing_from_query_record(record: dict[str, Any]) -> dict[str, float]:
    """Map query-record fields from the Rust backend to ``proof_time_ms`` / ``verify_time_ms``.

    The Rust API nests timings under a ``proof`` object (``proof.execution_time_ms``,
    ``proof.verification_time_ms``); older shapes occasionally placed them at the top level
    or under a ``query`` envelope. This recursively walks both shapes and normalizes so the
    dashboard can sum TPT/TVT per claim.
    """
    out: dict[str, float] = {}

    proof_keys = (
        "proof_time_ms",
        "execution_time_ms",
        "proof_generation_time_ms",
        "executionTimeMs",
        "proofGenerationTimeMs",
    )
    verify_keys = (
        "verify_time_ms",
        "verification_time_ms",
        "verifyTimeMs",
        "verificationTimeMs",
    )
    for k in proof_keys:
        v = record.get(k)
        if isinstance(v, int | float):
            out["proof_time_ms"] = float(v)
            break
    for k in verify_keys:
        v = record.get(k)
        if isinstance(v, int | float):
            out["verify_time_ms"] = float(v)
            break

    def _merge_from(sub_record: Any) -> None:
        if not isinstance(sub_record, dict):
            return
        sub = _timing_from_query_record(sub_record)
        for key in ("proof_time_ms", "verify_time_ms"):
            if key not in out and key in sub:
                out[key] = sub[key]

    if "proof_time_ms" not in out or "verify_time_ms" not in out:
        _merge_from(record.get("proof"))
    if "proof_time_ms" not in out or "verify_time_ms" not in out:
        _merge_from(record.get("query"))
    return out


def _error(claim: HandoffClaim, detail: str) -> dict[str, Any]:
    """Per-claim entry for an evaluation that could not run (no tampering signal).

    Used when ``query_record_id`` is missing — proof was never generated, so we cannot
    honestly say ``PASS`` *or* ``CAUGHT``.
    """
    return {
        "action_name": claim.action_name,
        "verification_mode": claim.verification_mode,
        "result": "ERROR",
        "claimed": canonical_json(claim.claimed_value),
        "indexed": "",
        "detail": detail,
        "query_record_id": (claim.query_record_id or "").strip(),
    }


def _caught_verdict(claim: HandoffClaim, detail: str) -> dict[str, Any]:
    """Per-claim entry when a proof exists but cannot be fetched or verified — unverifiable =
    suspicious.  Distinct from :func:`_error` (setup/infra failure, no proof attempted).
    """
    return {
        "action_name": claim.action_name,
        "verification_mode": claim.verification_mode,
        "result": "CAUGHT",
        "claimed": canonical_json(claim.claimed_value),
        "indexed": "",
        "detail": detail,
        "query_record_id": (claim.query_record_id or "").strip(),
    }
