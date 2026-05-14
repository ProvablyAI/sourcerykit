from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
import requests

import provably.intercept._storage as storage
import provably.intercept.interceptor as interceptor
from provably.intercept._responses import RequestsJsonOverride
from provably.intercept._self_egress import provably_self_egress


def test_insert_row_receives_raw_before_mutation(monkeypatch: Any) -> None:
    captured: list[Any] = []

    def fake_insert(_url: str, _req: dict[str, Any], raw: Any, *, method: str = "GET") -> None:
        captured.append(raw)

    def fake_mutate(raw: Any) -> Any:
        return {"user_edited": True}

    monkeypatch.setattr(interceptor, "_insert_row", fake_insert)
    monkeypatch.setattr(interceptor, "_maybe_transform_body", fake_mutate)
    monkeypatch.setattr(interceptor, "_enabled", True)
    try:
        interceptor.set_intercept_url_allowlist(["https://example.com/x"])

        resp = requests.Response()
        resp.status_code = 200
        resp._content = b'{"original": true}'
        resp.encoding = "utf-8"

        out = interceptor._attach(resp, "https://example.com/x", "GET", {})
        assert captured == [{"original": True}]
        assert isinstance(out, RequestsJsonOverride)
        assert out.json() == {"user_edited": True}
    finally:
        interceptor.set_intercept_url_allowlist(None)


def test_tamper_hook_not_run_when_allowlist_cleared(monkeypatch: Any) -> None:
    """After a run, allowlist is None but handoff POST must not invoke the body hook."""
    calls: list[Any] = []

    def fake_mutate(_raw: Any) -> Any:
        calls.append(True)
        return {"bad": True}

    monkeypatch.setattr(interceptor, "_insert_row", lambda *a, **k: None)
    monkeypatch.setattr(interceptor, "_maybe_transform_body", fake_mutate)
    monkeypatch.setattr(interceptor, "_enabled", True)

    resp = requests.Response()
    resp.status_code = 200
    resp._content = b'{"ok": true}'
    resp.encoding = "utf-8"

    out = interceptor._attach(resp, "https://cluster-b.internal/run", "POST", {})
    assert calls == []
    assert out is resp


