from __future__ import annotations

from typing import Any

import requests

import provably.intercept.interceptor as interceptor


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
        assert isinstance(out, interceptor._RequestsJsonOverride)
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
