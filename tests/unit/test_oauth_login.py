"""Tests for sourcerykit.provably.oauth_login."""

import base64
import hashlib

import pytest

from sourcerykit.provably.oauth_login import pkce_pair


def test_pkce_pair_s256_verifiable() -> None:
    verifier, challenge = pkce_pair()
    assert verifier and challenge
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == expected


def test_browser_login_carries_the_machine_id_in_the_consent_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio
    import urllib.parse

    from sourcerykit.provably import oauth_login

    opened: list[str] = []
    monkeypatch.setattr(
        "sourcerykit.provably.oauth_login.webbrowser.open", lambda url: opened.append(url)
    )

    async def no_callback(timeout: float = 300.0) -> dict[str, str]:
        return {}

    monkeypatch.setattr(oauth_login, "_wait_for_loopback_code", no_callback)

    async def run(**kwargs: str) -> None:
        try:
            await oauth_login.browser_login("https://app.example/consent", **kwargs)
        except ValueError:
            pass  # empty callback; only the opened URL matters here

    asyncio.run(run(machine_id="opaque-123"))
    with_id = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(opened[0]).query))
    assert with_id["machine_id"] == "opaque-123"
    assert with_id["response_type"] == "code"

    asyncio.run(run())
    without = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(opened[1]).query))
    assert "machine_id" not in without
