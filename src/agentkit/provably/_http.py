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
        self._client = httpx.Client()

        s = settings or get_settings()

        self.base_url = s.provably_api.rstrip("/")
        self._headers = {
            "x-api-key": s.api_key,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, *, timeout: float = 60.0, **kwargs: Any) -> httpx.Response:
        with provably_self_egress():
            return self._client.request(
                method, f"{self.base_url}{path}", headers=self._headers, timeout=timeout, **kwargs
            )

    def _fetch(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._request(method, path, **kwargs)
        if resp.is_error:
            _log.error("http_error", status=resp.status_code, body=resp.text[:2000])
            raise httpx.HTTPStatusError(
                f"HTTP {resp.status_code}: {resp.text[:200]}",
                request=resp.request,
                response=resp,
            )
        return resp.json() if resp.content else None

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self._fetch("GET", path, params=params)

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self._fetch("POST", path, json=payload or {})


# Global singleton instance
http = ProvablyHTTPClient()
