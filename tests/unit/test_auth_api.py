"""Tests for sourcerykit.provably._auth_api.ProvablyAuthAPI."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from sourcerykit.provably._auth_api import (
    OAUTH_CLIENT_ID,
    REDIRECT_URI,
    Organization,
    OrganizationType,
    ProvablyAuthAPI,
)

_TOKEN = "test-jwt-token"
_ORG = Organization(handle="my-org", name="My Org", organization_type=OrganizationType.EDUCATION)


def _make_api() -> tuple[ProvablyAuthAPI, MagicMock]:
    """Return a ProvablyAuthAPI with its _http client fully mocked."""
    with patch("sourcerykit.provably._auth_api.ProvablyHTTPClient"):
        api = ProvablyAuthAPI()

    mock_http = MagicMock()
    api._http = mock_http
    return api, mock_http


class TestProvablyAuthAPIOAuth:
    async def test_exchange_code_posts_form(self) -> None:
        api, mock_http = _make_api()
        mock_http.post_form = AsyncMock(return_value={"access_token": "at", "refresh_token": "rt"})

        result = await api.exchange_code("CODE", "VERIFIER")

        mock_http.post_form.assert_called_once_with(
            "/api/v1/auth/oauth/token",
            {
                "grant_type": "authorization_code",
                "code": "CODE",
                "redirect_uri": REDIRECT_URI,
                "client_id": OAUTH_CLIENT_ID,
                "code_verifier": "VERIFIER",
            },
        )
        assert result == {"access_token": "at", "refresh_token": "rt"}

    async def test_refresh_tokens_posts_form(self) -> None:
        api, mock_http = _make_api()
        mock_http.post_form = AsyncMock(return_value={"access_token": "new-at", "refresh_token": "new-rt"})

        result = await api.refresh_tokens("old-rt")

        mock_http.post_form.assert_called_once_with(
            "/api/v1/auth/oauth/refresh",
            {
                "grant_type": "refresh_token",
                "refresh_token": "old-rt",
                "client_id": OAUTH_CLIENT_ID,
            },
        )
        assert result == {"access_token": "new-at", "refresh_token": "new-rt"}


class TestProvablyAuthAPIUser:
    async def test_get_current_user_calls_get_with_token(self) -> None:
        api, mock_http = _make_api()
        mock_http.get = AsyncMock(return_value={"email": "user@example.com"})

        result = await api.get_current_user(_TOKEN)

        mock_http.get.assert_called_once_with("/api/v1/user/current", token=_TOKEN)
        assert result == {"email": "user@example.com"}


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
