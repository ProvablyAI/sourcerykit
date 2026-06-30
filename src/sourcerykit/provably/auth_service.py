"""
Provably auth service layer
"""

import uuid
from typing import Any

from sourcerykit.provably._api import get_api as get_main_api
from sourcerykit.provably._auth_api import Organization, User, get_api
from sourcerykit.provably._errors import provably_auth_error_handler


class ProvablyAuthService:
    """High-level service for account and organisation management."""

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    async def create_account(self, user: User) -> None:
        """Register a new account.

        Raises:
            ProvablyResourceAlreadyExistsError: If an account with that email already exists.
            ProvablyAuthError: For other 4xx/5xx responses.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_auth_error_handler("create_account"):
            await get_api().create_account(user)

    async def login(self, user: User) -> dict[str, Any]:
        """Authenticate with email and password.

        Returns:
            dict[str, Any]: The raw API response (contains ``token``).

        Raises:
            ProvablyUnauthorizedError: If credentials are wrong.
            ProvablyAuthError: For other 4xx/5xx responses.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_auth_error_handler("login"):
            result = await get_api().login(user)
            return result

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
