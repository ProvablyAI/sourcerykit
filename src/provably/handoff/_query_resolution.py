"""Resolve Rust query record UUIDs from indexed intercept truth (Provably API list + match)."""

from __future__ import annotations

import os
import time
from typing import Any

from provably.handoff._http import base_url, get_json_params, query_record_page_url
from provably.handoff.evaluator import extract_indexed_from_query_record
from provably.handoff.json_utils import canonical_json
from provably.log import get_logger

_log = get_logger(__name__)


def _wait_seconds_from_env() -> float:
    raw = (os.environ.get("PROVABLY_QUERY_RESOLVE_MAX_WAIT_S") or "").strip()
    if not raw:
        # Keep dashboard / cluster A HTTP responses snappy: handoff build runs inline.
        return 15.0
    try:
        return max(1.0, min(300.0, float(raw)))
    except ValueError:
        return 15.0


def resolve_query_record_ids_for_truths(
    truth_responses: list[Any | None],
    org_id: str,
    collection_id: str,
    *,
    max_wait_s: float | None = None,
    poll_s: float = 1.0,
) -> list[tuple[str, str]]:
    """For each non-``None`` truth (indexed response from ``provably_intercepts``), find a matching
    query record in the org/collection, by comparing canonical JSON to :func:`extract_indexed_from_query_record`.

    Each query UUID is used at most once, so multiple claims with identical bodies still match
    distinct query rows (same order as returned by the list API, newest first).

    Returns a list the same length as ``truth_responses``; each entry is ``(query_id, url)`` or
    ``("", "")`` if still unknown after the wait window.
    """
    n = len(truth_responses)
    if n == 0:
        return []
    empty: list[tuple[str, str]] = [("", "") for _ in range(n)]

    oid = (org_id or "").strip()
    cid = (collection_id or "").strip()
    if not oid or not cid:
        return empty

    try:
        base_url()
    except ValueError:
        return empty

    indices_needing: list[int] = []
    targets: list[str] = []
    for i, t in enumerate(truth_responses):
        if t is not None:
            indices_needing.append(i)
            targets.append(canonical_json(t))
    if not indices_needing:
        return empty

    wait = _wait_seconds_from_env() if max_wait_s is None else max(1.0, max_wait_s)
    path = f"/api/v1/organizations/{oid}/queries"
    params: dict[str, Any] = {
        "page": 1,
        "page_size": 100,
        "collection_ids": cid,
        "sort_by": "created_at",
        "sort_order": "desc",
    }
    out: list[tuple[str, str]] = [("", "") for _ in range(n)]
    t0 = time.monotonic()
    deadline = t0 + wait
    first = True
    consumed_ids: set[str] = set()
    # Which slot in ``indices_needing`` are still open
    while time.monotonic() < deadline:
        if not first:
            time.sleep(poll_s)
        first = False
        try:
            # Short timeout so a slow Rust list endpoint cannot block the whole wait window
            # on a single request (keeps the simulation worker from looking "stuck").
            data = get_json_params(path, params, timeout_s=12.0)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(data, list):
            continue

        for rec in data:
            if not isinstance(rec, dict):
                continue
            qid = str(rec.get("id") or "").strip()
            if not qid or qid in consumed_ids:
                continue
            cj = canonical_json(extract_indexed_from_query_record(rec))
            for slot, ti in enumerate(indices_needing):
                if out[ti][0]:
                    continue
                if cj == targets[slot]:
                    out[ti] = (qid, query_record_page_url(oid, qid))
                    consumed_ids.add(qid)
                    break
        if all(out[i][0] for i in indices_needing):
            break
    if indices_needing and not all(out[i][0] for i in indices_needing):
        _log.warning(
            "query_record_ids_unresolved",
            org_id=oid,
            collection_id=cid,
            waited_s=round(time.monotonic() - t0, 1),
        )
    return out


def resolve_query_record_id_for_intercept(
    truth_response: Any,
    org_id: str,
    collection_id: str,
    *,
    max_wait_s: float | None = None,
    poll_s: float = 2.0,
) -> tuple[str, str]:
    """Single-truth convenience wrapper around :func:`resolve_query_record_ids_for_truths`."""
    r = resolve_query_record_ids_for_truths(
        [truth_response], org_id, collection_id, max_wait_s=max_wait_s, poll_s=poll_s
    )
    return r[0] if r else ("", "")


__all__ = [
    "resolve_query_record_id_for_intercept",
    "resolve_query_record_ids_for_truths",
]
