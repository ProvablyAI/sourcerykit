from __future__ import annotations

from typing import Any

import pytest

from provably.intercept import _loader
from provably.intercept._loader import load_latest_intercept_payload


class FakeCursor:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row
        self.executed: tuple[str, tuple[Any, ...]] | None = None

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...]) -> None:
        self.executed = (sql, params)

    def fetchone(self) -> dict[str, Any] | None:
        return self._row


class FakeConn:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self.cursor_obj = FakeCursor(row)
        self.closed = False

    def cursor(self, *, cursor_factory: Any = None) -> FakeCursor:
        return self.cursor_obj

    def close(self) -> None:
        self.closed = True


def install_conn(monkeypatch: pytest.MonkeyPatch, row: dict[str, Any] | None) -> FakeConn:
    conn = FakeConn(row)
    monkeypatch.setattr(_loader.psycopg2, "connect", lambda _url: conn)
    return conn


def test_empty_pg_url_short_circuits() -> None:
    assert load_latest_intercept_payload("", "act", agent_id="ag") == ({}, None)


def test_row_with_json_string_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = install_conn(
        monkeypatch,
        {"request_payload": '{"q": 1}', "raw_response": '{"ok": true}'},
    )

    req, resp = load_latest_intercept_payload("postgres://x", "act", agent_id="ag")

    assert req == {"q": 1}
    assert resp == {"ok": True}
    assert conn.closed is True
    assert conn.cursor_obj.executed is not None
    assert conn.cursor_obj.executed[1] == ("ag", "act")


def test_row_with_dict_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    install_conn(
        monkeypatch,
        {"request_payload": {"q": 2}, "raw_response": {"already": "dict"}},
    )

    req, resp = load_latest_intercept_payload("postgres://x", "act", agent_id="ag")

    assert req == {"q": 2}
    assert resp == {"already": "dict"}


def test_no_row_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = install_conn(monkeypatch, None)

    assert load_latest_intercept_payload("postgres://x", "act", agent_id="ag") == ({}, None)
    assert conn.closed is True


def test_invalid_json_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    install_conn(
        monkeypatch,
        {"request_payload": "not-json", "raw_response": "not-json-either"},
    )

    req, resp = load_latest_intercept_payload("postgres://x", "act", agent_id="ag")

    # request payload: invalid JSON -> {}
    assert req == {}
    # raw_response: invalid JSON string -> returned as-is
    assert resp == "not-json-either"


def test_connection_closed_even_on_cursor_error(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = FakeConn(None)

    def boom(*, cursor_factory: Any = None) -> FakeCursor:
        raise RuntimeError("cursor failed")

    conn.cursor = boom  # type: ignore[method-assign]
    monkeypatch.setattr(_loader.psycopg2, "connect", lambda _url: conn)

    with pytest.raises(RuntimeError, match="cursor failed"):
        load_latest_intercept_payload("postgres://x", "act", agent_id="ag")
    assert conn.closed is True
