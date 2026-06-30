"""Provably bootstrap: middleware + database + collection + integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sourcerykit.config import Settings
from sourcerykit.db._engine import ConnectionInfo, get_connection_info
from sourcerykit.errors import SourceryKitBootstrapError, SourceryKitError
from sourcerykit.logger import get_logger
from sourcerykit.provably._errors import ProvablyError
from sourcerykit.provably.service import service

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
    collection_name: str | None = field(default=None)

    def load_from(self, settings: Settings) -> None:
        """Populate cache from pre-resolved settings."""
        self.middleware_id = settings.middleware_id
        self.database_id = settings.database_id
        self.schema_id = settings.schema_id
        self.table_id = settings.table_id
        self.collection_id = settings.collection_id
        self.integration_key = settings.integration_key
        self.collection_name = settings.project_name or None

    async def run_handshake(self, project_name: str) -> None:
        """Resolve or create all required Provably resources."""
        try:
            self.middleware_id = await self._resolve_middleware()

            connection_info = get_connection_info()
            self.database_id = await self._resolve_database(connection_info)

            ids = await service.get_database_schema_id_and_table_id(self.middleware_id, connection_info)
            self.schema_id = ids["schema_id"]
            self.table_id = ids["table_id"]

            self.collection_name = project_name
            self.collection_id = await self._resolve_collection(project_name)
            self.integration_key = await self._resolve_integration_key()
        except SourceryKitError:
            raise
        except Exception as e:
            _log.error("handshake_failed_unexpected", error=str(e))
            raise SourceryKitBootstrapError("Unexpected error during Provably handshake") from e

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

    async def _resolve_database(self, database: ConnectionInfo) -> UUID:
        if self.middleware_id is None:
            raise SourceryKitBootstrapError("middleware_id is not set; run_handshake() must be called first")
        try:
            return await service.get_database_id(self.middleware_id, database)
        except ProvablyError:
            _log.info("database_not_found_creating_new")
            try:
                return await service.create_database(self.middleware_id, database)
            except Exception as e:
                _log.error("database_creation_failed", error=str(e))
                raise

    async def _resolve_collection(self, project_name: str) -> UUID:
        if self.middleware_id is None or self.database_id is None or self.schema_id is None or self.table_id is None:
            raise SourceryKitBootstrapError(
                "middleware_id, database_id, schema_id, and table_id must all be resolved before creating a collection"
            )
        try:
            return await service.get_collection_id(name=project_name)
        except (ProvablyError, ValueError):
            _log.info("collection_not_found_creating_new")
            try:
                columns = await service.get_columns_from_database(
                    self.middleware_id, self.database_id, self.schema_id, self.table_id
                )
                return await service.create_collection(
                    self.middleware_id,
                    self.database_id,
                    self.schema_id,
                    self.table_id,
                    columns,
                    name=project_name,
                )
            except Exception as e:
                _log.error("collection_creation_failed", error=str(e))
                raise

    async def _resolve_integration_key(self) -> str:
        if self.collection_id is None:
            raise SourceryKitBootstrapError("collection_id is not set; _resolve_collection() must succeed first")
        _, key = await service.create_integration(self.collection_id)
        return key


# Module-level singleton.
_BOOTSTRAP_INSTANCE = ProvablyBootstrapCache()
