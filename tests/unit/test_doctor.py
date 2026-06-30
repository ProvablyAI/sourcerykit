"""Tests for sourcerykit.cli.doctor."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from sourcerykit.cli.doctor import (
    _check_api_key_and_org,
    _check_bootstrap_ids,
    _check_postgres,
    _check_project_name,
    _deep_check_collection_and_ids,
    _deep_check_integration,
    _run_deep_check_collection_and_ids,
    _run_deep_check_integration,
    run_doctor,
)
from sourcerykit.config import Settings
from sourcerykit.provably._errors import ProvablyConnectionError, ProvablyUnauthorizedError

_ORG_ID = uuid.uuid4()
_API_KEY = "zk-12345678-1234-1234-1234-123456789abc"


def _make_settings(
    *,
    api_key: str = _API_KEY,
    org_id: uuid.UUID = _ORG_ID,
    postgres_url: str = "postgresql://u:p@host/db",
    project_name: str = "my-project",
    middleware_id: uuid.UUID | None = None,
    database_id: uuid.UUID | None = None,
    schema_id: uuid.UUID | None = None,
    table_id: uuid.UUID | None = None,
    collection_id: uuid.UUID | None = None,
    integration_key: str | None = None,
) -> Settings:
    """Build a real Settings with sensible defaults."""
    return Settings(
        api_key=api_key,
        org_id=org_id,
        postgres_url=postgres_url,
        project_name=project_name,
        middleware_id=middleware_id,
        database_id=database_id,
        schema_id=schema_id,
        table_id=table_id,
        collection_id=collection_id,
        integration_key=integration_key,
    )


def _make_full_settings(**overrides: object) -> Settings:
    """Build a Settings with all bootstrap IDs populated."""
    return _make_settings(
        middleware_id=overrides.get("middleware_id") or uuid.uuid4(),  # type: ignore[arg-type]
        database_id=overrides.get("database_id") or uuid.uuid4(),  # type: ignore[arg-type]
        schema_id=overrides.get("schema_id") or uuid.uuid4(),  # type: ignore[arg-type]
        table_id=overrides.get("table_id") or uuid.uuid4(),  # type: ignore[arg-type]
        collection_id=overrides.get("collection_id") or uuid.uuid4(),  # type: ignore[arg-type]
        integration_key=overrides.get("integration_key") or "i-abc123",  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# _check_api_key_and_org
# ---------------------------------------------------------------------------


class TestCheckApiKeyAndOrg:
    def test_missing_api_key(self) -> None:
        s = MagicMock()
        s.api_key = ""
        ok, msg = _check_api_key_and_org(s)
        assert ok is False
        assert "PROVABLY_API_KEY is missing" in msg

    def test_valid_key_and_org(self) -> None:
        s = _make_settings()
        orgs = [{"id": str(s.org_id), "name": "My Org"}]
        with patch("sourcerykit.cli.doctor.auth_service") as mock_auth:
            mock_auth.list_organizations = AsyncMock(return_value=orgs)
            ok, msg = _check_api_key_and_org(s)
        assert ok is True
        assert "API key valid" in msg

    def test_unauthorized(self) -> None:
        s = _make_settings()
        with patch("sourcerykit.cli.doctor.auth_service") as mock_auth:
            mock_auth.list_organizations = AsyncMock(side_effect=ProvablyUnauthorizedError("bad"))
            ok, msg = _check_api_key_and_org(s)
        assert ok is False
        assert "invalid or expired" in msg

    def test_connection_error(self) -> None:
        s = _make_settings()
        with patch("sourcerykit.cli.doctor.auth_service") as mock_auth:
            mock_auth.list_organizations = AsyncMock(side_effect=ProvablyConnectionError("unreachable"))
            ok, msg = _check_api_key_and_org(s)
        assert ok is False
        assert "Cannot reach Provably API" in msg

    def test_org_not_found(self) -> None:
        s = _make_settings()
        orgs = [{"id": str(uuid.uuid4()), "name": "Other Org"}]
        with patch("sourcerykit.cli.doctor.auth_service") as mock_auth:
            mock_auth.list_organizations = AsyncMock(return_value=orgs)
            ok, msg = _check_api_key_and_org(s)
        assert ok is False
        assert "not found" in msg


# ---------------------------------------------------------------------------
# _check_postgres
# ---------------------------------------------------------------------------


class TestCheckPostgres:
    def test_missing_url(self) -> None:
        s = _make_settings(postgres_url="")
        ok, msg = _check_postgres(s)
        assert ok is False
        assert "SOURCERYKIT_POSTGRES_URL is missing" in msg

    def test_connected(self) -> None:
        s = _make_settings()
        with patch("sourcerykit.cli.doctor.run_connectivity_check", return_value=True):
            ok, msg = _check_postgres(s)
        assert ok is True
        assert "successful" in msg

    def test_connection_failed(self) -> None:
        s = _make_settings()
        with patch("sourcerykit.cli.doctor.run_connectivity_check", return_value=False):
            ok, msg = _check_postgres(s)
        assert ok is False
        assert "connection failed" in msg.lower()


# ---------------------------------------------------------------------------
# _check_project_name
# ---------------------------------------------------------------------------


class TestCheckProjectName:
    def test_set(self) -> None:
        s = _make_settings(project_name="my-proj")
        ok, msg = _check_project_name(s)
        assert ok is True
        assert "my-proj" in msg

    def test_missing(self) -> None:
        s = _make_settings(project_name="")
        ok, msg = _check_project_name(s)
        assert ok is False
        assert "missing" in msg.lower()


# ---------------------------------------------------------------------------
# _check_bootstrap_ids
# ---------------------------------------------------------------------------


class TestCheckBootstrapIds:
    def test_all_present(self) -> None:
        s = _make_full_settings()
        ok, msg = _check_bootstrap_ids(s)
        assert ok is True
        assert "All bootstrap IDs present" in msg

    def test_some_missing(self) -> None:
        s = _make_settings()  # no bootstrap IDs set
        ok, msg = _check_bootstrap_ids(s)
        assert ok is False
        assert "Missing" in msg


# ---------------------------------------------------------------------------
# _deep_check_collection_and_ids
# ---------------------------------------------------------------------------


class TestDeepCheckCollectionAndIds:
    async def test_all_match(self) -> None:
        s = _make_full_settings()
        with patch("sourcerykit.cli.doctor.service") as mock_svc, patch("sourcerykit.cli.doctor.get_connection_info"):
            mock_svc.get_middleware_id = AsyncMock(return_value=s.middleware_id)
            mock_svc.get_database_id = AsyncMock(return_value=s.database_id)
            mock_svc.get_database_schema_id_and_table_id = AsyncMock(
                return_value={"schema_id": s.schema_id, "table_id": s.table_id}
            )
            mock_svc.get_collection_id = AsyncMock(return_value=s.collection_id)
            ok, msg = await _deep_check_collection_and_ids(s)
        assert ok is True
        assert "verified" in msg.lower()

    async def test_middleware_mismatch(self) -> None:
        s = _make_full_settings()
        with patch("sourcerykit.cli.doctor.service") as mock_svc, patch("sourcerykit.cli.doctor.get_connection_info"):
            mock_svc.get_middleware_id = AsyncMock(return_value=uuid.uuid4())
            ok, msg = await _deep_check_collection_and_ids(s)
        assert ok is False
        assert "Middleware mismatch" in msg

    async def test_collection_mismatch(self) -> None:
        s = _make_full_settings()
        with patch("sourcerykit.cli.doctor.service") as mock_svc, patch("sourcerykit.cli.doctor.get_connection_info"):
            mock_svc.get_middleware_id = AsyncMock(return_value=s.middleware_id)
            mock_svc.get_database_id = AsyncMock(return_value=s.database_id)
            mock_svc.get_database_schema_id_and_table_id = AsyncMock(
                return_value={"schema_id": s.schema_id, "table_id": s.table_id}
            )
            mock_svc.get_collection_id = AsyncMock(return_value=uuid.uuid4())
            ok, msg = await _deep_check_collection_and_ids(s)
        assert ok is False
        assert "Collection mismatch" in msg

    async def test_missing_bootstrap_ids(self) -> None:
        s = _make_settings()  # no bootstrap IDs
        ok, msg = await _deep_check_collection_and_ids(s)
        assert ok is False
        assert "Bootstrap IDs missing" in msg


# ---------------------------------------------------------------------------
# _deep_check_integration
# ---------------------------------------------------------------------------


class TestDeepCheckIntegration:
    async def test_valid_format(self) -> None:
        s = _make_full_settings(integration_key="i-abc123")
        ok, msg = await _deep_check_integration(s)
        assert ok is True
        assert "valid" in msg.lower()

    async def test_missing_key(self) -> None:
        s = _make_settings(integration_key="")
        ok, msg = await _deep_check_integration(s)
        assert ok is False
        assert "missing" in msg.lower()

    async def test_wrong_format(self) -> None:
        s = _make_settings(integration_key="not-an-integration-key")
        ok, msg = await _deep_check_integration(s)
        assert ok is False
        assert "unexpected format" in msg.lower()


# ---------------------------------------------------------------------------
# _run_deep_check_collection_and_ids / _run_deep_check_integration
# ---------------------------------------------------------------------------


class TestRunDeepChecks:
    def test_run_deep_check_collection_handles_unauthorized(self) -> None:
        s = _make_full_settings()
        with patch(
            "sourcerykit.cli.doctor._deep_check_collection_and_ids",
            side_effect=ProvablyUnauthorizedError("bad"),
        ):
            ok, msg = _run_deep_check_collection_and_ids(s)
        assert ok is False
        assert "expired" in msg.lower()

    def test_run_deep_check_collection_handles_connection_error(self) -> None:
        s = _make_full_settings()
        with patch(
            "sourcerykit.cli.doctor._deep_check_collection_and_ids",
            side_effect=ProvablyConnectionError("fail"),
        ):
            ok, msg = _run_deep_check_collection_and_ids(s)
        assert ok is False
        assert "Cannot reach" in msg

    def test_run_deep_check_integration_handles_unauthorized(self) -> None:
        s = _make_full_settings()
        with patch(
            "sourcerykit.cli.doctor._deep_check_integration",
            side_effect=ProvablyUnauthorizedError("bad"),
        ):
            ok, msg = _run_deep_check_integration(s)
        assert ok is False
        assert "expired" in msg.lower()


# ---------------------------------------------------------------------------
# run_doctor
# ---------------------------------------------------------------------------


class TestRunDoctor:
    def test_all_checks_pass(self) -> None:
        s = _make_settings()
        with (
            patch("sourcerykit.cli.doctor.get_settings", return_value=s),
            patch("sourcerykit.cli.doctor._check_api_key_and_org", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._check_postgres", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._check_project_name", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._check_bootstrap_ids", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._run_deep_check_collection_and_ids", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._run_deep_check_integration", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor.console"),
        ):
            run_doctor()  # must not raise

    def test_some_checks_fail(self) -> None:
        s = _make_settings()
        with (
            patch("sourcerykit.cli.doctor.get_settings", return_value=s),
            patch("sourcerykit.cli.doctor._check_api_key_and_org", return_value=(False, "bad key")),
            patch("sourcerykit.cli.doctor._check_postgres", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._check_project_name", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._check_bootstrap_ids", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._run_deep_check_collection_and_ids", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._run_deep_check_integration", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor.console"),
        ):
            run_doctor()  # must not raise

    def test_fix_attempts_bootstrap(self) -> None:
        s = _make_settings()
        with (
            patch("sourcerykit.cli.doctor.get_settings", return_value=s),
            patch("sourcerykit.cli.doctor._check_api_key_and_org", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._check_postgres", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._check_project_name", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._check_bootstrap_ids", return_value=(False, "missing")),
            patch("sourcerykit.cli.doctor._run_deep_check_collection_and_ids", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor._run_deep_check_integration", return_value=(True, "ok")),
            patch("sourcerykit.cli.doctor.run_full_bootstrap", return_value=True),
            patch("sourcerykit.cli.doctor.console"),
        ):
            run_doctor(fix=True)

    def test_cannot_load_settings(self) -> None:
        with (
            patch("sourcerykit.cli.doctor.get_settings", side_effect=Exception("no config")),
            patch("sourcerykit.cli.doctor.console"),
        ):
            run_doctor()  # must not raise
