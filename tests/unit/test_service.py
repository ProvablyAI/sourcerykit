"""Tests for sourcerykit.provably.service.ProvablyService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sourcerykit.provably._errors import ProvablyAPIError, ProvablyConnectionError
from sourcerykit.provably.service import ProvablyService


def _make_service() -> tuple[ProvablyService, MagicMock]:
    """Return a ProvablyService with a mocked API."""
    service = ProvablyService()
    mock_api = MagicMock()
    return service, mock_api


# ---------------------------------------------------------------------------
# create_feedback
# ---------------------------------------------------------------------------


class TestProvablyServiceCreateFeedback:
    async def test_success_without_file(self) -> None:
        service, mock_api = _make_service()
        mock_api.create_feedback = AsyncMock(return_value=None)

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            await service.create_feedback("Great product!", None)

        mock_api.create_feedback.assert_called_once_with(
            {"description": "Great product!"},
            files={},
        )

    async def test_success_with_file(self) -> None:
        service, mock_api = _make_service()
        mock_api.create_feedback = AsyncMock(return_value=None)
        file_bytes = b"some file content"

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            await service.create_feedback("Bug report", file_bytes)

        mock_api.create_feedback.assert_called_once_with(
            {"description": "Bug report"},
            files={"files": ("attachment.dat", file_bytes)},
        )

    async def test_api_error(self) -> None:
        service, mock_api = _make_service()
        mock_request = httpx.Request("POST", "https://api.provably.ai/api/v1/feedback")
        mock_response = httpx.Response(500, request=mock_request, text="Internal Server Error")
        mock_api.create_feedback = AsyncMock(
            side_effect=httpx.HTTPStatusError("500", request=mock_request, response=mock_response)
        )

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyAPIError):
                await service.create_feedback("test", None)


# ---------------------------------------------------------------------------
# list_collections
# ---------------------------------------------------------------------------


class TestProvablyServiceListCollections:
    async def test_returns_list(self) -> None:
        service, mock_api = _make_service()
        collections = [{"id": str(uuid.uuid4()), "name": "my-project"}]
        mock_api.list_collections = AsyncMock(return_value=collections)

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            result = await service.list_collections()

        assert result == collections

    async def test_returns_empty_list(self) -> None:
        service, mock_api = _make_service()
        mock_api.list_collections = AsyncMock(return_value=[])

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            result = await service.list_collections()

        assert result == []

    async def test_api_error(self) -> None:
        service, mock_api = _make_service()
        mock_request = httpx.Request("GET", "https://api.provably.ai/api/v1/collections")
        mock_response = httpx.Response(403, request=mock_request, text="Forbidden")
        mock_api.list_collections = AsyncMock(
            side_effect=httpx.HTTPStatusError("403", request=mock_request, response=mock_response)
        )

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyAPIError):
                await service.list_collections()


# ---------------------------------------------------------------------------
# get_integration_by_id
# ---------------------------------------------------------------------------


class TestProvablyServiceGetIntegrationById:
    async def test_returns_record(self) -> None:
        service, mock_api = _make_service()
        integration_id = uuid.uuid4()
        record = {"id": str(integration_id), "name": "my-integration", "api_key": "key-123"}
        mock_api.get_integration_by_id = AsyncMock(return_value=record)

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            result = await service.get_integration_by_id(integration_id)

        assert result == record
        mock_api.get_integration_by_id.assert_called_once_with(integration_id)

    async def test_api_error(self) -> None:
        service, mock_api = _make_service()
        integration_id = uuid.uuid4()
        mock_request = httpx.Request("GET", f"https://api.provably.ai/api/v1/integrations/{integration_id}")
        mock_response = httpx.Response(404, request=mock_request, text="Not Found")
        mock_api.get_integration_by_id = AsyncMock(
            side_effect=httpx.HTTPStatusError("404", request=mock_request, response=mock_response)
        )

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyAPIError):
                await service.get_integration_by_id(integration_id)

    async def test_connection_error(self) -> None:
        service, mock_api = _make_service()
        integration_id = uuid.uuid4()
        mock_request = httpx.Request("GET", f"https://api.provably.ai/api/v1/integrations/{integration_id}")
        mock_api.get_integration_by_id = AsyncMock(side_effect=httpx.ConnectError("unreachable", request=mock_request))

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyConnectionError):
                await service.get_integration_by_id(integration_id)
