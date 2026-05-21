"""Provably bootstrap: middleware + database + collection + integration."""

from dataclasses import dataclass, field
from uuid import UUID

from agentkit.db import get_connection_info
from agentkit.logger import get_logger
from agentkit.provably import service
from agentkit.provably.errors import ProvablyError

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
        self.middleware_id = await self._resolve_middleware()

        connection_info = get_connection_info()
        self.database_id = await self._resolve_database(connection_info)

        ids = await service.get_database_schema_id_and_table_id(self.middleware_id, connection_info)
        self.schema_id = ids["schema_id"]
        self.table_id = ids["table_id"]

        self.collection_id = await self._resolve_collection()
        self.integration_key = await self._resolve_integration_key()

    async def _resolve_middleware(self) -> UUID:
        try:
            return await service.get_middleware_id()
        except ProvablyError:
            _log.info("middleware_not_found_creating_new")
            return await service.create_middleware()

    async def _resolve_database(self, database) -> UUID:
        assert self.middleware_id is not None
        try:
            return await service.get_database_id(self.middleware_id, database)
        except ProvablyError:
            _log.info("database_not_found_creating_new")
            return await service.create_database(self.middleware_id, database)

    async def _resolve_collection(self) -> UUID:
        assert self.middleware_id is not None
        assert self.database_id is not None
        assert self.schema_id is not None
        assert self.table_id is not None
        try:
            return await service.get_collection_id()
        except ProvablyError:
            _log.info("collection_not_found_creating_new")
            columns = await service.get_columns_from_database(
                self.middleware_id, self.database_id, self.schema_id, self.table_id
            )
            return await service.create_collection(
                self.middleware_id, self.database_id, self.schema_id, self.table_id, columns
            )

    async def _resolve_integration_key(self) -> str:
        assert self.collection_id is not None
        try:
            return await service.get_integration_intercepts_api_key(self.collection_id)
        except ProvablyError:
            _log.info("integration_not_found_creating_new")
            _, key = await service.create_integration(self.collection_id)
            return key


# Module-level singleton.
_BOOTSTRAP_INSTANCE = ProvablyBootstrapCache()
