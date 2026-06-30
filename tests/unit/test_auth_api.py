"""Tests for sourcerykit.provably._auth_api.ProvablyAuthAPI."""

import uuid
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

from sourcerykit.provably._auth_api import (
    Organization,
    OrganizationType,
    ProvablyAuthAPI,
    User,
)

_TOKEN = "test-jwt-token"
_USER = User(email="user@example.com", password="secret")
_ORG = Organization(handle="my-org", name="My Org", organization_type=OrganizationType.EDUCATION)


def _make_api() -> tuple[ProvablyAuthAPI, MagicMock]:
    """Return a ProvablyAuthAPI with its _http client fully mocked."""
    with patch("sourcerykit.provably._auth_api.ProvablyHTTPClient"):
        api = ProvablyAuthAPI()

    mock_http = MagicMock()
    api._http = mock_http
    return api, mock_http


class TestProvablyAuthAPIAccount:
    async def test_create_account_calls_post_register(self) -> None:
        api, mock_http = _make_api()
        mock_http.post = AsyncMock(return_value={})

        await api.create_account(_USER)

        mock_http.post.assert_called_once_with(
            "/api/v1/auth/register",
            asdict(_USER),
        )

    async def test_login_calls_post_login_and_returns_dict(self) -> None:
        api, mock_http = _make_api()
        mock_http.post = AsyncMock(return_value={"token": "abc123"})

        result = await api.login(_USER)

        mock_http.post.assert_called_once_with(
            "/api/v1/auth/login",
            asdict(_USER),
        )
        assert result == {"token": "abc123"}


class TestProvablyAuthAPIApiKey:
    async def test_get_api_key_calls_get_with_token(self) -> None:
        api, mock_http = _make_api()
        mock_http.get = AsyncMock(return_value={"api_key": "key-xyz"})

        result = await api.get_api_key(_TOKEN)

        mock_http.get.assert_called_once_with("/api/v1/user/key", token=_TOKEN)
        assert result == {"api_key": "key-xyz"}


class TestProvablyAuthAPIOrganization:
    async def test_create_organization_calls_post_multipart_with_token(self) -> None:
        org_id = str(uuid.uuid4())
        api, mock_http = _make_api()
        mock_http.post_multipart = AsyncMock(return_value={"id": org_id})

        result = await api.create_organization(_TOKEN, _ORG)

        mock_http.post_multipart.assert_called_once_with(
            "/api/v1/organizations",
            {
                "handle": _ORG.handle,
                "name": _ORG.name,
                "type": _ORG.organization_type.value,
            },
            token=_TOKEN,
        )
        assert result == {"id": org_id}

    async def test_get_organizations_calls_get_with_token(self) -> None:
        orgs = [{"id": str(uuid.uuid4()), "name": "My Org"}]
        api, mock_http = _make_api()
        mock_http.get = AsyncMock(return_value=orgs)

        result = await api.get_organizations(_TOKEN)

        mock_http.get.assert_called_once_with("/api/v1/organizations", token=_TOKEN)
        assert result == orgs

    async def test_get_organizations_returns_empty_list(self) -> None:
        api, mock_http = _make_api()
        mock_http.get = AsyncMock(return_value=[])

        result = await api.get_organizations(_TOKEN)

        assert result == []
