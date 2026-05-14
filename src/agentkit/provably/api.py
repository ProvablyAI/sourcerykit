"""Provably API — named methods for every endpoint.

:class:`ProvablyAPI` covers five resource groups:
- **Middlewares** — create the Provably middleware for an org
- **Databases / Schemas / Tables / Columns** — onboard and inspect the connected database
- **Collections** — manage query collections
- **Integrations** — register external integrations
- **Queries & Proofs** — run queries, generate proofs, poll status
"""

import uuid
from typing import Any

from agentkit.config import Settings, get_settings
from agentkit.provably._http import http


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
        return await http.post(path)

    async def list_middlewares(self) -> list[dict[str, Any]]:
        """
        List all middlewares.

        Args:
            middleware_id: The ID of the middleware to query.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/middlewares"
        return await http.get(path)

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
        return await http.post(path, body)

    async def list_databases(self, middleware_id: uuid.UUID) -> list[dict[str, Any]]:
        """
        List all databases attached to a middleware.

        Args:
            middleware_id: The ID of the middleware to query.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/middlewares/{middleware_id}/databases"
        return await http.get(path)

    # ------------------------------------------------------------------
    # Schemas / Tables / Columns
    # ------------------------------------------------------------------

    async def list_schemas(self, middleware_id: uuid.UUID, database_id: uuid.UUID) -> Any:
        """
        List all schemas in a database.

        Args:
            middleware_id: The ID of the middleware owning the database.
            database_id: The ID of the database to inspect.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/middlewares/{middleware_id}/databases/{database_id}/schemas"
        return await http.get(path)

    async def list_tables(self, middleware_id: str, database_id: str, schema_id: str) -> Any:
        """
        List all tables in a schema.

        Args:
            middleware_id: The ID of the middleware owning the database.
            database_id: The ID of the database containing the schema.
            schema_id: The ID of the schema to inspect.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/middlewares/{middleware_id}/databases/{database_id}/schemas/{schema_id}/tables"
        return await http.get(path)

    async def list_columns_from_database(
        self,
        middleware_id: uuid.UUID,
        database_id: uuid.UUID,
        schema_id: uuid.UUID,
        table_id: uuid.UUID,
    ) -> Any:
        """
        List all columns in a table.

        Args:
            middleware_id: The ID of the middleware owning the database.
            database_id: The ID of the database containing the schema.
            schema_id: The ID of the schema containing the table.
            table_id: The ID of the table to inspect.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = (
            f"{self._org_path()}/middlewares/{middleware_id}"
            f"/databases/{database_id}/schemas/{schema_id}/tables/{table_id}/columns"
        )
        return await http.get(path)

    async def list_columns_from_collection(
        self,
        collection_id: uuid.UUID,
    ) -> Any:
        """
        List all columns in a collection.

        Args:
            collection_id: The ID of the middleware owning the database.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/collections/{collection_id}/columns"
        return await http.get(path)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    async def get_data(self) -> Any:
        """
        Retrieve data for the configured org.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/data"
        return await http.get(path)

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    async def list_collections(self) -> Any:
        """
        List all collections for the configured org.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/collections"
        return await http.get(path)

    async def create_collection(self, body: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new collection for the configured org.

        Args:
            body: The collection creation payload.

        Returns:
            httpx.Response: The raw HTTP response from the API.
        """
        path = f"{self._org_path()}/collections"
        return await http.post(path, body)

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
        return await http.post(path, body)

    async def list_integrations(self) -> Any:
        """
        List all integrations for the configured org.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/integrations"
        return await http.get(path)

    async def get_integration_by_id(self, integration_id: uuid.UUID) -> Any:
        """
        Get integration by id.

        Returns:
            Any: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/integrations/{integration_id}"
        return await http.get(path)

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
        return await http.post(path, {"force": True})

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
        return await http.get(path)

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
        return await http.post(path, {"query": sql, "require_proof": True, "collection_id": collection_id})

    async def get_query(self, query_id: uuid.UUID) -> dict[str, Any]:
        """
        Retrieve a query record by ID.

        Args:
            query_id: The ID of the query to retrieve.

        Returns:
            dict[str, Any]: The raw JSON response from the API.
        """
        path = f"{self._org_path()}/queries/{query_id}"
        return await http.get(path)

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def query_record_url(self, query_record_id: uuid.UUID) -> str:
        """Provably Data Admin URL for a query record."""
        if not query_record_id:
            raise ValueError("query_record_id is required")
        return f"{self.app}/org/{self.org_id}/query-record/{query_record_id}"


# Shared singleton
api = ProvablyAPI()
