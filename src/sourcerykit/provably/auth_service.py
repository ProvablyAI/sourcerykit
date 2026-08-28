"""
Provably auth service layer
"""

import uuid
from typing import Any

from sourcerykit.provably._api import get_api as get_main_api
from sourcerykit.provably._auth_api import OAuthTokens, Organization, get_api
from sourcerykit.provably._errors import provably_auth_error_handler


class ProvablyAuthService:
    """High-level service for account and organisation management."""

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------

    async def exchange_code(self, code: str, verifier: str) -> OAuthTokens:
        """Exchange an authorization code for tokens (public client, no secret).

        Args:
            code: The authorization code from the redirect.
            verifier: The PKCE code verifier.

        Returns:
            OAuthTokens: The issued access and refresh tokens.

        Raises:
            ProvablyAuthError: On API errors.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_auth_error_handler("oauth_token_exchange"):
            result = await get_api().exchange_code(code, verifier)
            return OAuthTokens(access_token=result["access_token"], refresh_token=result.get("refresh_token"))

    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """Rotate tokens: exchange a refresh token for a new access+refresh pair.

        Args:
            refresh_token: The refresh token to redeem.

        Returns:
            OAuthTokens: The new access and refresh tokens.

        Raises:
            ProvablyAuthError: On API errors.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_auth_error_handler("oauth_refresh"):
            result = await get_api().refresh_tokens(refresh_token)
            return OAuthTokens(access_token=result["access_token"], refresh_token=result.get("refresh_token"))

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    async def get_user_email(self, token: str) -> str:
        """Retrieve the email of the authenticated user.

        Args:
            token: OAuth access token (Bearer) from ``browser_login``.

        Returns:
            str: The user's email address.

        Raises:
            ProvablyAuthError: On API errors.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_auth_error_handler("get_user_email"):
            result = await get_api().get_current_user(token)
            return str(result["email"])

    # ------------------------------------------------------------------
    # API Key
    # ------------------------------------------------------------------

    async def get_api_key(self, token: str) -> str:
        """Retrieve the API key for the authenticated user.

        Args:
            token: JWT Bearer token from ``login``.

        Returns:
            str: The API key string.

        Raises:
            ProvablyAuthError: On API errors.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_auth_error_handler("get_api_key"):
            result = await get_api().get_api_key(token)
            return str(result["api_key"])

    # ------------------------------------------------------------------
    # Organisation
    # ------------------------------------------------------------------

    async def create_organization(self, token: str, organization: Organization) -> uuid.UUID:
        """Create a new organisation and return its ID.

        Args:
            token: JWT Bearer token from ``login``.
            organization: Organisation details.

        Returns:
            uuid.UUID: The ID of the newly created organisation.

        Raises:
            ProvablyResourceAlreadyExistsError: If the handle is already taken.
            ProvablyAuthError: On other API errors.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_auth_error_handler("create_organization"):
            result = await get_api().create_organization(token, organization)
            return uuid.UUID(str(result["id"]))

    async def get_organizations(self, token: str) -> list[dict[str, Any]]:
        """List organisations accessible to the authenticated user.

        Args:
            token: JWT token from ``login``.

        Returns:
            list[dict[str, Any]]: List of organisation.

        Raises:
            ProvablyAuthError: On API errors.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_auth_error_handler("get_organizations"):
            result = await get_api().get_organizations(token)
            return result

    async def list_organizations(self) -> list[dict[str, Any]]:
        """List organisations accessible to the authenticated user (via API key).

        Returns:
            list[dict[str, Any]]: List of organisation objects (each contains at least ``id`` and ``name``).

        Raises:
            ProvablyAuthError: On API errors.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_auth_error_handler("list_organizations"):
            result = await get_main_api().list_organizations()
            return result


auth_service = ProvablyAuthService()
