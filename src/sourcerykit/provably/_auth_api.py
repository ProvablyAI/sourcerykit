"""Provably Auth API — OAuth tokens, user, API key and organisation endpoints.

:class:`ProvablyAuthAPI` covers four resource groups:
- **OAuth** — exchange an authorization code and rotate refresh tokens
- **User** — retrieve the current authenticated user
- **API Key** — retrieve the API key for the authenticated user
- **Organisations** — create and list organisations

The browser OAuth flow itself lives in
:mod:`sourcerykit.provably.oauth_login`.
"""

import functools
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sourcerykit.provably._http import ProvablyHTTPClient

OAUTH_CLIENT_ID = "sourcerykit-cli"
OAUTH_SCOPE = "read write"
LOOPBACK_PORT = 8910
REDIRECT_URI = f"http://127.0.0.1:{LOOPBACK_PORT}/callback"


@dataclass(slots=True)
class OAuthTokens:
    """Tokens issued by the OAuth token endpoint."""

    access_token: str
    refresh_token: str | None


class OrganizationType(StrEnum):
    DEMOGRAPHICS = "demographics"
    E_COMMERCE = "e-commerce"
    SOCIAL_MEDIA = "social-media"
    HEALTH_AND_FITNESS = "health-and-fitness"
    CLIMATE_AND_WEATHER = "climate-and-weather"
    EDUCATION = "education"
    FINANCIAL = "financial"
    REAL_ESTATE = "real-estate"
    ENERGY_CONSUMPTION = "energy-consumption"
    SPORTS = "sports"
    RETAIL = "retail"
    HEALTHCARE = "healthcare"
    CRYPTOCURRENCY = "cryptocurrency"
    GOVERNMENT = "government"
    ENTERTAINMENT = "entertainment"


@dataclass(slots=True)
class Organization:
    handle: str
    name: str
    organization_type: OrganizationType


class ProvablyAuthAPI:
    """Provably Auth API endpoints."""

    def __init__(self) -> None:
        self._http = ProvablyHTTPClient(pre_auth=True)

    def _user_path(self) -> str:
        return "/api/v1/user"

    def _org_path(self) -> str:
        return "/api/v1/organizations"

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    async def exchange_code(self, code: str, verifier: str) -> dict[str, Any]:
        """
        Exchange an authorization code for tokens (public client, no secret).

        Args:
            code: The authorization code from the redirect.
            verifier: The PKCE code verifier.

        Returns:
            dict[str, Any]: The raw JSON response (contains ``access_token``
            and optionally ``refresh_token``).
        """
        path = "/api/v1/auth/oauth/token"

        result: dict[str, Any] = await self._http.post_form(
            path,
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": OAUTH_CLIENT_ID,
                "code_verifier": verifier,
            },
        )
        return result

    async def refresh_tokens(self, refresh_token: str) -> dict[str, Any]:
        """
        Rotate tokens: exchange a refresh token for a new access+refresh pair.

        Args:
            refresh_token: The refresh token to redeem.

        Returns:
            dict[str, Any]: The raw JSON response (contains ``access_token``
            and optionally ``refresh_token``).
        """
        path = "/api/v1/auth/oauth/refresh"

        result: dict[str, Any] = await self._http.post_form(
            path,
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": OAUTH_CLIENT_ID,
            },
        )
        return result

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    async def get_current_user(self, token: str) -> dict[str, Any]:
        """
        Retrieve the current authenticated user.

        Args:
            token: OAuth access token (Bearer).

        Returns:
            dict[str, Any]: The raw JSON response from the API (contains ``email``).
        """
        path = f"{self._user_path()}/current"

        result: dict[str, Any] = await self._http.get(path, token=token)
        return result

    # ------------------------------------------------------------------
    # API KEY
    # ------------------------------------------------------------------

    async def get_api_key(self, token: str) -> dict[str, Any]:
        """
        Retrieve the API key for the authenticated user.

        Args:
            token: JWT Bearer token obtained from ``login``.

        Returns:
            dict[str, Any]: The raw JSON response from the API (contains ``api_key``).
        """
        path = f"{self._user_path()}/key"

        result: dict[str, Any] = await self._http.get(path, token=token)
        return result

    # ------------------------------------------------------------------
    # Organization
    # ------------------------------------------------------------------

    async def create_organization(self, token: str, organization: Organization) -> dict[str, Any]:
        """
        Create a new organisation.

        Args:
            token: JWT Bearer token obtained from ``login``.
            organization: The organisation details.

        Returns:
            dict[str, Any]: The raw JSON response from the API (contains ``id``).
        """
        payload = {
            "handle": organization.handle,
            "name": organization.name,
            "type": organization.organization_type.value,
        }
        path = f"{self._org_path()}"

        result: dict[str, Any] = await self._http.post_multipart(path, payload, token=token)
        return result

    async def get_organizations(self, token: str) -> list[dict[str, Any]]:
        """
        List all organisations accessible to the authenticated user.

        Args:
            token: JWT Bearer token obtained from ``login``.

        Returns:
            list[dict[str, Any]]: List of organisation objects (each contains at least ``id`` and ``name``).
        """
        path = f"{self._org_path()}"

        result: list[dict[str, Any]] = await self._http.get(path, token=token)
        return result


@functools.lru_cache(maxsize=1)
def get_api() -> ProvablyAuthAPI:
    """Return the shared :class:`ProvablyAuthAPI`, constructed on first call."""
    return ProvablyAuthAPI()
