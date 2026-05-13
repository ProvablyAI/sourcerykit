"""Provably API — named methods for every endpoint.

:class:`ProvablyAPI` covers five resource groups:
- **Middlewares** — create the Provably middleware for an org
- **Databases / Schemas / Tables / Columns** — onboard and inspect the connected database
- **Collections** — manage query collections
- **Integrations** — register external integrations
- **Queries & Proofs** — run queries, generate proofs, poll status
"""

from __future__ import annotations

from typing import Any

import httpx

from agentkit.config import Settings, get_settings
from agentkit.provably._http import http


class ProvablyAPI:
    """Provably API endpoints."""

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        self.org_id = s.org_id
        self.app = s.provably_app

    def _org(self) -> str:
        return f"/api/v1/organizations/{self.org_id}"

    # ------------------------------------------------------------------
    # Middlewares
    # ------------------------------------------------------------------

    def create_middleware(self) -> dict[str, Any]:
        return http.post(f"{self._org()}/middlewares/provably")

    # ------------------------------------------------------------------
    # Databases
    # ------------------------------------------------------------------

    def onboard_database(self, middleware_id: str, body: dict[str, Any]) -> httpx.Response:
        return http.post(f"{self._org()}/middlewares/{middleware_id}/databases", body)

    def list_databases(self, middleware_id: str) -> Any:
        return http.get(f"{self._org()}/middlewares/{middleware_id}/databases")

    def list_databases_for_org(self) -> Any:
        return http.get(f"{self._org()}/databases")

    # ------------------------------------------------------------------
    # Schemas / Tables / Columns
    # ------------------------------------------------------------------

    def list_schemas(self, middleware_id: str, database_id: str) -> Any:
        return http.get(f"{self._org()}/middlewares/{middleware_id}/databases/{database_id}/schemas")

    def list_tables(self, middleware_id: str, database_id: str, schema_id: str) -> Any:
        return http.get(f"{self._org()}/middlewares/{middleware_id}/databases/{database_id}/schemas/{schema_id}/tables")

    def list_columns(self, middleware_id: str, database_id: str, schema_id: str, table_id: str) -> Any:
        return http.get(
            f"{self._org()}/middlewares/{middleware_id}"
            f"/databases/{database_id}/schemas/{schema_id}/tables/{table_id}/columns"
        )

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def get_data(self) -> Any:
        return http.get(f"{self._org()}/data")

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def list_collections(self) -> Any:
        return http.get(f"{self._org()}/collections")

    def create_collection(self, body: dict[str, Any]) -> httpx.Response:
        return http.post(f"{self._org()}/collections", body)

    # ------------------------------------------------------------------
    # Integrations
    # ------------------------------------------------------------------

    def create_integration(self, body: dict[str, Any]) -> dict[str, Any]:
        return http.post(f"{self._org()}/integrations", body)

    def list_integrations(self) -> Any:
        return http.get(f"{self._org()}/integrations")

    # ------------------------------------------------------------------
    # Preprocess
    # ------------------------------------------------------------------

    def start_preprocess(self, middleware_id: str, table_id: str) -> dict[str, Any]:
        return http.post(
            f"{self._org()}/middlewares/{middleware_id}/tables/{table_id}/preprocess",
            {"force": True},
        )

    def get_preprocess_status(self, middleware_id: str, table_id: str) -> dict[str, Any]:
        return http.get(f"{self._org()}/middlewares/{middleware_id}/tables/{table_id}/preprocess")

    # ------------------------------------------------------------------
    # Queries / Proofs
    # ------------------------------------------------------------------

    def run_query(self, middleware_id: str, collection_id: str, sql: str) -> dict[str, Any]:
        return http.post(
            f"{self._org()}/middlewares/{middleware_id}/query",
            {"query": sql, "require_proof": True, "collection_id": collection_id},
        )

    def get_query(self, query_id: str) -> dict[str, Any]:
        return http.get(f"{self._org()}/queries/{query_id}")

    def generate_proof(self, query_id: str) -> dict[str, Any]:
        return http.post(f"{self._org()}/queries/{query_id}/generate_proof")

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def query_record_url(self, query_record_id: str) -> str:
        """Provably Data Admin URL for a query record."""
        if not query_record_id:
            raise ValueError("query_record_id is required")
        return f"{self.app}/org/{self.org_id}/query-record/{query_record_id.strip()}"


# Shared singleton
api = ProvablyAPI()
