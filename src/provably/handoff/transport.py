"""Required A→B transport: POST HandoffPayload JSON to external Cluster B."""

from __future__ import annotations

import os

import httpx

from provably.handoff.types import HandoffPayload
from provably.log import get_logger

_log = get_logger(__name__)


def post_handoff(
    cluster_b_url: str,
    handoff_payload: HandoffPayload,
    *,
    headers: dict[str, str] | None = None,
    timeout_s: float = 120.0,
) -> None:
    """POST a serialized :class:`HandoffPayload` to Cluster B's ``/handoffs/receive`` endpoint.

    The payload is serialized via ``model_dump(mode="json")`` so all Pydantic types end up as
    valid JSON. Trailing slashes on ``cluster_b_url`` are stripped; the final URL is always
    ``{base}/handoffs/receive``. On HTTP failure this logs ``post_handoff_failed`` (structured
    logger) and re-raises so callers can decide how to handle the error.

    Args:
        cluster_b_url: Base URL of the Cluster B service. Empty string is rejected.
        handoff_payload: Fully-assembled Cluster A → B contract.
        headers: Extra HTTP headers merged on top of the default ``Content-Type: application/json``.
        timeout_s: HTTP timeout for the single POST.

    Raises:
        ValueError: ``cluster_b_url`` is empty.
        httpx.HTTPError: The downstream service returned a non-2xx response or the request failed.
    """
    base = (cluster_b_url or "").strip().rstrip("/")
    if not base:
        raise ValueError("cluster_b_url is empty — set CLUSTER_B_URL to post handoff")
    url = f"{base}/handoffs/receive"
    body = handoff_payload.model_dump(mode="json")
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    try:
        resp = httpx.post(url, json=body, headers=hdrs, timeout=timeout_s)
        resp.raise_for_status()
    except Exception as e:
        _log.error("post_handoff_failed", url=url, error=str(e))
        raise


def default_cluster_b_url() -> str:
    """Return ``CLUSTER_B_URL`` from the env (trimmed, no trailing slash), or localhost:8082 if unset."""
    return (os.getenv("CLUSTER_B_URL") or "http://localhost:8082").strip().rstrip("/")
