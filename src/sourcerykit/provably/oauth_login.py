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
import os
import secrets
import threading
import urllib.parse
import webbrowser
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
    """Captures ?code/&state on GET /callback and signals completion."""

    result: dict[str, str] = {}
    done = threading.Event()

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        parsed = urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query)
        type(self).result = dict(parsed)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h2>Logged in!</h2>You can close this window.</body></html>")
        type(self).done.set()

    def log_message(self, format: str, *args: object) -> None:  # silence stderr
        pass


async def _wait_for_loopback_code(timeout: float = 300.0) -> dict[str, str]:
    """Bind the registered loopback port and wait for the OAuth redirect."""
    server = HTTPServer(("127.0.0.1", LOOPBACK_PORT), _LoopbackCallbackHandler)
    _LoopbackCallbackHandler.result = {}
    _LoopbackCallbackHandler.done.clear()
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True)
    thread.start()
    try:
        await asyncio.wait_for(asyncio.to_thread(_LoopbackCallbackHandler.done.wait), timeout)
    finally:
        server.shutdown()
        server.server_close()
    return _LoopbackCallbackHandler.result


async def browser_login(consent_page: str | None = None) -> OAuthTokens:
    """Open the web app's consent page and complete the loopback redirect flow.

    Args:
        consent_page: Full URL of the consent page. Defaults to
            :func:`consent_page_url`.
    """
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(16)

    page = (consent_page or consent_page_url()).split("?", 1)[0]
    consent_url = f"{page}?" + urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": OAUTH_CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": OAUTH_SCOPE,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )

    _log.info("oauth_browser_opening", consent_url=consent_url)
    webbrowser.open(consent_url)

    callback = await _wait_for_loopback_code()
    if callback.get("state") != state:
        raise ValueError("OAuth state mismatch — aborting")
    code = callback.get("code", "")
    if not code:
        error = callback.get("error", "unknown error")
        raise ValueError(f"authorization denied: {error}")

    return await auth_service.exchange_code(code, verifier)
