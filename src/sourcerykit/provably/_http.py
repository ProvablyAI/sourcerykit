"""HTTP client for the Provably API."""

import functools
from typing import Any

import httpx

from sourcerykit.config import Settings, get_settings
from sourcerykit.intercept._self_egress import provably_self_egress
from sourcerykit.logger import get_logger

_log = get_logger(__name__)


class ProvablyHTTPClient:
    """Httpx wrapper for the Provably API.

    All requests are wrapped in ``provably_self_egress()`` so SDK-internal
    traffic bypasses the trust gate and the intercept recorder.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._client = httpx.AsyncClient()

        s = settings or get_settings()

        self.base_url = s.provably_api.rstrip("/")
        self._headers = {
            "x-api-key": s.api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, path: str, *, timeout: float = 60.0, api_key: str | None = None, **kwargs: Any
    ) -> httpx.Response:
        headers = self._headers if api_key is None else {**self._headers, "x-api-key": api_key}
        with provably_self_egress():
            return await self._client.request(
                method, f"{self.base_url}{path}", headers=headers, timeout=timeout, **kwargs
            )

    async def _fetch(self, method: str, path: str, *, api_key: str | None = None, **kwargs: Any) -> Any:
        _log.debug("provably_api_request", method=method, path=path)
        try:
            response = await self._request(method, path, api_key=api_key, **kwargs)
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

    async def get(self, path: str, params: dict[str, Any] | None = None, *, api_key: str | None = None) -> Any:
        return await self._fetch("GET", path, api_key=api_key, params=params)

    async def post(self, path: str, json: dict[str, Any] | None = None, *, api_key: str | None = None) -> Any:
        return await self._fetch("POST", path, api_key=api_key, json=json or {})


@functools.lru_cache(maxsize=1)
def get_http() -> ProvablyHTTPClient:
    """Return the shared :class:`ProvablyHTTPClient`, constructed on first call."""
    return ProvablyHTTPClient()
