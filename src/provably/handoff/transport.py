from __future__ import annotations

import os

import httpx

from provably.handoff.types import HandoffPayload
from provably.intercept._self_egress import provably_self_egress
from provably.log import get_logger

_log = get_logger(__name__)


def post_handoff(
    cluster_b_url: str,
    handoff_payload: HandoffPayload,
    *,
    headers: dict[str, str] | None = None,
    timeout_s: float = 120.0,
) -> None:
    base = (cluster_b_url or "").strip().rstrip("/")
    if not base:
        raise ValueError("cluster_b_url is empty — set CLUSTER_B_URL to post handoff")
    url = f"{base}/handoffs/receive"
    body = handoff_payload.model_dump(mode="json")
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    try:
        with provably_self_egress():
            resp = httpx.post(url, json=body, headers=hdrs, timeout=timeout_s)
        resp.raise_for_status()
    except Exception as e:
        _log.error("post_handoff_failed", url=url, error=str(e))
        raise


def default_cluster_b_url() -> str:
    return (os.getenv("CLUSTER_B_URL") or "http://localhost:8082").strip().rstrip("/")
