"""Tests for sourcerykit.provably.oauth_login."""

import asyncio
import base64
import contextlib
import hashlib
import socket
import urllib.error
import urllib.request
from collections.abc import Callable

import pytest

from sourcerykit.provably import oauth_login
from sourcerykit.provably.oauth_login import _origin_of, _wait_for_loopback_code, pkce_pair


def _free_port() -> int:
    """A port nothing else holds, so the suite does not fight the real CLI."""
    with contextlib.closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def loopback_port(monkeypatch: pytest.MonkeyPatch) -> int:
    port = _free_port()
    monkeypatch.setattr(oauth_login, "LOOPBACK_PORT", port)
    return port


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
    monkeypatch.setattr("sourcerykit.provably.oauth_login.webbrowser.open", lambda url: opened.append(url))

    async def no_callback(
        allowed_origin: str = "",
        timeout: float = 300.0,
    ) -> tuple[dict[str, str], Callable[[str | None], None]]:
        return {}, lambda failure: None

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


def test_origin_of() -> None:
    assert _origin_of("https://app.example/consent") == "https://app.example"
    assert _origin_of("https://app.example/consent?a=1") == "https://app.example"
    assert _origin_of("not a url") == ""


async def _open_callback(port: int, reply: dict[str, object]) -> None:
    """Stand in for the browser: fetch /callback and record what came back."""
    request = urllib.request.Request(f"http://127.0.0.1:{port}/callback?code=abc&state=xyz")

    def fetch() -> None:
        try:
            with urllib.request.urlopen(request, timeout=10) as answer:
                reply["status"] = answer.status
                reply["origin"] = answer.headers.get("Access-Control-Allow-Origin")
                reply["body"] = answer.read().decode()
        except urllib.error.HTTPError as failed:
            reply["status"] = failed.code
            reply["origin"] = failed.headers.get("Access-Control-Allow-Origin")
            reply["body"] = failed.read().decode()

    await asyncio.to_thread(fetch)


@pytest.mark.asyncio
async def test_callback_reply_waits_and_reports_success(loopback_port: int) -> None:
    reply: dict[str, object] = {}
    browser = asyncio.create_task(_open_callback(loopback_port, reply))

    callback, settle = await _wait_for_loopback_code("https://app.example")

    assert callback == {"code": "abc", "state": "xyz"}
    assert not reply, "the browser must still be waiting for its reply"

    settle(None)
    await browser

    assert reply["status"] == 200
    assert reply["origin"] == "https://app.example"
    assert "Logged in!" in str(reply["body"])


@pytest.mark.asyncio
async def test_callback_reply_reports_failure(loopback_port: int) -> None:
    reply: dict[str, object] = {}
    browser = asyncio.create_task(_open_callback(loopback_port, reply))

    _, settle = await _wait_for_loopback_code("https://app.example")
    settle("the code was refused")
    await browser

    assert reply["status"] == 500
    assert "the code was refused" in str(reply["body"])
