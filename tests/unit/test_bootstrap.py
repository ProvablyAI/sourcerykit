"""Tests for agentkit.bootstrap.bootstrap.bootstrap_system."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentkit.bootstrap.bootstrap import bootstrap_system, get_bootstrap
from agentkit.errors import AgentKitBootstrapError, AgentKitStorageError


class TestBootstrapSystem:
    async def test_happy_path_calls_all_steps(self) -> None:
        mock_engine = MagicMock()
        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_engine.begin.return_value = mock_conn_ctx

        with (
            patch("agentkit.bootstrap.bootstrap.get_settings") as mock_cfg,
            patch("agentkit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("agentkit.bootstrap.bootstrap._BOOTSTRAP_INSTANCE") as mock_cache,
            patch("agentkit.bootstrap.bootstrap.init_interceptor") as mock_init,
        ):
            mock_cfg.return_value = MagicMock()
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

        with (
            patch("agentkit.bootstrap.bootstrap.get_settings"),
            patch("agentkit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
        ):
            with pytest.raises(AgentKitStorageError):
                await bootstrap_system()

    async def test_raises_bootstrap_error_when_handshake_fails(self) -> None:
        mock_engine = MagicMock()
        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_engine.begin.return_value = mock_conn_ctx

        with (
            patch("agentkit.bootstrap.bootstrap.get_settings"),
            patch("agentkit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("agentkit.bootstrap.bootstrap._BOOTSTRAP_INSTANCE") as mock_cache,
        ):
            mock_cache.run_handshake = AsyncMock(side_effect=RuntimeError("handshake failed"))
            with pytest.raises(AgentKitBootstrapError):
                await bootstrap_system()

    async def test_propagates_agentkit_error_from_handshake(self) -> None:
        mock_engine = MagicMock()
        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_engine.begin.return_value = mock_conn_ctx

        with (
            patch("agentkit.bootstrap.bootstrap.get_settings"),
            patch("agentkit.bootstrap.bootstrap.get_engine", return_value=mock_engine),
            patch("agentkit.bootstrap.bootstrap._BOOTSTRAP_INSTANCE") as mock_cache,
        ):
            mock_cache.run_handshake = AsyncMock(side_effect=AgentKitBootstrapError("explicit"))
            with pytest.raises(AgentKitBootstrapError, match="explicit"):
                await bootstrap_system()


class TestGetBootstrap:
    def test_returns_bootstrap_cache_instance(self) -> None:
        from agentkit.bootstrap._cache import ProvablyBootstrapCache

        result = get_bootstrap()
        assert isinstance(result, ProvablyBootstrapCache)
