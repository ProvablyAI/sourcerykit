"""Tests for sourcerykit.provably.auth_service.ProvablyAuthService."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sourcerykit.provably._auth_api import OAuthTokens, Organization, OrganizationType
from sourcerykit.provably._errors import (
    ProvablyConnectionError,
    ProvablyResourceAlreadyExistsError,
    ProvablyUnauthorizedError,
)
from sourcerykit.provably.auth_service import ProvablyAuthService

_TOKEN = "test-jwt-token"
_ORG = Organization(handle="my-org", name="My Org", organization_type=OrganizationType.EDUCATION)
_ORG_ID = uuid.uuid4()


def _make_service() -> tuple[ProvablyAuthService, MagicMock]:
    """Return a ProvablyAuthService with `get_api` patched to a mock."""
    service = ProvablyAuthService()
    mock_api = MagicMock()
    return service, mock_api


class TestProvablyAuthServiceOAuth:
    async def test_exchange_code_returns_tokens(self) -> None:
        service, mock_api = _make_service()
        mock_api.exchange_code = AsyncMock(return_value={"access_token": "at", "refresh_token": "rt"})

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            result = await service.exchange_code("CODE", "VERIFIER")

        assert isinstance(result, OAuthTokens)
        assert result.access_token == "at"
        assert result.refresh_token == "rt"

    async def test_refresh_tokens_rotates(self) -> None:
        service, mock_api = _make_service()
        mock_api.refresh_tokens = AsyncMock(return_value={"access_token": "new-at", "refresh_token": "new-rt"})

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            result = await service.refresh_tokens("old-rt")

        assert result.access_token == "new-at"
        assert result.refresh_token == "new-rt"


class TestProvablyAuthServiceUserEmail:
    async def test_returns_email(self) -> None:
        service, mock_api = _make_service()
        mock_api.get_current_user = AsyncMock(return_value={"email": "user@example.com"})

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            result = await service.get_user_email(_TOKEN)

        assert result == "user@example.com"

    async def test_missing_email_raises_data_error(self) -> None:
        from sourcerykit.provably._errors import ProvablyDataError

        service, mock_api = _make_service()
        mock_api.get_current_user = AsyncMock(return_value={})

        with patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api):
            with pytest.raises(ProvablyDataError):
                await service.get_user_email(_TOKEN)


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


class TestProvablyAuthServiceListOrganizations:
    async def test_returns_list(self) -> None:
        service, mock_api = _make_service()
        orgs = [{"id": str(_ORG_ID), "name": "My Org"}]
        mock_main_api = MagicMock()
        mock_main_api.list_organizations = AsyncMock(return_value=orgs)

        with (
            patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api),
            patch("sourcerykit.provably.auth_service.get_main_api", return_value=mock_main_api),
        ):
            result = await service.list_organizations()

        assert result == orgs

    async def test_returns_empty_list(self) -> None:
        service, mock_api = _make_service()
        mock_main_api = MagicMock()
        mock_main_api.list_organizations = AsyncMock(return_value=[])

        with (
            patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api),
            patch("sourcerykit.provably.auth_service.get_main_api", return_value=mock_main_api),
        ):
            result = await service.list_organizations()

        assert result == []

    async def test_connection_error(self) -> None:
        service, mock_api = _make_service()
        mock_main_api = MagicMock()
        req = httpx.Request("GET", "https://api.provably.ai/api/v1/organizations")
        mock_main_api.list_organizations = AsyncMock(side_effect=httpx.ConnectError("refused", request=req))

        with (
            patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api),
            patch("sourcerykit.provably.auth_service.get_main_api", return_value=mock_main_api),
        ):
            with pytest.raises(ProvablyConnectionError):
                await service.list_organizations()

    async def test_unauthorized(self) -> None:
        service, mock_api = _make_service()
        mock_main_api = MagicMock()
        mock_request = httpx.Request("GET", "https://api.provably.ai/api/v1/organizations")
        mock_response = httpx.Response(401, request=mock_request, text="Unauthorized")
        mock_main_api.list_organizations = AsyncMock(
            side_effect=httpx.HTTPStatusError("401", request=mock_request, response=mock_response)
        )

        with (
            patch("sourcerykit.provably.auth_service.get_api", return_value=mock_api),
            patch("sourcerykit.provably.auth_service.get_main_api", return_value=mock_main_api),
        ):
            with pytest.raises(ProvablyUnauthorizedError):
                await service.list_organizations()
