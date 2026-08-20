"""Tests for sourcerykit.provably._api — sandbox API methods."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from sourcerykit.provably._api import ProvablyAPI


def _make_api() -> tuple[ProvablyAPI, MagicMock]:
    """Return a ProvablyAPI with mocked settings and HTTP client."""
    settings = MagicMock()
    settings.org_id = uuid.uuid4()
    settings.provably_app = "https://app.provably.ai"
    api = ProvablyAPI(settings=settings)
    return api, settings


# ---------------------------------------------------------------------------
# create_sandbox
# ---------------------------------------------------------------------------


class TestProvablyAPICreateSandbox:
    async def test_posts_org_id(self) -> None:
        api, settings = _make_api()
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={"status": "active", "connection_uri": "postgresql://sandbox/db"})

        with patch("sourcerykit.provably._api.get_http", return_value=mock_http):
            result = await api.create_sandbox(settings.org_id)

        mock_http.post.assert_called_once_with(
            "/api/v1/sandboxes",
            {"org_id": str(settings.org_id)},
            token=None,
        )
        assert result["status"] == "active"

    async def test_passes_token(self) -> None:
        api, settings = _make_api()
        mock_http = MagicMock()
        mock_http.post = AsyncMock(return_value={"status": "provisioning"})

        with patch("sourcerykit.provably._api.get_http", return_value=mock_http):
            await api.create_sandbox(settings.org_id, token="jwt-abc")

        mock_http.post.assert_called_once_with(
            "/api/v1/sandboxes",
            {"org_id": str(settings.org_id)},
            token="jwt-abc",
        )


# ---------------------------------------------------------------------------
# get_sandbox
# ---------------------------------------------------------------------------


class TestProvablyAPIGetSandbox:
    async def test_returns_sandbox_record(self) -> None:
        api, _ = _make_api()
        mock_http = MagicMock()
        sandbox = {"status": "active", "connection_uri": "postgresql://sandbox/db"}
        mock_http.get = AsyncMock(return_value=sandbox)

        with patch("sourcerykit.provably._api.get_http", return_value=mock_http):
            result = await api.get_sandbox()

        mock_http.get.assert_called_once_with("/api/v1/sandboxes", token=None)
        assert result == sandbox

    async def test_passes_token(self) -> None:
        api, _ = _make_api()
        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value={})

        with patch("sourcerykit.provably._api.get_http", return_value=mock_http):
            await api.get_sandbox(token="jwt-xyz")

        mock_http.get.assert_called_once_with("/api/v1/sandboxes", token="jwt-xyz")


# ---------------------------------------------------------------------------
# delete_sandbox
# ---------------------------------------------------------------------------


class TestProvablyAPIDeleteSandbox:
    async def test_calls_delete(self) -> None:
        api, _ = _make_api()
        mock_http = MagicMock()
        mock_http.delete = AsyncMock(return_value=None)

        with patch("sourcerykit.provably._api.get_http", return_value=mock_http):
            await api.delete_sandbox()

        mock_http.delete.assert_called_once_with("/api/v1/sandboxes", token=None)

    async def test_passes_token(self) -> None:
        api, _ = _make_api()
        mock_http = MagicMock()
        mock_http.delete = AsyncMock(return_value=None)

        with patch("sourcerykit.provably._api.get_http", return_value=mock_http):
            await api.delete_sandbox(token="jwt-del")

        mock_http.delete.assert_called_once_with("/api/v1/sandboxes", token="jwt-del")
