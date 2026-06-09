"""Provably API — named methods for every endpoint.

:class:`ProvablyAPI` covers five resource groups:
- **Middlewares** — create the Provably middleware for an org
- **Databases / Schemas / Tables / Columns** — onboard and inspect the connected database
- **Collections** — manage query collections
- **Integrations** — register external integrations
- **Queries & Proofs** — run queries, generate proofs, poll status
"""

import functools
import uuid
from typing import Any

from agentkit.config import Settings, get_settings
from agentkit.provably._http import get_http


class ProvablyAPI:
    """Provably API endpoints."""

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        self.org_id = s.org_id
        self.app = s.provably_app

    def _org_path(self) -> str:
        return f"/api/v1/organizations/{self.org_id}"

    # ------------------------------------------------------------------
    # Middlewares
    # ------------------------------------------------------------------

    async def create_middleware(self) -> dict[str, Any]:
        """
        Create the Provably middleware for the configured org.

        Returns:
            dict[str, Any]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/middlewares/provably"

        result: dict[str, Any] = await get_http().post(path)
        return result

    async def list_middlewares(self) -> list[dict[str, Any]]:
        """
        List all middlewares.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/middlewares"

        result: list[dict[str, Any]] = await get_http().get(path)
        return result

    # ------------------------------------------------------------------
    # Databases
    # ------------------------------------------------------------------

    async def create_database(self, middleware_id: uuid.UUID, body: dict[str, Any]) -> dict[str, Any]:
        """
        Onboard a database to a middleware.

        Args:
            middleware_id: The ID of the middleware to attach the database to.
            body: The database connection payload.

        Returns:
            httpx.Response: The raw HTTP response from the API.
        """
        path = f"{self._org_path()}/middlewares/{middleware_id}/databases"

        result: dict[str, Any] = await get_http().post(path, body)
        return result

    async def list_databases(self, middleware_id: uuid.UUID) -> list[dict[str, Any]]:
        """
        List all databases attached to a middleware.

        Args:
            middleware_id: The ID of the middleware to query.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/middlewares/{middleware_id}/databases"

        result: list[dict[str, Any]] = await get_http().get(path)
        return result

    # ------------------------------------------------------------------
    # Schemas / Tables / Columns
    # ------------------------------------------------------------------

    async def list_columns_from_database(
        self,
        middleware_id: uuid.UUID,
        database_id: uuid.UUID,
        schema_id: uuid.UUID,
        table_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """
        List all columns in a table.

        Args:
            middleware_id: The ID of the middleware owning the database.
            database_id: The ID of the database containing the schema.
            schema_id: The ID of the schema containing the table.
            table_id: The ID of the table to inspect.

        Returns:
            list[dict[str, Any]]: The raw JSON response from the API.
        """
        path = (
            f"{self._org_path()}/middlewares/{middleware_id}"
            f"/databases/{database_id}/schemas/{schema_id}/tables/{table_id}/columns"
        )
        result: list[dict[str, Any]] = await get_http().get(path)
        return result

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    async def get_data(self) -> dict[str, Any]:
        """
        Retrieve data for the configured org.

        Returns:
            dict[str, Any]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/data"
        result: dict[str, Any] = await get_http().get(path)
        return result

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    async def list_collections(self) -> list[dict[str, Any]]:
        """
        List all collections for the configured org.

        Returns:
            list[dict[str, Any]]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/collections"
        result: list[dict[str, Any]] = await get_http().get(path)
        return result

    async def create_collection(self, body: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new collection for the configured org.

        Args:
            body: The collection creation payload.

        Returns:
            httpx.Response: The raw HTTP response from the API.
        """
        path = f"{self._org_path()}/collections"

        result: dict[str, Any] = await get_http().post(path, body)
        return result

    # ------------------------------------------------------------------
    # Integrations
    # ------------------------------------------------------------------

    async def create_integration(self, body: dict[str, Any]) -> dict[str, Any]:
        """
        Register a new external integration for the configured org.

        Args:
            body: The integration registration payload.

        Returns:
            dict[str, Any]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/integrations"

        result: dict[str, Any] = await get_http().post(path, body)
        return result

    async def list_integrations(self, query: str | None = None) -> list[dict[str, Any]]:
        """
        List all integrations for the configured org.

        Args:
            query: Optional search string to filter integrations by name.

        Returns:
            list[dict[str, Any]]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/integrations"
        params = {"query": query} if query is not None else None
        result: list[dict[str, Any]] = await get_http().get(path, params=params)
        return result

    async def get_integration_by_id(self, integration_id: uuid.UUID) -> dict[str, Any]:
        """
        Get integration by id.

        Returns:
            dict[str, Any]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/integrations/{integration_id}"
        result: dict[str, Any] = await get_http().get(path)
        return result

    # ------------------------------------------------------------------
    # Preprocess
    # ------------------------------------------------------------------

    async def start_preprocess(self, middleware_id: uuid.UUID, table_id: uuid.UUID) -> dict[str, Any]:
        """
        Start a preprocessing job for a table.

        Args:
            middleware_id: The ID of the middleware owning the table.
            table_id: The ID of the table to preprocess.

        Returns:
            dict[str, Any]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/middlewares/{middleware_id}/tables/{table_id}/preprocess"

        result: dict[str, Any] = await get_http().post(path, {"force": True})
        return result

    async def get_preprocess_status(self, middleware_id: uuid.UUID, table_id: uuid.UUID) -> dict[str, Any]:
        """
        Get the preprocessing status for a table.

        Args:
            middleware_id: The ID of the middleware owning the table.
            table_id: The ID of the table to check.

        Returns:
            dict[str, Any]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/middlewares/{middleware_id}/tables/{table_id}/preprocess"

        result: dict[str, Any] = await get_http().get(path)
        return result

    # ------------------------------------------------------------------
    # Queries / Proofs
    # ------------------------------------------------------------------

    async def run_query(self, middleware_id: uuid.UUID, collection_id: uuid.UUID, sql: str) -> dict[str, Any]:
        """
        Run a SQL query through a middleware and request a proof.

        Args:
            middleware_id: The ID of the middleware to execute the query against.
            collection_id: The ID of the collection to associate the query with.
            sql: The SQL query string to execute.

        Returns:
            dict[str, Any]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/middlewares/{middleware_id}/query"

        result: dict[str, Any] = await get_http().post(
            path, {"query": sql, "require_proof": True, "collection_id": str(collection_id)}
        )
        return result

    async def get_query(self, query_id: uuid.UUID, *, api_key: str | None = None) -> dict[str, Any]:
        """
        Retrieve a query record by ID.

        Args:
            query_id: The ID of the query to retrieve.
            api_key: Optional API key override for this request.

        Returns:
            dict[str, Any]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/queries/{query_id}"

        result: dict[str, Any] = await get_http().get(path, api_key=api_key)
        return result

    async def verify_proof(self, query_id: uuid.UUID, *, api_key: str | None = None) -> dict[str, Any]:
        """
        Request verification for an existing query proof.

        Args:
            query_id: The unique identifier of the query whose proof needs
                verification.
            api_key: Optional API key override for this request.

        Returns:
            dict[str, Any]: A response confirming the verification
                task has been successfully initiated.

        Raises:
            ProvablyAPIError: If the query does not exist or verification
                cannot be initiated.
        """
        path = f"{self._org_path()}/queries/{query_id}/verify"

        result: dict[str, Any] = await get_http().post(path, {}, api_key=api_key)
        return result

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def query_record_url(self, query_record_id: uuid.UUID) -> str:
        """Provably Data Admin URL for a query record."""
        if not query_record_id:
            raise ValueError("query_record_id is required")
        return f"{self.app}/org/{self.org_id}/query-record/{query_record_id}"


@functools.lru_cache(maxsize=1)
def get_api() -> ProvablyAPI:
    """Return the shared :class:`ProvablyAPI`, constructed on first call."""
    return ProvablyAPI()
