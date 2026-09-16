"""Tests for sourcerykit.provably.service.ProvablyService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sourcerykit.provably._errors import ProvablyAPIError, ProvablyDataError
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
# ensure_integration
# ---------------------------------------------------------------------------


class TestProvablyServiceEnsureIntegration:
    async def test_returns_id_and_key(self) -> None:
        service, mock_api = _make_service()
        collection_id = uuid.uuid4()
        integration_id = uuid.uuid4()
        mock_api.ensure_integration = AsyncMock(
            return_value={"id": str(integration_id), "api_key": "i-zk-key-123", "collections": [str(collection_id)]}
        )

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            result = await service.ensure_integration(collection_id)

        assert result == (integration_id, "i-zk-key-123")
        call_body = mock_api.ensure_integration.call_args.args[0]
        assert call_body["collections"] == [str(collection_id)]

    async def test_missing_key_raises_data_error(self) -> None:
        service, mock_api = _make_service()
        mock_api.ensure_integration = AsyncMock(return_value={"id": str(uuid.uuid4())})

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyDataError):
                await service.ensure_integration(uuid.uuid4())
