"""
Provably service layer
"""

import asyncio
import uuid
from typing import Any

from sourcerykit.db._engine import ConnectionInfo
from sourcerykit.db._schema import INTERCEPTS_TABLE
from sourcerykit.logger import get_logger
from sourcerykit.provably._api import get_api
from sourcerykit.provably._errors import provably_error_handler

_log = get_logger(__name__)


class ProvablyService:
    """High-level service for managing Provably resources."""

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------
    async def create_feedback(self, description: str, file: bytes | None) -> None:
        """Send a feedback."""

        feedback_body = {"description": description}

        file_payload = {}

        if file:
            file_payload["files"] = ("attachment.dat", file)

        async with provably_error_handler("create_feedback"):
            return await get_api().create_feedback(feedback_body, files=file_payload)

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
            result = await get_api().create_middleware()
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
            middlewares = await get_api().list_middlewares()

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
            result = await get_api().create_database(middleware_id, database.to_dict())
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
            databases = await get_api().list_databases(middleware_id)

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
        name: str,
    ) -> uuid.UUID:
        """Create a new query collection.

        Args:
            middleware_id: The ID of the middleware owning the table.
            database_id: The ID of the database containing the table.
            schema_id: The ID of the schema containing the table.
            table_id: The ID of the table to base the collection on.
            columns: List of column IDs to enable for the collection.
            name: Collection name (the project name).

        Returns:
            uuid.UUID: The ID of the newly created collection.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
            ProvablyDataError: If the response is malformed.
        """

        collection = {
            "name": name,
            "publicity_status": "private",
            "middleware_id": str(middleware_id),
            "database_id": str(database_id),
            "is_descriptions_generated": False,
            "entities": [],
            "integrations": [],
            "query_price": 0,
            "is_general_sql_queries_enabled": True,
            "schema_id": str(schema_id),
            "table_id": str(table_id),
            "enabled_columns": [{"id": str(c)} for c in columns],
        }

        async with provably_error_handler("create_collection"):
            result = await get_api().create_collection(collection)
            return uuid.UUID(str(result["id"]))

    async def get_collection_id(self, name: str) -> uuid.UUID:
        """Find and return the ID of an existing collection by name.

        Args:
            name: The collection name to look up.

        Returns:
            uuid.UUID: The ID of the matching collection.

        Raises:
            ValueError: If no matching collection is found.
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("get_collection_id"):
            collections = await get_api().list_collections()

            try:
                match = next(collection for collection in collections if collection.get("name") == name)
                return uuid.UUID(str(match["id"]))
            except StopIteration:
                raise ValueError(f"Collection with name '{name}' not found")

    async def list_collections(self) -> list[dict[str, Any]]:
        """Return all collections.

        Returns:
            list[dict[str, Any]]: Raw collection dicts from the API.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("list_collections"):
            return await get_api().list_collections()

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
            data = await get_api().get_data()
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
                table = next((t for t in schema.get("tables", []) if t.get("name") == INTERCEPTS_TABLE), None)

                if table:
                    return {"schema_id": uuid.UUID(str(schema["id"])), "table_id": uuid.UUID(str(table["id"]))}

            # Table not found
            raise ValueError(f"Table '{INTERCEPTS_TABLE}' not found in any schema for database '{database.name}'")

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------

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
            columns = await get_api().list_columns_from_database(middleware_id, database_id, schema_id, table_id)

            try:
                return [uuid.UUID(str(col["id"])) for col in columns]
            except (KeyError, ValueError) as e:
                raise ValueError("One or more columns missing a valid 'id' field") from e

    # ------------------------------------------------------------------
    # Integrations
    # ------------------------------------------------------------------

    async def create_integration(self, collection_id: uuid.UUID) -> tuple[uuid.UUID, str]:
        """Register a new agent integration for the intercepts collection.

        Args:
            collection_id: The ID of the collection to associate with the integration.

        Returns:
            tuple[uuid.UUID, str]: The ID and full API key of the newly created integration.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
            ProvablyDataError: If the response is malformed.
        """
        integration = {
            "description": INTERCEPTS_TABLE,
            "is_enabled": True,
            "name": INTERCEPTS_TABLE,
            "role": "developer",
            "type": "agent",
            "collections": [str(collection_id)],
        }

        async with provably_error_handler("create_integration"):
            result = await get_api().create_integration(integration)
            api_key = result.get("api_key")
            if not api_key:
                raise ValueError("create_integration response missing 'api_key'")
            return uuid.UUID(str(result["id"])), str(api_key)

    async def get_integration_intercepts_api_key(self, collection_id: uuid.UUID) -> str:
        """Find the intercepts integration, verify collection access, and return its API key.

        Args:
            collection_id: The collection ID the integration must have access to.

        Returns:
            str: The API key for the intercepts integration.

        Raises:
            ValueError: If the integration is not found, does not have access to the
                collection, or the API key is missing.
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("get_integration_intercepts_id"):
            integrations = await get_api().list_integrations(query=INTERCEPTS_TABLE)

            candidates = [i for i in integrations if i.get("name") == INTERCEPTS_TABLE]
            if not candidates:
                raise ValueError(f"No integration named '{INTERCEPTS_TABLE}' was found.")

            # collections and api_key are only present in get_integration_by_id
            full_records = await asyncio.gather(
                *(get_api().get_integration_by_id(uuid.UUID(str(c["id"]))) for c in candidates)
            )

            match = next(
                (r for r in full_records if str(collection_id) in [str(c) for c in r.get("collections", [])]),
                None,
            )
            if match is None:
                raise ValueError(
                    f"No integration named '{INTERCEPTS_TABLE}' with access to collection {collection_id} was found."
                )

            print("MATCH: ", match)

            api_key = match.get("api_key")
            if not api_key:
                raise ValueError(f"Integration '{INTERCEPTS_TABLE}' found, but 'api_key' is missing.")

            return str(api_key)

    async def get_integration_by_id(self, integration_id: uuid.UUID) -> dict[str, Any]:
        """Return the full integration record by ID.

        Args:
            integration_id: The ID of the integration to look up.

        Returns:
            dict[str, Any]: The raw integration record from the API.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        async with provably_error_handler("get_integration_by_id"):
            return await get_api().get_integration_by_id(integration_id)

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
            result = await get_api().start_preprocess(middleware_id, table_id)
            return uuid.UUID(str(result["id"]))

    async def get_preprocess_completed(self, middleware_id: uuid.UUID, table_id: uuid.UUID, timeout: int = 60) -> None:
        """
        Polls the preprocess status until it reaches 'completed'.

        Args:
            middleware_id: The ID of the middleware.
            table_id: The ID of the table being preprocessed.
            timeout: maximum seconds to wait (default 60 seconds).

        Raises:
            RuntimeError: If the status becomes 'error'.
            TimeoutError: If the process exceeds the timeout.
        """

        start_time = asyncio.get_running_loop().time()

        api_client = get_api()
        current_delay = 0.05

        while (asyncio.get_running_loop().time() - start_time) < timeout:
            async with provably_error_handler("get_preprocess_status"):
                preprocess = await api_client.get_preprocess_status(middleware_id, table_id)

            status = preprocess.get("status")

            if status == "completed":
                _log.info("preprocess_finished", table_id=str(table_id))
                return

            if status == "error":
                error_detail = preprocess.get("error", preprocess.get("status_detail"))
                raise RuntimeError(f"Table preprocessing failed: {error_detail}")

            # If status is 'pending' or 'processing', wait and try again
            _log.debug("preprocess_in_progress", table_id=str(table_id), status=status)
            await asyncio.sleep(current_delay)
            current_delay = min(current_delay * 2, 0.1)

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
        _log.info("run_query_started", middleware_id=str(middleware_id), collection_id=str(collection_id))
        async with provably_error_handler("run_query"):
            result = await get_api().run_query(middleware_id, collection_id, sql)
            return uuid.UUID(str(result["query_id"]))

    async def get_query(self, query_id: uuid.UUID) -> dict[str, Any]:
        """Retrieve a query record by ID."""
        async with provably_error_handler("get_query"):
            return await get_api().get_query(query_id)

    async def get_query_proof(self, proof_id: uuid.UUID) -> bytes:
        """Download the full proof data for a given proof ID."""
        async with provably_error_handler("get_query_proof"):
            return await get_api().get_query_proof(proof_id)

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
        start_time = asyncio.get_running_loop().time()

        api_client = get_api()
        current_delay = 0.05

        while (asyncio.get_running_loop().time() - start_time) < timeout:
            async with provably_error_handler("wait_for_proof_computation"):
                data = await api_client.get_query(query_id)

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
            await asyncio.sleep(current_delay)
            current_delay = min(current_delay * 2, 0.1)

        raise TimeoutError(f"Timed out waiting for proof {query_id} after {timeout}s")

    async def verify_proof(self, query_id: uuid.UUID, integration_api_key: str) -> None:
        """Run a SQL query through a middleware and request a proof.

        Args:
            query_id: The ID of the query whose proof to verify.
            integration_api_key: The integration API key used to authenticate this request.

        Returns:
            dict: The raw JSON response from the API.

        Raises:
            ProvablyAPIError: If the server rejects the request.
            ProvablyConnectionError: If the network is unreachable.
        """
        _log.info("verify_proof_started", query_id=str(query_id))
        async with provably_error_handler("verify_proof"):
            await get_api().verify_proof(query_id, api_key=integration_api_key)

    async def wait_for_proof_verification(
        self, query_id: uuid.UUID, integration_api_key: str, timeout: int = 60
    ) -> dict[str, Any]:
        """
        Polls the query until the proof verification_status reaches 'Verified'.

        Args:
            query_id: The identifier for the query.
            integration_api_key: The integration API key used to authenticate polling requests.
            timeout: Maximum seconds to wait for verification.

        Returns:
            dict[str, Any]: The full response containing the Verified ProofInfo.

        Raises:
            RuntimeError: If verification_status becomes 'Failed'.
            TimeoutError: If verification doesn't complete within the timeout.
        """
        start_time = asyncio.get_running_loop().time()

        api_client = get_api()
        current_delay = 0.05

        while (asyncio.get_running_loop().time() - start_time) < timeout:
            async with provably_error_handler("wait_for_proof_verification"):
                data = await api_client.get_query(query_id, api_key=integration_api_key)

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
            await asyncio.sleep(current_delay)
            current_delay = min(current_delay * 2, 0.1)

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
        return get_api().query_record_url(query_id)


# Shared singleton
service = ProvablyService()
