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
    monkeypatch.setattr(interceptor, "_maybe_simulate_body", fake_mutate)
    monkeypatch.setattr(interceptor, "_enabled", True)

    resp = requests.Response()
    resp.status_code = 200
    resp._content = b'{"original": true}'
    resp.encoding = "utf-8"

    out = interceptor._attach(resp, "https://example.com/x", "GET", {})
    assert captured == [{"original": True}]
    assert isinstance(out, interceptor._RequestsJsonOverride)
    assert out.json() == {"user_edited": True}
