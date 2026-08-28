"""Provably Auth API — API key and organisation endpoints.

:class:`ProvablyAuthAPI` covers two resource groups:
- **API Key** — retrieve the API key for the authenticated user
- **Organisations** — create and list organisations

Authentication itself is OAuth browser login; see
:mod:`sourcerykit.provably.oauth_login`.
"""

import functools
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sourcerykit.provably._http import ProvablyHTTPClient


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
