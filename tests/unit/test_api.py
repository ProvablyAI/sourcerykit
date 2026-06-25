"""Tests for sourcerykit.provably._api.ProvablyAPI."""

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


class TestProvablyAPICreateFeedback:
    async def test_calls_post_multipart(self) -> None:
        api, _ = _make_api()
        mock_http = MagicMock()
        mock_http.post_multipart = AsyncMock()

        with patch("sourcerykit.provably._api.get_http", return_value=mock_http):
            await api.create_feedback({"description": "test"}, files={"file": ("f.txt", b"data")})

        mock_http.post_multipart.assert_called_once_with(
            "/api/v1/feedback",
            {"description": "test"},
            files={"file": ("f.txt", b"data")},
        )

    async def test_without_files(self) -> None:
        api, _ = _make_api()
        mock_http = MagicMock()
        mock_http.post_multipart = AsyncMock()

        with patch("sourcerykit.provably._api.get_http", return_value=mock_http):
            await api.create_feedback({"description": "test"})

        mock_http.post_multipart.assert_called_once_with(
            "/api/v1/feedback",
            {"description": "test"},
            files=None,
        )


class TestProvablyAPIListOrganizations:
    async def test_returns_list(self) -> None:
        api, _ = _make_api()
        orgs = [{"id": str(uuid.uuid4()), "name": "Org1"}]
        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value=orgs)

        with patch("sourcerykit.provably._api.get_http", return_value=mock_http):
            result = await api.list_organizations()

        assert result == orgs
        mock_http.get.assert_called_once_with("/api/v1/organizations")

    async def test_returns_empty_list(self) -> None:
        api, _ = _make_api()
        mock_http = MagicMock()
        mock_http.get = AsyncMock(return_value=[])

        with patch("sourcerykit.provably._api.get_http", return_value=mock_http):
            result = await api.list_organizations()

        assert result == []