def test_attach_skips_url_not_in_allowlist(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_insert(url: str, *_a: Any, **_k: Any) -> None:
        calls.append(url)

    monkeypatch.setattr(interceptor, "_insert_row", fake_insert)
    monkeypatch.setattr(interceptor, "_maybe_transform_body", lambda r: r)
    monkeypatch.setattr(interceptor, "_enabled", True)
    try:
        interceptor.set_intercept_url_allowlist(["https://trusted.example/api"])

        resp = requests.Response()
        resp.status_code = 200
        resp._content = b"{}"
        resp.encoding = "utf-8"

        out = interceptor._attach(resp, "https://other.example/x", "GET", {})
        assert calls == []
        assert out is resp
    finally:
        interceptor.set_intercept_url_allowlist(None)


# ---------------------------------------------------------------------------
# Allowlist pattern matching ({id} / {path:path} parity with trusted_endpoints)
# ---------------------------------------------------------------------------


def _attach_with_pattern_allowlist(
    monkeypatch: Any, allowlist_entries: list[str], call_url: str
) -> tuple[list[str], list[Any]]:
    """Helper: install a pattern allowlist, run _attach against ``call_url``, return
    (recorded URLs, tamper-hook calls)."""
    recorded: list[str] = []
    tampered: list[Any] = []

    monkeypatch.setattr(
        interceptor, "_insert_row", lambda url, *_a, **_k: recorded.append(url)
    )
    def _record_tamper(raw: Any) -> Any:
        tampered.append(raw)
        return raw

    monkeypatch.setattr(interceptor, "_maybe_transform_body", _record_tamper)
    monkeypatch.setattr(interceptor, "_enabled", True)
    try:
        interceptor.set_intercept_url_allowlist(allowlist_entries)
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b'{"ok": true}'
        resp.encoding = "utf-8"
        interceptor._attach(resp, call_url, "GET", {})
    finally:
        interceptor.set_intercept_url_allowlist(None)
    return recorded, tampered


def test_allowlist_pattern_matches_concrete_url(monkeypatch: Any) -> None:
    """Registered ``/customers/{id}`` matches the concrete ``/customers/42`` URL — both
    recorded and tamper-hooked."""
    recorded, tampered = _attach_with_pattern_allowlist(
        monkeypatch,
        ["https://api.example.com/customers/{id}"],
        "https://api.example.com/customers/42",
    )
    assert recorded == ["https://api.example.com/customers/42"]
    assert len(tampered) == 1


def test_allowlist_pattern_rejects_extra_segment(monkeypatch: Any) -> None:
    """Registered ``/customers/{id}`` does NOT match ``/customers/42/orders``
    (single-segment placeholder)."""
    recorded, tampered = _attach_with_pattern_allowlist(
        monkeypatch,
        ["https://api.example.com/customers/{id}"],
        "https://api.example.com/customers/42/orders",
    )
    assert recorded == []
    assert tampered == []


def test_allowlist_path_placeholder_matches_subtree(monkeypatch: Any) -> None:
    """``{rest:path}`` covers any subtree, including nested segments."""
    recorded, _ = _attach_with_pattern_allowlist(
        monkeypatch,
        ["https://api.example.com/customers/{rest:path}"],
        "https://api.example.com/customers/42/orders/9",
    )
    assert recorded == ["https://api.example.com/customers/42/orders/9"]


def test_allowlist_mixed_exact_and_pattern(monkeypatch: Any) -> None:
    """An allowlist with both exact URLs and patterns: each entry retains its semantics."""
    # Exact entry hits exactly; pattern entry hits its pattern; unrelated URL is rejected.
    for url, expected_recorded in [
        ("https://api.example.com/health", True),  # exact match
        ("https://api.example.com/customers/9", True),  # pattern match
        ("https://api.example.com/customers/9/orders", False),  # past pattern
        ("https://api.example.com/other", False),  # unrelated
    ]:
        recorded, _ = _attach_with_pattern_allowlist(
            monkeypatch,
            [
                "https://api.example.com/health",
                "https://api.example.com/customers/{id}",
            ],
            url,
        )
        assert (recorded == [url]) is expected_recorded, (
            f"url={url!r}: expected_recorded={expected_recorded}, got recorded={recorded}"
        )


def test_allowlist_plain_url_still_uses_exact_match(monkeypatch: Any) -> None:
    """An allowlist entry without ``{`` keeps exact-match semantics — no perf regression for
    the common case and no accidental prefix match."""
    recorded, _ = _attach_with_pattern_allowlist(
        monkeypatch,
        ["https://api.example.com/customers"],  # no placeholders → exact-only
        "https://api.example.com/customers/42",
    )
    assert recorded == []


# ---------------------------------------------------------------------------
# Phase 1 additions: Client.send / AsyncClient.send / Session.send coverage,
# re-entry guard, and self-egress exemption.
# ---------------------------------------------------------------------------


def _make_fake_insert(
    rows: list[dict[str, Any]],
) -> Callable[..., None]:
    """Return a fake _insert_row that appends to ``rows``."""

    def fake_insert(url: str, request_payload: dict[str, Any], raw: Any, *, method: str = "GET") -> None:
        rows.append({"url": url, "method": method, "request": request_payload, "raw": raw})

    return fake_insert


def _setup_interceptor(monkeypatch: Any, rows: list[dict[str, Any]]) -> None:
    """Patch _insert_row and enable interceptor; call init_interceptor to ensure patches are installed."""
    monkeypatch.setattr(interceptor, "_insert_row", _make_fake_insert(rows))
    interceptor.init_interceptor()
    monkeypatch.setattr(interceptor, "_enabled", True)


def test_httpx_client_send_intercepted(monkeypatch: Any, fake_server: Any) -> None:
    """httpx.Client(...).get(url) records exactly one row via the Client.send patch."""
    fake_server.respond("GET", "/data", status=200, body={"from_client": True})
    rows: list[dict[str, Any]] = []
    _setup_interceptor(monkeypatch, rows)

    client = httpx.Client()
    response = client.get(f"{fake_server.base_url}/data")
    client.close()

    assert response.status_code == 200
    assert len(rows) == 1
    assert rows[0]["method"] == "GET"
    assert rows[0]["raw"] == {"from_client": True}


async def test_httpx_async_client_send_intercepted(monkeypatch: Any, fake_server: Any) -> None:
    """await httpx.AsyncClient().get(url) records exactly one row via AsyncClient.send patch."""
    fake_server.respond("GET", "/async-data", status=200, body={"async": True})
    rows: list[dict[str, Any]] = []
    _setup_interceptor(monkeypatch, rows)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{fake_server.base_url}/async-data")

    assert response.status_code == 200
    assert len(rows) == 1
    assert rows[0]["method"] == "GET"
    assert rows[0]["raw"] == {"async": True}


def test_requests_session_send_intercepted(monkeypatch: Any, fake_server: Any) -> None:
    """requests.Session().get(url) records exactly one row via Session.send patch."""
    fake_server.respond("GET", "/session-data", status=200, body={"from_session": True})
    rows: list[dict[str, Any]] = []
    _setup_interceptor(monkeypatch, rows)

    session = requests.Session()
    response = session.get(f"{fake_server.base_url}/session-data")

    assert response.status_code == 200
    assert len(rows) == 1
    assert rows[0]["method"] == "GET"
    assert rows[0]["raw"] == {"from_session": True}


def test_no_double_record_when_module_httpx_get_called(monkeypatch: Any, fake_server: Any) -> None:
    """httpx.get(url) records exactly one row even though both module-level and Client.send patches are active."""
    fake_server.respond("GET", "/data", status=200, body={"v": 1})
    rows: list[dict[str, Any]] = []
    _setup_interceptor(monkeypatch, rows)

    httpx.get(f"{fake_server.base_url}/data")

    assert len(rows) == 1, f"Expected 1 row but got {len(rows)}: {rows}"


def test_no_double_record_when_module_requests_get_called(monkeypatch: Any, fake_server: Any) -> None:
    """requests.get(url) records exactly one row even though both module-level and Session.send patches are active."""
    fake_server.respond("GET", "/data", status=200, body={"v": 2})
    rows: list[dict[str, Any]] = []
    _setup_interceptor(monkeypatch, rows)

    requests.get(f"{fake_server.base_url}/data")

    assert len(rows) == 1, f"Expected 1 row but got {len(rows)}: {rows}"


def test_self_egress_skips_recording(monkeypatch: Any, fake_server: Any) -> None:
    """Inside with provably_self_egress(): no row is inserted."""
    fake_server.respond("GET", "/data", status=200, body={"v": 3})
    rows: list[dict[str, Any]] = []
    _setup_interceptor(monkeypatch, rows)

    with provably_self_egress():
        requests.get(f"{fake_server.base_url}/data")

    assert rows == [], f"Expected no rows but got: {rows}"


def test_self_egress_skips_trust_check(monkeypatch: Any, fake_server: Any) -> None:
    """Inside with provably_self_egress(): an untrusted URL does NOT raise (storage layer short-circuits)."""
    fake_server.respond("POST", "/untrusted", status=200, body={"ok": True})

    trust_calls: list[str] = []

    def fake_require(postgres_url: str, url: str) -> None:
        trust_calls.append(url)
        raise RuntimeError(f"BLOCKED: {url}")

    monkeypatch.setattr(storage, "_require_trusted_endpoint", fake_require)
    monkeypatch.setenv("POSTGRES_URL", "postgresql://fake/db")
    monkeypatch.setattr(interceptor, "_insert_row", _make_fake_insert([]))
    interceptor.init_interceptor()
    monkeypatch.setattr(interceptor, "_enabled", True)

    with provably_self_egress():
        # This should NOT raise even though _require_trusted_endpoint would block it
        response = requests.post(f"{fake_server.base_url}/untrusted", json={"x": 1})

    # Trust check was never called (self-egress bypassed storage entirely)
    assert trust_calls == []
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Storage-level trust gate tests (POST / DELETE coverage)
# ---------------------------------------------------------------------------


def test_trust_gate_fires_on_post(monkeypatch: Any) -> None:
    """POST to an untrusted URL raises RuntimeError('BLOCKED: ...')."""
    trust_calls: list[tuple[str, str]] = []

    def fake_require(postgres_url: str, url: str) -> None:
        trust_calls.append((postgres_url, url))
        raise RuntimeError(f"BLOCKED: {url} not in trusted index")

    monkeypatch.setattr(storage, "_require_trusted_endpoint", fake_require)
    monkeypatch.setenv("POSTGRES_URL", "postgresql://fake/db")

    with pytest.raises(RuntimeError, match="BLOCKED"):
        storage.insert_intercept_row(
            url="https://untrusted.example/api",
            method="POST",
            request_payload={"url": "https://untrusted.example/api", "method": "POST"},
            raw={"data": 1},
            agent_id="ag",
            action_name="act",
        )

    assert len(trust_calls) == 1
    assert trust_calls[0][1] == "https://untrusted.example/api"


# ---------------------------------------------------------------------------
# aiohttp coverage (soft dependency — only installs when aiohttp is importable)
# ---------------------------------------------------------------------------

aiohttp = pytest.importorskip("aiohttp")


async def test_aiohttp_session_request_intercepted(monkeypatch: Any, fake_server: Any) -> None:
    """aiohttp.ClientSession().get(url) records exactly one row via the _request patch."""
    fake_server.respond("GET", "/aiohttp-data", status=200, body={"from_aiohttp": True})
    rows: list[dict[str, Any]] = []
    _setup_interceptor(monkeypatch, rows)

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{fake_server.base_url}/aiohttp-data") as response:
            assert response.status == 200
            data = await response.json()
            assert data == {"from_aiohttp": True}

    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}: {rows}"
    assert rows[0]["method"] == "GET"
    assert rows[0]["raw"] == {"from_aiohttp": True}


