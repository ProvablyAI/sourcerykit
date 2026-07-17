"""Tests for sourcerykit.handoff.payload_builder.build_handoff_payload."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcerykit.config import get_settings, load_app_dir_config, load_local_env
from sourcerykit.handoff.payload_builder import DEFAULT_HANDOFF_TASK, build_handoff_payload

_ORG = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _mock_bootstrap(integration_key: str = "int-key-123") -> MagicMock:
    bootstrap = MagicMock()
    bootstrap.integration_key = integration_key
    return bootstrap


def _mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.provably_mcp = "https://mcp.example.com"
    settings.org_id = _ORG
    return settings


def _mock_engine() -> MagicMock:
    mock_conn = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_ctx
    return mock_engine


@pytest.fixture
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    load_app_dir_config.cache_clear()
    load_local_env.cache_clear()
    monkeypatch.setenv("PROVABLY_API_KEY", "k")
    monkeypatch.setenv("SOURCERYKIT_ORG_ID", str(_ORG))
    monkeypatch.setenv("SOURCERYKIT_POSTGRES_URL", "postgresql://x")
    monkeypatch.setenv("SOURCERYKIT_PROVABLY_MCP_URL", "https://mcp.example.com")


class TestBuildHandoffPayloadEmpty:
    async def test_returns_empty_claims_for_none_input(self, _env: None) -> None:
        with (
            patch("sourcerykit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("sourcerykit.handoff.payload_builder.get_engine", return_value=_mock_engine()),
            patch("sourcerykit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("sourcerykit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], [], []))),
        ):
            hp = await build_handoff_payload(None, prompt="test")
        assert hp.claims == []
        assert hp.task == DEFAULT_HANDOFF_TASK

    async def test_field_guide_populated(self, _env: None) -> None:
        with (
            patch("sourcerykit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("sourcerykit.handoff.payload_builder.get_engine", return_value=_mock_engine()),
            patch("sourcerykit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("sourcerykit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], [], []))),
        ):
            hp = await build_handoff_payload(None, prompt="test")
        assert isinstance(hp.field_guide, dict)
        assert len(hp.field_guide) > 0

    async def test_custom_task_is_propagated(self, _env: None) -> None:
        with (
            patch("sourcerykit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("sourcerykit.handoff.payload_builder.get_engine", return_value=_mock_engine()),
            patch("sourcerykit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("sourcerykit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], [], []))),
        ):
            hp = await build_handoff_payload(None, prompt="test", task="My custom task")
        assert hp.task == "My custom task"

    async def test_raises_if_bootstrap_has_no_integration_key(self, _env: None) -> None:
        bootstrap_no_key = _mock_bootstrap(integration_key=None)  # type: ignore[arg-type]
        with (
            patch("sourcerykit.handoff.payload_builder.get_bootstrap", return_value=bootstrap_no_key),
            patch("sourcerykit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
        ):
            with pytest.raises(RuntimeError, match="bootstrap"):
                await build_handoff_payload(None, prompt="test")

    async def test_run_id_forwarded(self, _env: None) -> None:
        rid = uuid.uuid4()
        with (
            patch("sourcerykit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("sourcerykit.handoff.payload_builder.get_engine", return_value=_mock_engine()),
            patch("sourcerykit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("sourcerykit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], [], []))),
        ):
            hp = await build_handoff_payload(None, prompt="test", run_id=rid)
        assert hp.run_id == rid

    async def test_integration_api_key_from_bootstrap(self, _env: None) -> None:
        with (
            patch("sourcerykit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap("my-int-key")),
            patch("sourcerykit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("sourcerykit.handoff.payload_builder.get_engine", return_value=_mock_engine()),
            patch("sourcerykit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("sourcerykit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], [], []))),
        ):
            hp = await build_handoff_payload(None, prompt="test")
        assert hp.integration_api_key == "my-int-key"

    async def test_answer_extracted_from_blob(self, _env: None) -> None:
        with (
            patch("sourcerykit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("sourcerykit.handoff.payload_builder.get_engine", return_value=_mock_engine()),
            patch("sourcerykit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("sourcerykit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], [], []))),
        ):
            hp = await build_handoff_payload({"answer": "answer"}, prompt="test")
        assert hp.answer == "answer"

    async def test_answer_stored_in_trace(self, _env: None) -> None:
        mock_engine = _mock_engine()
        with (
            patch("sourcerykit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("sourcerykit.handoff.payload_builder.get_engine", return_value=mock_engine),
            patch("sourcerykit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("sourcerykit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], []))),
        ):
            await build_handoff_payload({"answer": "test answer"}, prompt="my task")
        conn = mock_engine.begin.return_value.__aenter__.return_value
        stmt = conn.execute.call_args[0][0]
        compiled = stmt.compile(compile_kwargs={"literal_binds": True})
        sql_str = str(compiled)
        assert "answer" in sql_str.lower()
