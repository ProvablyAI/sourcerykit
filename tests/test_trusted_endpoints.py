from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from provably.trusted_endpoints import (
    is_trusted_endpoint,
    list_trusted_endpoints,
    normalize_url_for_trust,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", ""),
        ("  ", ""),
        ("HTTPS://API.EXAMPLE.COM/Path/", "https://api.example.com/Path"),
        ("http://localhost:8080/foo/", "http://localhost:8080/foo"),
        ("http://localhost:9000/", "http://localhost:9000"),
    ],
)
def test_normalize_url_for_trust(raw: str, expected: str) -> None:
    assert normalize_url_for_trust(raw) == expected


def test_is_trusted_false_when_empty_url_or_org() -> None:
    conn = MagicMock()
    assert is_trusted_endpoint("", "org", conn) is False
    assert is_trusted_endpoint("https://a.com", "", conn) is False


def test_is_trusted_queries_normalized_row(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("provably.trusted_endpoints._ensure_trusted_table", lambda _c: None)
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = lambda *_: cur
    conn.cursor.return_value.__exit__ = lambda *_: None
    cur.fetchone.return_value = (1,)

    assert is_trusted_endpoint("HTTPS://X.COM/a/", "org-1", conn) is True
    cur.execute.assert_called_once()
    args = cur.execute.call_args[0]
    assert "trusted_endpoints" in args[0]
    assert args[1][1] == "https://x.com/a"


def test_list_trusted_endpoints_excludes_given_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("provably.trusted_endpoints._ensure_trusted_table", lambda _c: None)
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = lambda *_: cur
    conn.cursor.return_value.__exit__ = lambda *_: None
    cur.fetchall.return_value = [
        ("https://httpbin.org/json", "HTTPBin"),
        ("http://internal.test/receive", "Internal"),
    ]

    rows = list_trusted_endpoints(
        conn,
        "org-1",
        excluded_urls={"http://internal.test/receive"},
    )
    assert rows == [
        {
            "url": "https://httpbin.org/json",
            "label": "HTTPBin",
            "category": "custom",
            "risk_level": "unknown",
            "description": "",
            "expected_response": "",
        }
    ]
