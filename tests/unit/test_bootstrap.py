"""Tests for sourcerykit.bootstrap.bootstrap.bootstrap_system."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcerykit.bootstrap.bootstrap import bootstrap_system, get_bootstrap
from sourcerykit.errors import SourceryKitBootstrapError, SourceryKitStorageError


class TestBootstrapSystem:
    async def test_happy_path_calls_all_steps(self) -> None:
        mock_engine = MagicMock()
        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_engine.begin.return_value = mock_conn_ctx

        with (
            patch("sourcerykit.bootstrap.bootstrap.get_settings") as mock_cfg,
            patch("sourcerykit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("sourcerykit.bootstrap.bootstrap._BOOTSTRAP_INSTANCE") as mock_cache,
            patch("sourcerykit.bootstrap.bootstrap.init_interceptor") as mock_init,
            patch("sourcerykit.bootstrap.bootstrap.provably_service") as mock_svc,
        ):
            settings = MagicMock()
            settings.postgres_url = "postgresql://test"
            settings.has_bootstrap_ids = False
            settings.project_name = "test-project"
            mock_cfg.return_value = settings
            mock_svc.get_sandbox_status = AsyncMock(return_value=(None, False))
            mock_cache.run_handshake = AsyncMock()
            await bootstrap_system()

        mock_cfg.assert_called_once()
        mock_cache.run_handshake.assert_awaited_once()
        mock_init.assert_called_once()

    async def test_raises_storage_error_when_db_schema_creation_fails(self) -> None:
        mock_engine = MagicMock()
        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("db unavailable"))
        mock_engine.begin.return_value = mock_conn_ctx

        settings = MagicMock()
        settings.postgres_url = "postgresql://test"

        with (
            patch("sourcerykit.bootstrap.bootstrap.get_settings", return_value=settings),
            patch("sourcerykit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("sourcerykit.bootstrap.bootstrap.provably_service") as mock_svc,
        ):
            mock_svc.get_sandbox_status = AsyncMock(return_value=(None, False))
            with pytest.raises(SourceryKitStorageError):
                await bootstrap_system()

    async def test_raises_bootstrap_error_when_handshake_fails(self) -> None:
        mock_engine = MagicMock()
        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_engine.begin.return_value = mock_conn_ctx

        settings = MagicMock()
        settings.postgres_url = "postgresql://test"
        settings.has_bootstrap_ids = False
        settings.project_name = "test-project"

        with (
            patch("sourcerykit.bootstrap.bootstrap.get_settings", return_value=settings),
            patch("sourcerykit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("sourcerykit.bootstrap.bootstrap._BOOTSTRAP_INSTANCE") as mock_cache,
            patch("sourcerykit.bootstrap.bootstrap.provably_service") as mock_svc,
        ):
            mock_svc.get_sandbox_status = AsyncMock(return_value=(None, False))
            mock_cache.run_handshake = AsyncMock(side_effect=RuntimeError("handshake failed"))
            with pytest.raises(RuntimeError, match="handshake failed"):
                await bootstrap_system()

    async def test_propagates_sourcerykit_error_from_handshake(self) -> None:
        mock_engine = MagicMock()
        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_engine.begin.return_value = mock_conn_ctx

        settings = MagicMock()
        settings.postgres_url = "postgresql://test"
        settings.has_bootstrap_ids = False
        settings.project_name = "test-project"

        with (
            patch("sourcerykit.bootstrap.bootstrap.get_settings", return_value=settings),
            patch("sourcerykit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("sourcerykit.bootstrap.bootstrap._BOOTSTRAP_INSTANCE") as mock_cache,
            patch("sourcerykit.bootstrap.bootstrap.provably_service") as mock_svc,
        ):
            mock_svc.get_sandbox_status = AsyncMock(return_value=(None, False))
            mock_cache.run_handshake = AsyncMock(side_effect=SourceryKitBootstrapError("explicit"))
            with pytest.raises(SourceryKitBootstrapError, match="explicit"):
                await bootstrap_system()

    async def test_sandbox_skips_ensure_schema(self) -> None:
        mock_engine = MagicMock()

        settings = MagicMock()
        settings.postgres_url = "postgresql://sandbox/db"
        settings.has_bootstrap_ids = True
        settings.project_name = "test-project"

        with (
            patch("sourcerykit.bootstrap.bootstrap.get_settings", return_value=settings),
            patch("sourcerykit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("sourcerykit.bootstrap.bootstrap._BOOTSTRAP_INSTANCE") as mock_cache,
            patch("sourcerykit.bootstrap.bootstrap.init_interceptor") as mock_init,
            patch("sourcerykit.bootstrap.bootstrap.provably_service") as mock_svc,
            patch("sourcerykit.bootstrap.bootstrap.ensure_schema") as mock_ensure,
        ):
            mock_svc.get_sandbox_status = AsyncMock(
                return_value=({"connection_uri": "postgresql://sandbox/db", "status": "active"}, True)
            )
            mock_cache.load_from = MagicMock()
            await bootstrap_system()

        mock_ensure.assert_not_called()
        mock_init.assert_called_once()

    async def test_recreates_expired_sandbox(self) -> None:
        mock_engine = MagicMock()

        settings = MagicMock()
        settings.postgres_url = "postgresql://old-sandbox/db"
        settings.org_id = "org-123"
        settings.has_bootstrap_ids = True

        with (
            patch("sourcerykit.bootstrap.bootstrap.get_settings", return_value=settings),
            patch("sourcerykit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("sourcerykit.bootstrap.bootstrap._BOOTSTRAP_INSTANCE") as mock_cache,
            patch("sourcerykit.bootstrap.bootstrap.init_interceptor"),
            patch("sourcerykit.bootstrap.bootstrap.provably_service") as mock_svc,
            patch("sourcerykit.bootstrap.bootstrap.save_local_env") as mock_save,
            patch("sourcerykit.bootstrap.bootstrap.ensure_schema"),
        ):
            mock_svc.get_sandbox_status = AsyncMock(
                return_value=({"connection_uri": "postgresql://old-sandbox/db", "status": "expired"}, True)
            )
            mock_svc.create_sandbox = AsyncMock(return_value="postgresql://new-sandbox/db")
            mock_cache.load_from = MagicMock()

            await bootstrap_system()

        mock_svc.create_sandbox.assert_awaited_once_with("org-123")
        mock_save.assert_called_once_with(SOURCERYKIT_POSTGRES_URL="postgresql://new-sandbox/db")

    async def test_skips_recreation_for_active_sandbox(self) -> None:
        mock_engine = MagicMock()

        settings = MagicMock()
        settings.postgres_url = "postgresql://sandbox/db"
        settings.has_bootstrap_ids = True

        with (
            patch("sourcerykit.bootstrap.bootstrap.get_settings", return_value=settings),
            patch("sourcerykit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("sourcerykit.bootstrap.bootstrap._BOOTSTRAP_INSTANCE") as mock_cache,
            patch("sourcerykit.bootstrap.bootstrap.init_interceptor"),
            patch("sourcerykit.bootstrap.bootstrap.provably_service") as mock_svc,
            patch("sourcerykit.bootstrap.bootstrap.save_local_env") as mock_save,
            patch("sourcerykit.bootstrap.bootstrap.ensure_schema"),
        ):
            mock_svc.get_sandbox_status = AsyncMock(
                return_value=({"connection_uri": "postgresql://sandbox/db", "status": "active"}, True)
            )
            mock_svc.create_sandbox = AsyncMock()
            mock_cache.load_from = MagicMock()

            await bootstrap_system()

        mock_svc.create_sandbox.assert_not_awaited()
        mock_save.assert_not_called()

    async def test_skips_recreation_when_no_org_id(self) -> None:
        mock_engine = MagicMock()

        settings = MagicMock()
        settings.postgres_url = "postgresql://sandbox/db"
        settings.org_id = None
        settings.has_bootstrap_ids = True

        with (
            patch("sourcerykit.bootstrap.bootstrap.get_settings", return_value=settings),
            patch("sourcerykit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("sourcerykit.bootstrap.bootstrap._BOOTSTRAP_INSTANCE") as mock_cache,
            patch("sourcerykit.bootstrap.bootstrap.init_interceptor"),
            patch("sourcerykit.bootstrap.bootstrap.provably_service") as mock_svc,
            patch("sourcerykit.bootstrap.bootstrap.save_local_env") as mock_save,
            patch("sourcerykit.bootstrap.bootstrap.ensure_schema"),
        ):
            mock_svc.get_sandbox_status = AsyncMock(
                return_value=({"connection_uri": "postgresql://sandbox/db", "status": "expired"}, True)
            )
            mock_svc.create_sandbox = AsyncMock()
            mock_cache.load_from = MagicMock()

            await bootstrap_system()

        mock_svc.create_sandbox.assert_not_awaited()
        mock_save.assert_not_called()


class TestGetBootstrap:
    def test_returns_bootstrap_cache_instance(self) -> None:
        from sourcerykit.bootstrap._cache import ProvablyBootstrapCache

        result = get_bootstrap()
        assert isinstance(result, ProvablyBootstrapCache)
