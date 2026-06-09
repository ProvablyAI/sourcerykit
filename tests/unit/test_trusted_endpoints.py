from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agentkit.trusted_endpoints import (
    _compile_pattern,
    _matches_registered,
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


# ---------------------------------------------------------------------------
# Pattern matching ({name} and {name:path} placeholders)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "registered",
    [
        "https://api.example.com/customers",
        "https://api.example.com/customers/123",
        "https://example.com",
    ],
)
def test_compile_pattern_returns_none_for_plain_urls(registered: str) -> None:
    assert _compile_pattern(registered) is None


def test_pattern_single_segment_matches_one_path_segment() -> None:
    pattern = _compile_pattern("https://api.example.com/customers/{id}")
    assert pattern is not None
    assert pattern.match("https://api.example.com/customers/123") is not None
    assert pattern.match("https://api.example.com/customers/abc-DEF") is not None
    # Must NOT swallow additional path segments
    assert pattern.match("https://api.example.com/customers/123/orders") is None
    # Must NOT match a different prefix
    assert pattern.match("https://api.example.com/clients/123") is None
    # Must NOT match the bare prefix without an id segment
    assert pattern.match("https://api.example.com/customers/") is None


def test_pattern_path_placeholder_matches_subtree() -> None:
    pattern = _compile_pattern("https://api.example.com/customers/{rest:path}")
    assert pattern is not None
    assert pattern.match("https://api.example.com/customers/123") is not None
    assert pattern.match("https://api.example.com/customers/123/orders/456") is not None
    # Still anchored at the prefix
    assert pattern.match("https://api.example.com/clients/123") is None


def test_pattern_multiple_placeholders() -> None:
    pattern = _compile_pattern("https://api.example.com/customers/{cust}/orders/{order}")
    assert pattern is not None
    assert pattern.match("https://api.example.com/customers/c1/orders/o9") is not None
    assert pattern.match("https://api.example.com/customers/c1/orders/o9/items/x") is None


def test_matches_registered_falls_back_to_exact() -> None:
    assert _matches_registered("https://x.com/a", "https://x.com/a") is True
    assert _matches_registered("https://x.com/a", "https://x.com/b") is False


def test_matches_registered_uses_pattern_when_present() -> None:
    assert _matches_registered("https://x.com/customers/9", "https://x.com/customers/{id}") is True
    assert _matches_registered("https://x.com/customers/9/orders", "https://x.com/customers/{id}") is False


def test_is_trusted_endpoint_matches_pattern_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """A claim URL matching a registered ``{id}`` pattern is trusted via the slow path."""
    monkeypatch.setattr("provably.trusted_endpoints._ensure_trusted_table", lambda _c: None)
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = lambda *_: cur
    conn.cursor.return_value.__exit__ = lambda *_: None
    # First query (exact match) misses; second query (pattern entries) returns one row.
    cur.fetchone.return_value = None
    cur.fetchall.return_value = [("https://api.example.com/customers/{id}",)]

    assert is_trusted_endpoint("https://api.example.com/customers/42", "org-1", conn) is True
    # Exact-then-pattern: two execute calls.
    assert cur.execute.call_count == 2


def test_is_trusted_endpoint_rejects_nonmatching_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("provably.trusted_endpoints._ensure_trusted_table", lambda _c: None)
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = lambda *_: cur
    conn.cursor.return_value.__exit__ = lambda *_: None
    cur.fetchone.return_value = None
    # Registered pattern allows /customers/{id} only — claim hits a deeper path.
    cur.fetchall.return_value = [("https://api.example.com/customers/{id}",)]

    assert is_trusted_endpoint("https://api.example.com/customers/42/orders", "org-1", conn) is False


def test_snapshot_check_accepts_pattern_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """The snapshot tamper-check must honor pattern entries the same way the live DB check does."""
    from agentkit.handoff.types import HandoffClaim, HandoffPayload
    from agentkit.trusted_endpoints import check_claim_endpoints_are_trusted

    # Live DB check is exercised separately; stub it as trusting whatever made it past
    # the snapshot check (returns True).
    monkeypatch.setattr("provably.trusted_endpoints.is_trusted_endpoint", lambda *_a, **_kw: True)
    monkeypatch.setattr("psycopg2.connect", lambda *_a, **_kw: MagicMock())

    payload = HandoffPayload(
        provably_org_id="org-1",
        trusted_endpoint_registry=["https://api.example.com/customers/{id}"],
        claims=[
            HandoffClaim(
                action_name="get_customer",
                request_payload={"url": "https://api.example.com/customers/42", "method": "GET"},
            )
        ],
    )

    # Should NOT raise — pattern entry covers the concrete URL.
    check_claim_endpoints_are_trusted(payload, postgres_url="postgresql://x")


def test_snapshot_check_rejects_url_outside_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    from agentkit.handoff.types import HandoffClaim, HandoffPayload
    from agentkit.trusted_endpoints import check_claim_endpoints_are_trusted

    monkeypatch.setattr("provably.trusted_endpoints.is_trusted_endpoint", lambda *_a, **_kw: True)
    monkeypatch.setattr("psycopg2.connect", lambda *_a, **_kw: MagicMock())

    payload = HandoffPayload(
        provably_org_id="org-1",
        trusted_endpoint_registry=["https://api.example.com/customers/{id}"],
        claims=[
            HandoffClaim(
                action_name="get_orders",
                # Goes one segment deeper than {id} permits.
                request_payload={"url": "https://api.example.com/customers/42/orders", "method": "GET"},
            )
        ],
    )

    with pytest.raises(ValueError, match="missing from trusted snapshot"):
        check_claim_endpoints_are_trusted(payload, postgres_url="postgresql://x")


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
