"""Provably bootstrap: middleware + database + collection + integration."""

from dataclasses import dataclass, field
from uuid import UUID

from agentkit.db import get_connection_info
from agentkit.logger import get_logger
from agentkit.provably import service
from agentkit.provably.errors import ProvablyError

_log = get_logger(__name__)


@dataclass
class _Bootstrap:
    """Holds the resolved Provably resource IDs obtained during bootstrapping.

    Each field is populated by `bootstrap()` and remains cached for the
    lifetime of the process.
    """

    middleware_id: UUID | None = field(default=None)
    database_id: UUID | None = field(default=None)
    schema_id: UUID | None = field(default=None)
    table_id: UUID | None = field(default=None)
    collection_id: UUID | None = field(default=None)

    async def bootstrap(self) -> None:
        """Resolve or create all required Provably resources and cache their IDs.

        For each resource the strategy is: attempt to fetch the existing ID
        first; if the service returns a `ProvablyError` (resource not found),
        create it instead.
        """
        # --- Middleware --------------------------------------------------
        try:
            self.middleware_id = await service.get_middleware_id()
        except ProvablyError:
            _log.info("middleware_not_found_creating_new")
            self.middleware_id = await service.create_middleware()

        # --- Database ---------------------------------------------------
        database = get_connection_info()
        try:
            self.database_id = await service.get_database_id(self.middleware_id, database)
        except ProvablyError:
            _log.info("database_not_found_creating_new")
            self.database_id = await service.create_database(self.middleware_id, database)

        # --- Collection -------------------------------------------------
        # Schema and table IDs are only needed when creating the collection,
        # so they are resolved lazily inside the except branch.
        try:
            self.collection_id = await service.get_collection_id()
        except ProvablyError:
            _log.info("collection_not_found_creating_new")
            ids = await service.get_database_schema_id_and_table_id(self.middleware_id, database)
            self.schema_id = ids["schema_id"]
            self.table_id = ids["table_id"]

            columns = await service.get_columns_from_database(
                self.middleware_id, self.database_id, self.schema_id, self.table_id
            )
            self.collection_id = await service.create_collection(
                self.middleware_id, self.database_id, self.schema_id, self.table_id, columns
            )


# Module-level singleton.
_BOOTSTRAP = _Bootstrap()
