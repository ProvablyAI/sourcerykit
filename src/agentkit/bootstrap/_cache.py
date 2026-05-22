"""Provably bootstrap: middleware + database + collection + integration."""

from dataclasses import dataclass, field
from uuid import UUID

from agentkit.db.engine import get_connection_info
from agentkit.errors import AgentKitBootstrapError, AgentKitError
from agentkit.logger import get_logger
from agentkit.provably.errors import ProvablyError
from agentkit.provably.service import service

_log = get_logger(__name__)


@dataclass
class ProvablyBootstrapCache:
    """Holds the resolved Provably resource IDs cached for the process lifetime."""

    middleware_id: UUID | None = field(default=None)
    database_id: UUID | None = field(default=None)
    schema_id: UUID | None = field(default=None)
    table_id: UUID | None = field(default=None)
    collection_id: UUID | None = field(default=None)
    integration_key: str | None = field(default=None)

    async def run_handshake(self) -> None:
        """Resolve or create all required Provably resources."""
        try:
            self.middleware_id = await self._resolve_middleware()

            connection_info = get_connection_info()
            self.database_id = await self._resolve_database(connection_info)

            ids = await service.get_database_schema_id_and_table_id(self.middleware_id, connection_info)
            self.schema_id = ids["schema_id"]
            self.table_id = ids["table_id"]

            self.collection_id = await self._resolve_collection()
            self.integration_key = await self._resolve_integration_key()
        except AgentKitError:
            raise
        except Exception as e:
            _log.error("handshake_failed_unexpected", error=str(e))
            raise AgentKitBootstrapError("Unexpected error during Provably handshake") from e

    async def _resolve_middleware(self) -> UUID:
        try:
            return await service.get_middleware_id()
        except ProvablyError:
            _log.info("middleware_not_found_creating_new")
            try:
                return await service.create_middleware()
            except Exception as e:
                _log.error("middleware_creation_failed", error=str(e))
                raise

    async def _resolve_database(self, database) -> UUID:
        if self.middleware_id is None:
            raise AgentKitBootstrapError("middleware_id is not set; run_handshake() must be called first")
        try:
            return await service.get_database_id(self.middleware_id, database)
        except ProvablyError:
            _log.info("database_not_found_creating_new")
            try:
                return await service.create_database(self.middleware_id, database)
            except Exception as e:
                _log.error("database_creation_failed", error=str(e))
                raise

    async def _resolve_collection(self) -> UUID:
        if self.middleware_id is None or self.database_id is None or self.schema_id is None or self.table_id is None:
            raise AgentKitBootstrapError(
                "middleware_id, database_id, schema_id, and table_id must all be resolved before creating a collection"
            )
        try:
            return await service.get_collection_id()
        except ProvablyError:
            _log.info("collection_not_found_creating_new")
            try:
                columns = await service.get_columns_from_database(
                    self.middleware_id, self.database_id, self.schema_id, self.table_id
                )
                return await service.create_collection(
                    self.middleware_id, self.database_id, self.schema_id, self.table_id, columns
                )
            except Exception as e:
                _log.error("collection_creation_failed", error=str(e))
                raise

    async def _resolve_integration_key(self) -> str:
        if self.collection_id is None:
            raise AgentKitBootstrapError("collection_id is not set; _resolve_collection() must succeed first")
        try:
            return await service.get_integration_intercepts_api_key(self.collection_id)
        except ProvablyError:
            _log.info("integration_not_found_creating_new")
            try:
                _, key = await service.create_integration(self.collection_id)
                return key
            except Exception as e:
                _log.error("integration_creation_failed", error=str(e))
                raise


# Module-level singleton.
_BOOTSTRAP_INSTANCE = ProvablyBootstrapCache()
