"""OAuth2 login for the SourceryKit CLI — public client with PKCE (RFC 7636/8252).

:func:`browser_login` opens ``{provably_app}/consent?…``; the web app drives
sign-in and consent and redirects to this CLI's loopback listener
(``http://127.0.0.1:8910/callback``). The client is public: no secret, PKCE
S256 is the only proof.

This module is pure OAuth orchestration — the token HTTP calls live in
:mod:`sourcerykit.provably.auth_service`.
"""

import asyncio
import base64
import hashlib
import html
import os
import secrets
import threading
import urllib.parse
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer

from sourcerykit.config import DEFAULT_PROVABLY_APP_URL, load_app_dir_config
from sourcerykit.logger import get_logger
from sourcerykit.provably._auth_api import (
    LOOPBACK_PORT,
    OAUTH_CLIENT_ID,
    OAUTH_SCOPE,
    REDIRECT_URI,
    OAuthTokens,
)
from sourcerykit.provably.auth_service import auth_service

_log = get_logger(__name__)

# How long the browser's request waits for the token exchange to finish.
SETTLE_TIMEOUT = 30.0


def pkce_pair() -> tuple[str, str]:
    """Return ``(verifier, challenge)`` using the S256 method."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def consent_page_url() -> str:
    """URL of the web app consent page.

    When ``SOURCERYKIT_PROVABLY_APP_URL`` (or ``provably_app``) is set it is
    used verbatim as the consent page URL — point it at your app's consent page
    in dev. When unset, falls back to the production app's ``/consent`` page.
    """
    raw = os.environ.get("SOURCERYKIT_PROVABLY_APP_URL") or ""
    if not raw:
        raw = str(load_app_dir_config().get("provably_app", ""))
    raw = raw.strip().rstrip("/")
    return raw or f"{DEFAULT_PROVABLY_APP_URL}/consent"


# ----------------------------------------------------------------------
# Browser flow
# ----------------------------------------------------------------------


class _LoopbackCallbackHandler(BaseHTTPRequestHandler):
    """Captures ?code/&state on GET /callback and holds its reply.

    The reply waits until the code has been traded for tokens, so what the
    browser reads is the real outcome rather than "received it". The consent
    page reads that reply across origins, which needs the allow-origin header.
    """

    result: dict[str, str] = {}
    done = threading.Event()
    settled = threading.Event()
    failure: str | None = None
    allowed_origin: str = ""

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        parsed = urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query)
        type(self).result = dict(parsed)
        type(self).done.set()

        type(self).settled.wait(SETTLE_TIMEOUT)

        failure = type(self).failure
        if not type(self).settled.is_set():
            failure = "the CLI stopped waiting"

        self.send_response(200 if failure is None else 500)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if type(self).allowed_origin:
            self.send_header("Access-Control-Allow-Origin", type(self).allowed_origin)
        self.end_headers()
        self.wfile.write(_callback_page(failure))

    def log_message(self, format: str, *args: object) -> None:  # silence stderr
        pass


def _callback_page(failure: str | None) -> bytes:
    """What the browser shows when the CLI has finished with the code."""
    if failure is None:
        body = "<h2>Logged in!</h2>You can close this window."
    else:
        body = f"<h2>Sign-in failed</h2>{html.escape(failure)}"
    return f"<html><body>{body}</body></html>".encode()


def _origin_of(url: str) -> str:
    """Scheme and host of a URL, or "" when it has neither."""
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else ""


async def _wait_for_loopback_code(
    allowed_origin: str = "",
    timeout: float = 300.0,
) -> tuple[dict[str, str], Callable[[str | None], None]]:
    """Bind the registered loopback port and wait for the OAuth redirect.

    The browser is still waiting for its reply when this returns. Call the
    returned ``settle`` with ``None`` once the code has been traded for tokens,
    or with a reason when it failed, and the browser is told which. ``settle``
    also stops the listener, so it has to run exactly once.
    """
    server = HTTPServer(("127.0.0.1", LOOPBACK_PORT), _LoopbackCallbackHandler)
    _LoopbackCallbackHandler.result = {}
    _LoopbackCallbackHandler.failure = None
    _LoopbackCallbackHandler.allowed_origin = allowed_origin
    _LoopbackCallbackHandler.done.clear()
    _LoopbackCallbackHandler.settled.clear()
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True)
    thread.start()

    def settle(failure: str | None) -> None:
        _LoopbackCallbackHandler.failure = failure
        _LoopbackCallbackHandler.settled.set()
        server.shutdown()
        server.server_close()
        thread.join(SETTLE_TIMEOUT)

    try:
        await asyncio.wait_for(asyncio.to_thread(_LoopbackCallbackHandler.done.wait), timeout)
    except BaseException:
        settle("the CLI stopped waiting")
        raise

    return _LoopbackCallbackHandler.result, settle


async def browser_login(consent_page: str | None = None, *, machine_id: str | None = None) -> OAuthTokens:
    """Open the web app's consent page and complete the loopback redirect flow.

    Args:
        consent_page: Full URL of the consent page. Defaults to
            :func:`consent_page_url`.
        machine_id: Opaque, stable id of this machine. When given it rides
            along in the consent page address, so the page can tell whether
            the machine is already paired. Never the raw hardware id.
    """
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(16)

    query = {
        "response_type": "code",
        "client_id": OAUTH_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": OAUTH_SCOPE,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if machine_id:
        query["machine_id"] = machine_id
    page = (consent_page or consent_page_url()).split("?", 1)[0]
    consent_url = f"{page}?" + urllib.parse.urlencode(query)

    _log.info("oauth_browser_opening", consent_url=consent_url)
    print(f"Sign-in page: {consent_url}")
    webbrowser.open(consent_url)

    callback, settle = await _wait_for_loopback_code(_origin_of(page))

    try:
        if callback.get("state") != state:
            raise ValueError("OAuth state mismatch — aborting")
        code = callback.get("code", "")
        if not code:
            error = callback.get("error", "unknown error")
            raise ValueError(f"authorization denied: {error}")

        tokens = await auth_service.exchange_code(code, verifier)
    except BaseException as error:
        settle(str(error) or error.__class__.__name__)
        raise

    settle(None)
    return tokens
