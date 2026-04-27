"""End-to-end test for ``provably.handoff.transport.post_handoff``.

Drives the real ``httpx.post`` against a loopback HTTP server and asserts the
SDK serialized the ``HandoffPayload`` correctly and hit ``/handoffs/receive``.
"""

from __future__ import annotations

import json

import pytest

from provably.handoff.transport import post_handoff
from provably.handoff.types import HandoffClaim, HandoffPayload
from tests.e2e.conftest import FakeHttpServer


@pytest.mark.e2e
def test_post_handoff_sends_canonical_json(fake_server: FakeHttpServer) -> None:
    fake_server.respond("POST", "/handoffs/receive", status=200, body={"ok": True})

    payload = HandoffPayload(
        provably_org_id="org-1",
        integration_api_key="key-abc",
        task="discharge_summary",
        claims=[
            HandoffClaim(action_name="get", claimed_value={"x": 1}, query_record_id="q1"),
        ],
    )

    post_handoff(fake_server.base_url, payload, headers={"x-trace-id": "t-42"})

    assert len(fake_server.requests) == 1
    req = fake_server.requests[0]
    assert req.method == "POST"
    assert req.path == "/handoffs/receive"
    assert req.headers.get("Content-Type") == "application/json"
    assert req.headers.get("x-trace-id") == "t-42"

    body = json.loads(req.body)
    assert body["provably_org_id"] == "org-1"
    assert body["integration_api_key"] == "key-abc"
    assert body["task"] == "discharge_summary"
    assert body["claims"][0]["action_name"] == "get"
    assert body["claims"][0]["query_record_id"] == "q1"


@pytest.mark.e2e
def test_post_handoff_raises_on_server_error(fake_server: FakeHttpServer) -> None:
    fake_server.respond("POST", "/handoffs/receive", status=500, body={"error": "boom"})

    with pytest.raises(Exception):  # noqa: B017,PT011 — httpx.HTTPStatusError or wrapper
        post_handoff(fake_server.base_url, HandoffPayload(task="t"))
