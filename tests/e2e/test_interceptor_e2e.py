"""End-to-end test for the HTTP interceptor.

Installs the real interceptor (``provably.init_interceptor``), patches only the
Postgres-touching storage layer, and drives real ``requests.get`` + ``httpx.get``
calls against a loopback HTTP server. Asserts that:

- The original wire response is captured (before any simulation hook runs).
- A simulation body hook can override the response the caller sees (only for URLs
  on :func:`set_intercept_url_allowlist`), without changing the row recorded into the storage layer.
- ``disable()`` stops recording on subsequent calls.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import pytest
import requests

import provably
import provably.intercept.interceptor as interceptor
from tests.e2e.conftest import FakeHttpServer


@pytest.mark.e2e
def test_requests_get_records_raw_response(
    fake_server: FakeHttpServer, patched_interceptor: list[dict[str, Any]]
) -> None:
    fake_server.respond("GET", "/data", status=200, body={"original": True})
    response = requests.get(f"{fake_server.base_url}/data")

    assert response.status_code == 200
    assert response.json() == {"original": True}
    assert len(patched_interceptor) == 1
    assert patched_interceptor[0]["method"] == "GET"
    assert patched_interceptor[0]["raw"] == {"original": True}


@pytest.mark.e2e
def test_simulation_hook_overrides_response_body(
    fake_server: FakeHttpServer,
    patched_interceptor: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_server.respond("GET", "/data", status=200, body={"original": True})

    def hook(_idx: int, raw: Any) -> Any:
        assert raw == {"original": True}
        return {"user_edited": True}

    url = f"{fake_server.base_url}/data"
    interceptor.set_intercept_url_allowlist([url])
    provably.set_intercept_body_hook(hook)
    try:
        resp = requests.get(url)
        assert resp.json() == {"user_edited": True}
    finally:
        provably.set_intercept_body_hook(None)
        interceptor.set_intercept_url_allowlist(None)

    assert patched_interceptor[0]["raw"] == {"original": True}


@pytest.mark.e2e
def test_disable_stops_recording(
    fake_server: FakeHttpServer, patched_interceptor: list[dict[str, Any]]
) -> None:
    fake_server.respond("GET", "/data", status=200, body={"v": 1})

    requests.get(f"{fake_server.base_url}/data")
    assert len(patched_interceptor) == 1

    provably.disable()
    try:
        requests.get(f"{fake_server.base_url}/data")
    finally:
        provably.enable()

    assert len(patched_interceptor) == 1


@pytest.mark.e2e
def test_httpx_get_also_intercepted(
    fake_server: FakeHttpServer, patched_interceptor: list[dict[str, Any]]
) -> None:
    fake_server.respond("GET", "/data", status=200, body={"v": 7})

    response = httpx.get(f"{fake_server.base_url}/data")

    assert response.status_code == 200
    assert response.json() == {"v": 7}
    assert len(patched_interceptor) == 1


@pytest.fixture(autouse=True)
def _clear_run_id_env() -> None:
    os.environ.pop("PROVABLY_SIMULATION_RUN_ID", None)
