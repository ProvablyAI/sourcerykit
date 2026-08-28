"""HTTP client for the Provably API."""

import asyncio
import functools
import json
from typing import Any

import httpx

from sourcerykit.config import (
    CONFIG_FILE,
    Settings,
    get_bootstrap_settings,
    get_settings,
    load_app_dir_config,
    save_app_dir_config,
)
from sourcerykit.intercept._self_egress import provably_self_egress
from sourcerykit.logger import get_logger

_log = get_logger(__name__)


async def _refresh_session() -> str | None:
    """Rotate the stored OAuth refresh token once; return the new access token.

    Returns None (and clears the stored refresh token) when no refresh token
    is configured or rotation fails.
    """
    from sourcerykit.provably.auth_service import auth_service

    refresh = load_app_dir_config().get("refresh_token")
    if not refresh:
        return None
    try:
        tokens = await auth_service.refresh_tokens(str(refresh))
    except Exception:
        _log.warning("oauth_refresh_failed", detail="dropping stored refresh token")
        payload = load_app_dir_config()
        payload.pop("refresh_token", None)
        CONFIG_FILE.write_text(json.dumps(payload))
        load_app_dir_config.cache_clear()
        get_settings.cache_clear()
        return None

    save_app_dir_config(token=tokens.access_token, refresh_token=tokens.refresh_token)
    return tokens.access_token


class ProvablyHTTPClient:
    """Httpx wrapper for the Provably API.

    All requests are wrapped in ``provably_self_egress()`` so SDK-internal
    traffic bypasses the trust gate and the intercept recorder.
    """

    def __init__(self, settings: Settings | None = None, *, pre_auth: bool = False) -> None:
        self._client: httpx.AsyncClient | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None

        if pre_auth:
            self.base_url = get_bootstrap_settings()
            self._headers = {"Content-Type": "application/json"}
        else:
            s = settings or get_settings()
            self.base_url = s.provably_api.rstrip("/")
            self._headers = {
                "x-api-key": s.api_key,
                "Content-Type": "application/json",
            }

    def _get_client(self) -> httpx.AsyncClient:
        """Return a shared AsyncClient, recreating it when the event loop has changed."""
        try:
            loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if self._client is None or self._client.is_closed or loop is not self._client_loop:
            self._client = httpx.AsyncClient()
            self._client_loop = loop

        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        timeout: float = 60.0,
        api_key: str | None = None,
        token: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:

        headers = {**self._headers}

        if "files" in kwargs or "data" in kwargs:
            headers.pop("Content-Type", None)

        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
            headers.pop("x-api-key", None)

        elif api_key is not None:
            headers["x-api-key"] = api_key

        with provably_self_egress():
            return await self._get_client().request(
                method, f"{self.base_url}{path}", headers=headers, timeout=timeout, **kwargs
            )

    async def _fetch(
        self,
        method: str,
        path: str,
        *,
        api_key: str | None = None,
        token: str | None = None,
        _oauth_retried: bool = False,
        **kwargs: Any,
    ) -> Any:
        # Sentinel kwarg guards the single refresh-retry; never forwarded to httpx.
        kwargs.pop("_oauth_retried", None)
        _log.debug("provably_api_request", method=method, path=path)
        try:
            response = await self._request(method, path, api_key=api_key, token=token, **kwargs)
            response.raise_for_status()

            if not response.content or not response.content.strip():
                return {}

            try:
                result = response.json()
                _log.debug("provably_api_response_ok", method=method, path=path, status=response.status_code)
                return result
            except ValueError:
                _log.debug(
                    "provably_api_response_not_json",
                    method=method,
                    path=path,
                    body=response.text[:200],
                )
                return {}

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401 and token is not None and not _oauth_retried:
                new_token = await _refresh_session()
                if new_token is not None:
                    _log.info("provably_api_token_refreshed", method=method, path=path)
                    return await self._fetch(
                        method, path, api_key=api_key, token=new_token, _oauth_retried=True, **kwargs
                    )
            _log.error(
                "provably_api_rejected",
                method=method,
                path=path,
                status_code=e.response.status_code,
                body=e.response.text[:500],
            )
            raise
        except httpx.RequestError as e:
            _log.error("provably_api_network_error", method=method, path=path, error=str(e))
            raise
        except httpx.HTTPError as e:
            _log.error("provably_api_unexpected_error", method=method, path=path, error=str(e))
            raise

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        api_key: str | None = None,
        token: str | None = None,
    ) -> Any:
        return await self._fetch("GET", path, api_key=api_key, token=token, params=params)

    async def get_raw(
        self,
        path: str,
        *,
        api_key: str | None = None,
        token: str | None = None,
    ) -> bytes:
        """GET that returns raw response bytes instead of parsed JSON."""
        _log.debug("provably_api_request_raw", method="GET", path=path)
        response = await self._request("GET", path, api_key=api_key, token=token)
        response.raise_for_status()
        return response.content

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        *,
        api_key: str | None = None,
        token: str | None = None,
    ) -> Any:
        return await self._fetch("POST", path, api_key=api_key, token=token, json=json or {})

    async def post_form(
        self,
        path: str,
        data: dict[str, Any],
        *,
        token: str | None = None,
    ) -> Any:
        """POST with an ``application/x-www-form-urlencoded`` body."""
        return await self._fetch("POST", path, token=token, data=data)

    async def post_multipart(
        self,
        path: str,
        data: dict[str, Any],
        *,
        files: dict[str, Any] | None = None,
        api_key: str | None = None,
        token: str | None = None,
    ) -> Any:
        processed_payload = {key: (None, str(value)) for key, value in data.items()}
        if files:
            processed_payload.update(files)
        return await self._fetch("POST", path, api_key=api_key, token=token, files=processed_payload)

    async def delete(
        self,
        path: str,
        *,
        api_key: str | None = None,
        token: str | None = None,
    ) -> Any:
        return await self._fetch("DELETE", path, api_key=api_key, token=token)


@functools.lru_cache(maxsize=1)
def get_http() -> ProvablyHTTPClient:
    """Return the shared :class:`ProvablyHTTPClient`, constructed on first call."""
    return ProvablyHTTPClient()
