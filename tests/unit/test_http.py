"""Tests for sourcerykit.provably._http.ProvablyHTTPClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sourcerykit.config import Settings
from sourcerykit.provably._http import ProvablyHTTPClient

_ORG = "00000000-0000-0000-0000-000000000001"


def _make_settings(api_url: str = "https://api.provably.ai") -> Settings:
    import uuid

    return Settings(
        api_key="test-api-key",
        org_id=uuid.UUID(_ORG),
        postgres_url="postgresql://user:pass@localhost/db",
        provably_api=api_url,
    )


def _make_client(api_url: str = "https://api.provably.ai") -> ProvablyHTTPClient:
    return ProvablyHTTPClient(settings=_make_settings(api_url))


class TestProvablyHTTPClientInit:
    def test_base_url_stripped_of_trailing_slash(self) -> None:
        client = _make_client("https://api.provably.ai/")
        assert client.base_url == "https://api.provably.ai"

    def test_headers_include_api_key(self) -> None:
        client = _make_client()
        assert client._headers["x-api-key"] == "test-api-key"

    def test_headers_include_content_type(self) -> None:
        client = _make_client()
        assert client._headers["Content-Type"] == "application/json"


class TestProvablyHTTPClientGet:
    async def test_get_returns_parsed_json(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.content = b'{"result": "ok"}'
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": "ok"}

        with patch.object(client, "_request", AsyncMock(return_value=mock_response)):
            result = await client.get("/test-path")
        assert result == {"result": "ok"}

    async def test_get_raises_on_http_status_error(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        error = httpx.HTTPStatusError("404", request=MagicMock(), response=mock_response)

        with patch.object(client, "_request", AsyncMock(side_effect=error)):
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("/missing")

    async def test_get_passes_params(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.content = b"{}"
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}

        with patch.object(client, "_request", AsyncMock(return_value=mock_response)) as mock_req:
            await client.get("/path", params={"key": "val"})
            _, kwargs = mock_req.call_args
            assert kwargs.get("params") == {"key": "val"}


class TestProvablyHTTPClientPost:
    async def test_post_returns_empty_dict_on_empty_body(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_request", AsyncMock(return_value=mock_response)):
            result = await client.post("/some/path", json={"payload": "data"})
        assert result == {}

    async def test_post_with_custom_api_key(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.content = b'{"ok": true}'
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"ok": True}

        with patch.object(client, "_request", AsyncMock(return_value=mock_response)) as mock_req:
            await client.post("/path", json={}, api_key="custom-key")
            _, kwargs = mock_req.call_args
            assert kwargs.get("api_key") == "custom-key"
