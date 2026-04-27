"""Create Provably query records (with proof) over ``provably_intercepts``.

This is the SDK-side counterpart to the Rust open endpoints:

* ``POST /middlewares/{mw}/query``       — execute SQL, ``require_proof=true``
* ``POST /queries/{id}/generate_proof``  — kick proof generation
* ``GET  /queries/{id}``                 — poll until ``proof.status == "completed"``

Verification is *not* done here: per the agreed contract, the only end-to-end ``/verify``
call in the system is fired by the evaluator on the receiving side (cluster B) as the
final step of :func:`provably.handoff.evaluator.evaluate_handoff`. Cluster A only
provisions the proof so the evaluator has something to verify.

The handoff payload builder calls :func:`create_query_record_for_intercept` once per
claim so each claim carries a ``query_record_id`` whose proof binds the SQL truth that
the evaluator (and the dashboard) compares against the LLM's claim.
"""

from __future__ import annotations

from provably.handoff._http import org_id as env_org_id
from provably.handoff._http import post_json, query_record_page_url
from provably.handoff._preprocess import wait_for_proof_completed
from provably.handoff._resources import extract_id
from provably.log import get_logger

_log = get_logger(__name__)


def _sql_escape(s: str) -> str:
    return s.replace("'", "''")


def create_query_record_for_intercept(
    action_name: str,
    *,
    agent_id: str,
    middleware_id: str,
    collection_id: str,
    org_id: str | None = None,
    row_id: int | None = None,
    proof_timeout_s: float = 180.0,
) -> tuple[str, str]:
    """Run SQL over ``provably_intercepts`` and wait for a Completed proof (no verify).

    Provably's query engine supports only single-column filters (``=``, ``<``, ``>``, etc.);
    ``AND`` and string-function operators are rejected. To uniquely address a row we prefer
    ``WHERE id = {row_id}`` (integer PK). When ``row_id`` is not supplied we fall back to
    ``WHERE action_name = '{action_name}'``, which is sufficient for action names that are
    unique within the collection.

    The function returns as soon as ``proof.status == "completed"`` so the receiving side
    (the evaluator) can perform the final ``/verify`` call as the last step of evaluation.

    Args:
        action_name: Recorded in ``provably_intercepts.action_name`` by the interceptor.
        agent_id: Recorded in ``provably_intercepts.agent_id`` by the interceptor.
        middleware_id: Provably middleware UUID (from the bootstrap cache).
        collection_id: Provably collection UUID for the intercepts table.
        org_id: Provably organization UUID; falls back to ``PROVABLY_ORG_ID`` when omitted.
        row_id: Integer PK of the specific ``provably_intercepts`` row; preferred over
            name-based fallback because it is always unique.
        proof_timeout_s: How long to wait for ``proof.status == "completed"``.

    Returns:
        ``(query_id, query_record_url)`` — the URL is a Provably *app* deep-link when
        ``PROVABLY_APP_UI_URL`` is set; the evaluator still fetches the record over the JSON API.

    Raises:
        ValueError: ``agent_id`` / ``action_name`` / ``middleware_id`` / ``collection_id`` empty.
    """
    a = (agent_id or "").strip()
    b = (action_name or "").strip()
    if not a or not b:
        raise ValueError("create_query_record_for_intercept requires non-empty agent_id and action_name")

    oid = (org_id or env_org_id()).strip()
    if not oid or not middleware_id or not collection_id:
        raise ValueError(
            "create_query_record_for_intercept requires org_id, middleware_id, collection_id"
        )

    if row_id is not None:
        # Single integer equality — accepted by all Provably engine versions.
        sql = f"SELECT * FROM provably_intercepts WHERE id = {int(row_id)}"
    else:
        # Fallback: filter by action_name alone (unique per run in the demo setup).
        sql = f"SELECT * FROM provably_intercepts WHERE action_name = '{_sql_escape(b)}'"
    query_rec = post_json(
        f"/api/v1/organizations/{oid}/middlewares/{middleware_id}/query",
        {"query": sql, "require_proof": True, "collection_id": collection_id},
    )
    query_id = extract_id(query_rec if isinstance(query_rec, dict) else {}, ["query_id", "id"])

    post_json(f"/api/v1/organizations/{oid}/queries/{query_id}/generate_proof", {})
    wait_for_proof_completed(oid, query_id, timeout_s=proof_timeout_s)

    url = query_record_page_url(oid, query_id)
    _log.info("query_record_created", action_name=action_name, agent_id=agent_id, query_id=query_id)
    return query_id, url


__all__ = ["create_query_record_for_intercept"]
