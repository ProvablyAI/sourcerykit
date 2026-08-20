"""Tests for sourcerykit.provably.service — sandbox service methods."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcerykit.provably._errors import ProvablyDataError
from sourcerykit.provably.service import ProvablyService


def _make_service() -> tuple[ProvablyService, MagicMock]:
    """Return a ProvablyService with a mocked API."""
    service = ProvablyService()
    mock_api = MagicMock()
    return service, mock_api


# ---------------------------------------------------------------------------
# create_sandbox
# ---------------------------------------------------------------------------


class TestProvablyServiceCreateSandbox:
    async def test_returns_uri(self) -> None:
        service, mock_api = _make_service()
        org_id = uuid.uuid4()
        mock_api.create_sandbox = AsyncMock(
            return_value={"status": "active", "connection_uri": "postgresql://sandbox/db"}
        )

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            result = await service.create_sandbox(org_id)

        assert result == "postgresql://sandbox/db"

    async def test_missing_uri_raises(self) -> None:
        service, mock_api = _make_service()
        org_id = uuid.uuid4()
        mock_api.create_sandbox = AsyncMock(return_value={"status": "provisioning"})

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyDataError, match="connection_uri"):
                await service.create_sandbox(org_id)

    async def test_passes_token(self) -> None:
        service, mock_api = _make_service()
        org_id = uuid.uuid4()
        mock_api.create_sandbox = AsyncMock(return_value={"connection_uri": "postgresql://sandbox/db"})

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            await service.create_sandbox(org_id, token="jwt-abc")

        mock_api.create_sandbox.assert_called_once_with(org_id, token="jwt-abc")


# ---------------------------------------------------------------------------
# get_sandbox
# ---------------------------------------------------------------------------


class TestProvablyServiceGetSandbox:
    async def test_returns_sandbox_data(self) -> None:
        service, mock_api = _make_service()
        sandbox = {"status": "active", "connection_uri": "postgresql://sandbox/db"}
        mock_api.get_sandbox = AsyncMock(return_value=sandbox)

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            result = await service.get_sandbox()

        assert result == sandbox

    async def test_not_found_returns_none(self) -> None:
        service = ProvablyService()
        with patch.object(service, "get_sandbox", return_value=None):
            result = await service.get_sandbox()

        assert result is None


# ---------------------------------------------------------------------------
# get_sandbox_connection_uri
# ---------------------------------------------------------------------------


class TestProvablyServiceGetSandboxConnectionUri:
    async def test_active_returns_uri(self) -> None:
        service, mock_api = _make_service()
        mock_api.get_sandbox = AsyncMock(return_value={"status": "active", "connection_uri": "postgresql://sandbox/db"})

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            result = await service.get_sandbox_connection_uri()

        assert result == "postgresql://sandbox/db"

    async def test_provisioning_returns_uri(self) -> None:
        service, mock_api = _make_service()
        mock_api.get_sandbox = AsyncMock(
            return_value={"status": "provisioning", "connection_uri": "postgresql://sandbox/db"}
        )

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            result = await service.get_sandbox_connection_uri()

        assert result == "postgresql://sandbox/db"

    async def test_expired_returns_none(self) -> None:
        service, mock_api = _make_service()
        mock_api.get_sandbox = AsyncMock(
            return_value={"status": "expired", "connection_uri": "postgresql://sandbox/db"}
        )

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            result = await service.get_sandbox_connection_uri()

        assert result is None

    async def test_no_sandbox_returns_none(self) -> None:
        service = ProvablyService()
        with patch.object(service, "get_sandbox", return_value=None):
            result = await service.get_sandbox_connection_uri()

        assert result is None


# ---------------------------------------------------------------------------
# get_sandbox_status
# ---------------------------------------------------------------------------


class TestProvablyServiceGetSandboxStatus:
    async def test_matching_url_returns_true(self) -> None:
        service, mock_api = _make_service()
        uri = "postgresql://user:pass@sandbox.provably.ai:5432/mydb"
        mock_api.get_sandbox = AsyncMock(return_value={"status": "active", "connection_uri": uri})

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            sandbox, is_sandbox = await service.get_sandbox_status(uri)

        assert is_sandbox is True
        assert sandbox is not None
        assert sandbox["status"] == "active"

    async def test_different_url_returns_false(self) -> None:
        service, mock_api = _make_service()
        sandbox_uri = "postgresql://user:pass@sandbox.provably.ai:5432/mydb"
        personal_uri = "postgresql://user:pass@myhost:5432/mydb"
        mock_api.get_sandbox = AsyncMock(return_value={"status": "active", "connection_uri": sandbox_uri})

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            sandbox, is_sandbox = await service.get_sandbox_status(personal_uri)

        assert is_sandbox is False
        assert sandbox is not None

    async def test_no_sandbox_returns_none_false(self) -> None:
        service = ProvablyService()
        with patch.object(service, "get_sandbox", return_value=None):
            sandbox, is_sandbox = await service.get_sandbox_status("postgresql://host/db")

        assert sandbox is None
        assert is_sandbox is False


# ---------------------------------------------------------------------------
# delete_sandbox
# ---------------------------------------------------------------------------


class TestProvablyServiceDeleteSandbox:
    async def test_calls_api_delete(self) -> None:
        service, mock_api = _make_service()
        mock_api.delete_sandbox = AsyncMock(return_value=None)

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            await service.delete_sandbox()

        mock_api.delete_sandbox.assert_awaited_once()

    async def test_passes_token(self) -> None:
        service, mock_api = _make_service()
        mock_api.delete_sandbox = AsyncMock(return_value=None)

        with patch("sourcerykit.provably.service.get_api", return_value=mock_api):
            await service.delete_sandbox(token="jwt-del")

        mock_api.delete_sandbox.assert_called_once_with(token="jwt-del")
