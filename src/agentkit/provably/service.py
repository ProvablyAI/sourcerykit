"""
Provably service layer
"""

import asyncio
import uuid
from typing import Any

from agentkit.db.engine import ConnectionInfo
from agentkit.db.schema import PROVABLY_INTERCEPTS_TABLE
from agentkit.logger import get_logger
from agentkit.provably.api import api
from agentkit.provably.errors import provably_error_handler

_log = get_logger(__name__)


class ProvablyService:
    """High-level service for managing Provably resources."""

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    async def create_middleware(self) -> uuid.UUID:
        """Create the Provably middleware.

        Returns:
            uuid.UUID: The ID of the middleware.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
            ProvablyDataError: If the response is malformed.
        """
        async with provably_error_handler("create_middleware"):
            result = await api.create_middleware()
            return uuid.UUID(str(result["id"]))

    async def get_middleware_id(self) -> uuid.UUID:
        """Find and return the ID of the existing Provably middleware.

        Returns:
            uuid.UUID: The ID of the middleware named 'Provably Middleware'.

        Raises:
            ValueError: If no middleware with that name exists.
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """

        async with provably_error_handler("get_middleware_id"):
            middlewares = await api.list_middlewares()

            try:
                match = next(md for md in middlewares if md.get("name") == "Provably Middleware")
                return uuid.UUID(str(match["id"]))
            except StopIteration:
                raise ValueError("Middleware with name 'Provably Middleware' not found.")

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    # Will create database, schema and table
    async def create_database(self, middleware_id: uuid.UUID, database: ConnectionInfo) -> uuid.UUID:
        """Register a new database with the middleware.

        Args:
            middleware_id: The ID of the middleware to attach the database to.
            database: Connection details for the database to register.

        Returns:
            uuid.UUID: The ID of the newly created database.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
            ProvablyDataError: If the response is malformed.
        """

        async with provably_error_handler("create_database"):
            result = await api.create_database(middleware_id, database.to_dict())
            return uuid.UUID(str(result["id"]))

    async def get_database_id(self, middleware_id: uuid.UUID, database: ConnectionInfo) -> uuid.UUID:
        """Find and return the ID of an existing database by name.

        Args:
            middleware_id: The ID of the middleware owning the database.
            database: Connection info whose name is used to locate the database.

        Returns:
            uuid.UUID: The ID of the matching database.

        Raises:
            ValueError: If no database with the given name exists in the middleware.
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """

        async with provably_error_handler("get_database_id"):
            databases = await api.list_databases(middleware_id)

            try:
                match = next(db for db in databases if db.get("name") == database.name)
                return uuid.UUID(str(match["id"]))
            except StopIteration:
                raise ValueError(f"Database with name '{database.name}' not found in middleware {middleware_id}")

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    async def create_collection(
        self,
        middleware_id: uuid.UUID,
        database_id: uuid.UUID,
        schema_id: uuid.UUID,
        table_id: uuid.UUID,
        columns: list[uuid.UUID],
    ) -> uuid.UUID:
        """Create a new query collection for the intercepts table.

        Args:
            middleware_id: The ID of the middleware owning the table.
            database_id: The ID of the database containing the table.
            schema_id: The ID of the schema containing the table.
            table_id: The ID of the table to base the collection on.
            columns: List of column IDs to enable for the collection.

        Returns:
            uuid.UUID: The ID of the newly created collection.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
            ProvablyDataError: If the response is malformed.
        """

        collection = {
            "name": PROVABLY_INTERCEPTS_TABLE,
            "publicity_status": "private",
            "middleware_id": middleware_id,
            "database_id": database_id,
            "is_descriptions_generated": False,
            "entities": [],
            "integrations": [],
            "query_price": 0,
            "is_general_sql_queries_enabled": True,
            "schema_id": schema_id,
            "table_id": table_id,
            "enabled_columns": columns,
        }

        async with provably_error_handler("create_collection"):
            result = await api.create_collection(collection)
            return uuid.UUID(str(result["id"]))

    async def get_collection_id(self) -> uuid.UUID:
        """Find and return the ID of the existing intercepts collection.

        Returns:
            uuid.UUID: The ID of the collection named after the intercepts table.

        Raises:
            ValueError: If no matching collection is found.
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("get_collection_id"):
            collections = await api.list_collections()

            try:
                match = next(
                    collection for collection in collections if collection.get("name") == PROVABLY_INTERCEPTS_TABLE
                )
                return uuid.UUID(str(match["id"]))
            except StopIteration:
                raise ValueError(f"Collection with name '{PROVABLY_INTERCEPTS_TABLE}' not found")

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    async def get_database_schema_id_and_table_id(
        self, middleware_id: uuid.UUID, database: ConnectionInfo
    ) -> dict[str, uuid.UUID]:
        """Locate the schema and table IDs for the intercepts table within a database.

        Args:
            middleware_id: The ID of the middleware owning the database.
            database: Connection info used to identify the target database by name.

        Returns:
            dict[str, uuid.UUID]: A dict with keys ``schema_id`` and ``table_id``.

        Raises:
            ValueError: If the middleware, database, or table cannot be found.
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("get_data"):
            data = await api.get_data()
            middlewares = data.get("middlewares", [])

            # Find the Middleware
            mw = next((m for m in middlewares if m.get("id") == str(middleware_id)), None)
            if not mw:
                raise ValueError(f"Middleware {middleware_id} not found in response")

            # Find the Database
            db = next((d for d in mw.get("databases", []) if d.get("name") == database.name), None)
            if not db:
                raise ValueError(f"Database '{database.name}' not found in middleware {middleware_id}")

            # Find the Schema and Table
            # We assume the table exists within one of the schemas of this database
            for schema in db.get("schemas", []):
                table = next((t for t in schema.get("tables", []) if t.get("name") == PROVABLY_INTERCEPTS_TABLE), None)

                if table:
                    return {"schema_id": uuid.UUID(str(schema["id"])), "table_id": uuid.UUID(str(table["id"]))}

            # Table not found
            raise ValueError(
                f"Table '{PROVABLY_INTERCEPTS_TABLE}' not found in any schema for database '{database.name}'"
            )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------

    async def get_columns_from_collection(self, collection_id: uuid.UUID) -> dict[str, Any]:
        """Retrieve all columns associated with a collection.

        Args:
            collection_id: The ID of the collection to inspect.

        Returns:
            dict[str, Any]: The raw columns response from the API.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("get_columns_from_database"):
            columns = await api.list_columns_from_collection(collection_id)
            return columns

    async def get_columns_from_database(
        self,
        middleware_id: uuid.UUID,
        database_id: uuid.UUID,
        schema_id: uuid.UUID,
        table_id: uuid.UUID,
    ) -> list[uuid.UUID]:
        """Retrieve the column IDs for a specific table.

        Args:
            middleware_id: The ID of the middleware owning the database.
            database_id: The ID of the database containing the table.
            schema_id: The ID of the schema containing the table.
            table_id: The ID of the table whose columns to retrieve.

        Returns:
            list[uuid.UUID]: List of column IDs.

        Raises:
            ValueError: If any column is missing a valid ``id`` field.
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("get_columns_from_database"):
            columns = await api.list_columns_from_database(middleware_id, database_id, schema_id, table_id)

            try:
                return [uuid.UUID(str(col["id"])) for col in columns]
            except (KeyError, ValueError) as e:
                raise ValueError("One or more columns missing a valid 'id' field") from e

    # ------------------------------------------------------------------
    # Integrations
    # ------------------------------------------------------------------

    async def create_integration(self, collection_id: uuid.UUID) -> uuid.UUID:
        """Register a new agent integration for the intercepts collection.

        Args:
            collection_id: The ID of the collection to associate with the integration.

        Returns:
            uuid.UUID: The ID of the newly created integration.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
            ProvablyDataError: If the response is malformed.
        """
        integration = {
            "description": PROVABLY_INTERCEPTS_TABLE,
            "is_enabled": True,
            "name": PROVABLY_INTERCEPTS_TABLE,
            "role": "owner",
            "type": "agent",
            "collections": [collection_id],
        }

        async with provably_error_handler("create_integration"):
            result = await api.create_integration(integration)
            return uuid.UUID(str(result["id"]))

    async def get_integration_intercepts_id(self) -> str:
        """Find the intercepts integration and return its API key.

        Returns:
            str: The API key for the intercepts integration.

        Raises:
            ValueError: If the integration is not found or the API key is missing.
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("get_integration_intercepts_id"):
            integrations = await api.list_integrations()

            # Find the integration with the matching name
            try:
                match = next(item for item in integrations if item.get("name") == PROVABLY_INTERCEPTS_TABLE)
            except StopIteration:
                raise ValueError(f"Integration with name '{PROVABLY_INTERCEPTS_TABLE}' not found.")

            # Extract and return the API key
            api_key = match.get("api_key")
            if not api_key:
                raise ValueError(f"Integration '{PROVABLY_INTERCEPTS_TABLE}' found, but 'api_key' is missing.")

            return str(api_key)

    async def get_integration_intercepts_api_key(self, integration_id: uuid.UUID, collection_id: uuid.UUID) -> str:
        """Validate an integration and return its API key.

        Args:
            integration_id: The ID of the integration to look up.
            collection_id: The collection ID that must be associated with the integration.

        Returns:
            str: The API key of the integration.

        Raises:
            ValueError: If the integration name mismatches, the collection is not associated,
                or the API key is missing.
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("get_integration_intercepts_api_key"):
            integration = await api.get_integration_by_id(integration_id)

            # Validate the Integration Name
            if integration.get("name") != PROVABLY_INTERCEPTS_TABLE:
                raise ValueError(
                    f"Integration {integration_id} name mismatch. "
                    f"Expected '{PROVABLY_INTERCEPTS_TABLE}', got '{integration.get('name')}'"
                )

            # Check if the collection_id is associated with this integration
            associated_collections = integration.get("collections", [])
            if str(collection_id) not in [str(c) for c in associated_collections]:
                raise ValueError(f"Collection {collection_id} not found in integration {integration_id}")

            # Extract and return the API key
            api_key = integration.get("api_key")
            if not api_key:
                raise ValueError(f"Integration '{PROVABLY_INTERCEPTS_TABLE}' found, but 'api_key' is missing.")

            return str(api_key)

    # ------------------------------------------------------------------
    # Preprocess
    # ------------------------------------------------------------------

    async def start_preprocess(self, middleware_id: uuid.UUID, table_id: uuid.UUID) -> uuid.UUID:
        """Start a preprocessing job for a table.

        Args:
            middleware_id: The ID of the middleware owning the table.
            table_id: The ID of the table to preprocess.

        Returns:
            uuid.UUID: The ID of the started preprocessing job.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
            ProvablyDataError: If the response is malformed.
        """
        async with provably_error_handler("start_preprocess"):
            result = await api.start_preprocess(middleware_id, table_id)
            return uuid.UUID(str(result["id"]))

    async def get_preprocess_completed(self, middleware_id: uuid.UUID, table_id: uuid.UUID, timeout: int = 60):
        """
        Polls the preprocess status until it reaches 'completed'.

        Args:
            middleware_id: The ID of the middleware.
            table_id: The ID of the table being preprocessed.
            timeout: maximum seconds to wait (default 10 minutes).

        Raises:
            RuntimeError: If the status becomes 'error'.
            TimeoutError: If the process exceeds the timeout.
        """

        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            async with provably_error_handler("get_preprocess_status"):
                preprocess = await api.get_preprocess_status(middleware_id, table_id)

            status = preprocess.get("status")

            if status == "completed":
                _log.info("preprocess_finished", table_id=str(table_id))
                return

            if status == "error":
                error_detail = preprocess.get("error", preprocess.get("status_detail"))
                raise RuntimeError(f"Table preprocessing failed: {error_detail}")

            # If status is 'pending' or 'processing', wait and try again
            _log.debug("preprocess_in_progress", table_id=str(table_id), status=status)
            await asyncio.sleep(0.3)

        raise TimeoutError(f"Preprocessing for table {table_id} timed out after {timeout}s")

    # ------------------------------------------------------------------
    # Queries / Proofs
    # ------------------------------------------------------------------

    async def run_query(self, middleware_id: uuid.UUID, collection_id: uuid.UUID, sql: str) -> uuid.UUID:
        """Run a SQL query through a middleware and request a proof.

        Args:
            middleware_id: The ID of the middleware to execute the query against.
            collection_id: The ID of the collection to associate the query with.
            sql: The SQL query string to execute.

        Returns:
            dict: The raw JSON response from the API.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("run_query"):
            result = await api.run_query(middleware_id, collection_id, sql)
            return uuid.UUID(str(result["id"]))

    async def wait_for_proof_computation(self, query_id: uuid.UUID, timeout: int = 60) -> dict[str, Any]:
        """
        Polls the query status until it reaches a terminal state (completed or failed).

        Args:
            query_id: The unique identifier for the query.
            timeout: Maximum seconds to wait for the proof/result.

        Returns:
            dict[str, Any]: The final query result and proof data.

        Raises:
            ProvablyAPIError: If the server rejects a status check.
            RuntimeError: If the query fails on the backend.
            TimeoutError: If the terminal state isn't reached within the timeout.
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            async with provably_error_handler("wait_for_proof_computation"):
                data = await api.get_query(query_id)

            proof = data.get("proof")

            # If proof is not null, check the internal status
            if proof:
                status = proof.get("status")
                if status == "Completed":
                    _log.info("proof_generation_success", query_id=str(query_id))
                    return data

                if status == "Failed":
                    _log.error("proof_generation_failed", query_id=str(query_id))
                    raise RuntimeError(f"Provably proof generation failed for query {query_id}")

            # If status is 'Pending' (or proof is still null), we continue waiting
            _log.debug("proof_generation_pending", query_id=str(query_id))
            await asyncio.sleep(0.1)

        raise TimeoutError(f"Timed out waiting for proof {query_id} after {timeout}s")

    async def verify_proof(self, query_id: uuid.UUID):
        """Run a SQL query through a middleware and request a proof.

        Args:
            middleware_id: The ID of the middleware to execute the query against.
            collection_id: The ID of the collection to associate the query with.
            sql: The SQL query string to execute.

        Returns:
            dict: The raw JSON response from the API.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("run_query"):
            await api.verify_proof(query_id)

    async def wait_for_proof_verification(self, query_id: uuid.UUID, timeout: int = 60) -> dict[str, Any]:
        """
        Polls the query until the proof verification_status reaches 'Verified'.

        Args:
            query_id: The identifier for the query.
            timeout: Maximum seconds to wait for verification.

        Returns:
            dict[str, Any]: The full response containing the Verified ProofInfo.

        Raises:
            RuntimeError: If verification_status becomes 'Failed'.
            TimeoutError: If verification doesn't complete within the timeout.
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            async with provably_error_handler("wait_for_proof_verification"):
                data = await api.get_query(query_id)

            proof = data.get("proof")

            # If proof is not null, check the internal status
            if proof:
                v_status = proof.get("verification_status")
                if v_status == "Verified":
                    _log.info("proof_verification_success", query_id=str(query_id))
                    return data

                if v_status == "Failed":
                    _log.error("proof_verification_failed", query_id=str(query_id))
                    raise RuntimeError(f"Provably proof verification failed for query {query_id}")

            # If status is 'Unverified' or 'Verifying', continue polling
            _log.debug(
                "proof_verification_pending",
                query_id=str(query_id),
                status=proof.get("verification_status") if proof else "null",
            )
            await asyncio.sleep(0.1)

        raise TimeoutError(f"Verification for query {query_id} timed out after {timeout}s")

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def query_record_url(self, query_id: uuid.UUID) -> str:
        """Build the Provably Data Admin URL for a query record.

        Args:
            query_id: The ID of the query record.

        Returns:
            str: The full URL to the query record in the Provably admin UI.
        """
        return api.query_record_url(query_id)


# Shared singleton
service = ProvablyService()
