"""Glue between sourcerykit and the Provably SDK (``provably-sdk``).

The SDK reads nothing on its own; this module tells it where sourcerykit keeps
its settings and session, and exempts the SDK's traffic from the interceptor.
It configures the SDK on import, which ``sourcerykit/__init__`` does first.
"""

import json
import os

import provably
from dotenv import set_key
from provably import OAuthTokens, ProvablyConfig

from sourcerykit.config import (
    CONFIG_FILE,
    get_bootstrap_app_url,
    get_bootstrap_settings,
    get_settings,
    load_app_dir_config,
    load_local_env,
    save_app_dir_config,
)
from sourcerykit.errors import SourceryKitConfigError
from sourcerykit.intercept._self_egress import provably_self_egress

# The OAuth client sourcerykit is registered as, and the loopback port it listens on.
OAUTH_CLIENT_ID = "sourcerykit-cli"
OAUTH_LOOPBACK_PORT = 8910
# The web app's consent page
DEFAULT_CONSENT_URL = "https://switchboard-app.provably.ai/consent"


def _token_store() -> str | None:
    """Return the app's token-store path (SOURCERYKIT_TOKEN_STORE) or None for global JSON.

    Resolved per-call so the app can set it at startup regardless of import order.
    """
    return os.getenv("SOURCERYKIT_TOKEN_STORE") or None


class SourceryKitTokenStore:
    """The session in sourcerykit's global JSON, or in an embedding app's ``.env``."""

    def load(self) -> OAuthTokens | None:
        # Raises SourceryKitConfigError when sourcerykit is not set up, as before the SDK split.
        settings = get_settings()
        # sourcerykit only ever signs in as its own client, so its tokens are that client's.
        return OAuthTokens(
            access_token=settings.access_token,
            refresh_token=settings.refresh_token or None,
            client_id=OAUTH_CLIENT_ID,
        )

    def save(self, tokens: OAuthTokens) -> None:
        store = _token_store()
        if store:
            set_key(store, "PROVABLY_ACCESS_TOKEN", tokens.access_token)
            set_key(store, "PROVABLY_REFRESH_TOKEN", tokens.refresh_token or "")
            os.environ["PROVABLY_ACCESS_TOKEN"] = tokens.access_token
            if tokens.refresh_token:
                os.environ["PROVABLY_REFRESH_TOKEN"] = tokens.refresh_token
            load_local_env.cache_clear()
        else:
            save_app_dir_config(token=tokens.access_token, refresh_token=tokens.refresh_token)
        get_settings.cache_clear()

    def clear_refresh_token(self) -> None:
        store = _token_store()
        if store:
            set_key(store, "PROVABLY_REFRESH_TOKEN", "")
            os.environ.pop("PROVABLY_REFRESH_TOKEN", None)
            load_local_env.cache_clear()
        else:
            payload = load_app_dir_config()
            payload.pop("refresh_token", None)
            CONFIG_FILE.write_text(json.dumps(payload))
            load_app_dir_config.cache_clear()
        get_settings.cache_clear()


def sdk_config() -> ProvablyConfig:
    """sourcerykit's settings as the SDK's; before setup, the API and app URLs alone."""
    try:
        settings = get_settings()
    except SourceryKitConfigError:
        return ProvablyConfig(api_url=get_bootstrap_settings(), app_url=get_bootstrap_app_url())
    return ProvablyConfig(api_url=settings.provably_api, app_url=settings.provably_app, org_id=settings.org_id)


def consent_page_url() -> str:
    """URL of the web app consent page: ``SOURCERYKIT_CONSENT_URL``, else production.

    A setting of its own, not ``SOURCERYKIT_PROVABLY_APP_URL``: that one is the
    base of the app's query-record links, which a consent page URL would break.
    """
    return (os.environ.get("SOURCERYKIT_CONSENT_URL") or "").strip() or DEFAULT_CONSENT_URL


provably.configure(config=sdk_config, tokens=SourceryKitTokenStore(), egress=provably_self_egress)
