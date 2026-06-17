"""Tests for sourcerykit.provably.auth_service.ProvablyAuthService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sourcerykit.provably._auth_api import Organization, OrganizationType, User
from sourcerykit.provably._errors import (
    ProvablyConnectionError,
    ProvablyResourceAlreadyExistsError,
    ProvablyUnauthorizedError,
)
from sourcerykit.provably.auth_service import ProvablyAuthService

_TOKEN = "test-jwt-token"
_USER = User(email="user@example.com", password="secret")
_ORG = Organization(handle="my-org", name="My Org", organization_type=OrganizationType.EDUCATION)
_ORG_ID = uuid.uuid4()


def _make_service() -> tuple[ProvablyAuthService, MagicMock]:
    """Return a ProvablyAuthService with `get_api` patched to a mock."""
    service = ProvablyAuthService()
    mock_api = MagicMock()
    return service, mock_api


class TestProvablyAuthServiceAccount:
    async def test_create_account_happy_path(self) -> None:
        service, mock_api = _make_service()
        mock_api.create_account = AsyncMock(return_value=None)

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            await service.create_account(_USER)

        mock_api.create_account.assert_called_once_with(_USER)

    async def test_create_account_connection_error(self) -> None:
        service, mock_api = _make_service()
        req = httpx.Request("POST", "https://api.provably.ai/api/v1/auth/register")
        mock_api.create_account = AsyncMock(side_effect=httpx.ConnectError("refused", request=req))

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyConnectionError):
                await service.create_account(_USER)

    async def test_login_happy_path(self) -> None:
        service, mock_api = _make_service()
        mock_api.login = AsyncMock(return_value={"token": "abc123"})

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            result = await service.login(_USER)

        assert result == {"token": "abc123"}

    async def test_login_unauthorized_raises_error(self) -> None:
        service, mock_api = _make_service()
        mock_request = httpx.Request("POST", "https://api.provably.ai/api/v1/auth/login")
        mock_response = httpx.Response(401, request=mock_request, text="Unauthorized")
        mock_api.login = AsyncMock(
            side_effect=httpx.HTTPStatusError("401", request=mock_request, response=mock_response)
        )

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyUnauthorizedError):
                await service.login(_USER)

    async def test_login_connection_error(self) -> None:
        service, mock_api = _make_service()
        req = httpx.Request("POST", "https://api.provably.ai/api/v1/auth/login")
        mock_api.login = AsyncMock(side_effect=httpx.ConnectError("refused", request=req))

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyConnectionError):
                await service.login(_USER)


class TestProvablyAuthServiceApiKey:
    async def test_get_api_key_returns_string(self) -> None:
        service, mock_api = _make_service()
        mock_api.get_api_key = AsyncMock(return_value={"api_key": "my-key-abc"})

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            result = await service.get_api_key(_TOKEN)

        assert result == "my-key-abc"

    async def test_get_api_key_missing_key_raises_data_error(self) -> None:
        from sourcerykit.provably._errors import ProvablyDataError

        service, mock_api = _make_service()
        mock_api.get_api_key = AsyncMock(return_value={})

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyDataError):
                await service.get_api_key(_TOKEN)


class TestProvablyAuthServiceOrganization:
    async def test_create_organization_returns_uuid(self) -> None:
        service, mock_api = _make_service()
        mock_api.create_organization = AsyncMock(return_value={"id": str(_ORG_ID)})

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            result = await service.create_organization(_TOKEN, _ORG)

        assert result == _ORG_ID

    async def test_create_organization_already_exists_raises_error(self) -> None:
        service, mock_api = _make_service()
        mock_request = httpx.Request("POST", "https://api.provably.ai/api/v1/organizations")
        mock_response = httpx.Response(409, request=mock_request, text="Conflict")
        mock_api.create_organization = AsyncMock(
            side_effect=httpx.HTTPStatusError("409", request=mock_request, response=mock_response)
        )

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyResourceAlreadyExistsError):
                await service.create_organization(_TOKEN, _ORG)

    async def test_get_organizations_returns_list(self) -> None:
        orgs = [{"id": str(_ORG_ID), "name": "My Org"}]
        service, mock_api = _make_service()
        mock_api.get_organizations = AsyncMock(return_value=orgs)

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            result = await service.get_organizations(_TOKEN)

        assert result == orgs

    async def test_get_organizations_returns_empty_list(self) -> None:
        service, mock_api = _make_service()
        mock_api.get_organizations = AsyncMock(return_value=[])

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            result = await service.get_organizations(_TOKEN)

        assert result == []