async def test_aiohttp_post_with_json_body_intercepted(monkeypatch: Any, fake_server: Any) -> None:
    """POSTing JSON via aiohttp records request payload correctly."""
    fake_server.respond("POST", "/echo", status=200, body={"ok": True})
    rows: list[dict[str, Any]] = []
    _setup_interceptor(monkeypatch, rows)

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{fake_server.base_url}/echo", json={"k": "v"}) as response:
            assert response.status == 200

    assert len(rows) == 1
    assert rows[0]["method"] == "POST"
    assert rows[0]["request"]["json"] == {"k": "v"}


async def test_aiohttp_self_egress_skips_recording(monkeypatch: Any, fake_server: Any) -> None:
    """Inside provably_self_egress(): aiohttp call records nothing."""
    fake_server.respond("GET", "/data", status=200, body={"v": 9})
    rows: list[dict[str, Any]] = []
    _setup_interceptor(monkeypatch, rows)

    with provably_self_egress():
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{fake_server.base_url}/data") as _resp:
                pass

    assert rows == []


def test_trust_gate_fires_on_delete(monkeypatch: Any) -> None:
    """DELETE to an untrusted URL raises RuntimeError('BLOCKED: ...') — all-methods coverage."""
    trust_calls: list[str] = []

    def fake_require(postgres_url: str, url: str) -> None:
        trust_calls.append(url)
        raise RuntimeError(f"BLOCKED: {url}")

    monkeypatch.setattr(storage, "_require_trusted_endpoint", fake_require)
    monkeypatch.setenv("POSTGRES_URL", "postgresql://fake/db")

    with pytest.raises(RuntimeError, match="BLOCKED"):
        storage.insert_intercept_row(
            url="https://untrusted.example/resource/1",
            method="DELETE",
            request_payload={"url": "https://untrusted.example/resource/1", "method": "DELETE"},
            raw={},
            agent_id="ag",
            action_name="act",
        )

    assert trust_calls == ["https://untrusted.example/resource/1"]
