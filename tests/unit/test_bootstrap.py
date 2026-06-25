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
        ):
            settings = MagicMock()
            settings.postgres_url = "postgresql://test"
            settings.has_bootstrap_ids = False
            settings.project_name = "test-project"
            mock_cfg.return_value = settings
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
        ):
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
        ):
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
        ):
            mock_cache.run_handshake = AsyncMock(side_effect=SourceryKitBootstrapError("explicit"))
            with pytest.raises(SourceryKitBootstrapError, match="explicit"):
                await bootstrap_system()


class TestGetBootstrap:
    def test_returns_bootstrap_cache_instance(self) -> None:
        from sourcerykit.bootstrap._cache import ProvablyBootstrapCache

        result = get_bootstrap()
        assert isinstance(result, ProvablyBootstrapCache)
