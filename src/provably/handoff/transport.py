from __future__ import annotations

import httpx

from provably.handoff.types import HandoffPayload
from provably.intercept._self_egress import provably_self_egress
from provably.log import get_logger

_log = get_logger(__name__)


def post_handoff(
    receiver_url: str,
    handoff_payload: HandoffPayload,
    *,
    headers: dict[str, str] | None = None,
    timeout_s: float = 120.0,
) -> None:
    """POST a serialized ``HandoffPayload`` to ``{receiver_url}/handoffs/receive``.

    The receiver is whatever service runs ``evaluate_handoff`` on the payload — typically
    a separate verifier in a two-service deployment, but the SDK has no opinion on its
    location: ``receiver_url`` is supplied by the caller, never read from the environment.
    """
    base = (receiver_url or "").strip().rstrip("/")
    if not base:
        raise ValueError("receiver_url is empty — pass the verifier's base URL to post_handoff")
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
