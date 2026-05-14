"""HTTP client for the Provably API."""

from typing import Any

import httpx
from config import Settings, get_settings
from logger import get_logger

from agentkit.intercept._self_egress import provably_self_egress

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

    async def _request(self, method: str, path: str, *, timeout: float = 60.0, **kwargs: Any) -> httpx.Response:
        with provably_self_egress():
            return await self._client.request(
                method, f"{self.base_url}{path}", headers=self._headers, timeout=timeout, **kwargs
            )

    async def _fetch(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._request(method, path, **kwargs)
            response.raise_for_status()

            if not response.content:
                return {}

            return response.json()

        except httpx.HTTPStatusError as e:
            # 400/500 errors from the server
            _log.error(
                "API rejected request: %s | Status: %s | Body: %s",
                path,
                e.response.status_code,
                e.response.text[:500],
            )
            raise
        except httpx.RequestError as e:
            # network issues
            _log.error("Network connectivity issue: %s | Error: %s", path, str(e))
            raise
        except httpx.HTTPError as e:
            # unexpected issues
            _log.exception("Unexpected error during request to %s | Error: %s", path, str(e))
            raise

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._fetch("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        return await self._fetch("POST", path, json=json or {})


# Global singleton instance
http = ProvablyHTTPClient()
