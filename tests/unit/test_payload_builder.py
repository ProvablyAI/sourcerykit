"""Tests for agentkit.handoff.payload_builder.build_handoff_payload."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentkit.handoff.payload_builder import DEFAULT_HANDOFF_TASK, build_handoff_payload

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


@pytest.fixture
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTKIT_API_KEY", "k")
    monkeypatch.setenv("AGENTKIT_ORG_ID", str(_ORG))
    monkeypatch.setenv("AGENTKIT_POSTGRES_URL", "postgresql://x")
    monkeypatch.setenv("AGENTKIT_PROVABLY_MCP_URL", "https://mcp.example.com")


class TestBuildHandoffPayloadEmpty:
    async def test_returns_empty_claims_for_none_input(self, _env: None) -> None:
        with (
            patch("agentkit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("agentkit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("agentkit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("agentkit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], []))),
        ):
            hp = await build_handoff_payload(None)
        assert hp.claims == []
        assert hp.task == DEFAULT_HANDOFF_TASK

    async def test_field_guide_populated(self, _env: None) -> None:
        with (
            patch("agentkit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("agentkit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("agentkit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("agentkit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], []))),
        ):
            hp = await build_handoff_payload(None)
        assert isinstance(hp.field_guide, dict)
        assert len(hp.field_guide) > 0

    async def test_custom_task_is_propagated(self, _env: None) -> None:
        with (
            patch("agentkit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("agentkit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("agentkit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("agentkit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], []))),
        ):
            hp = await build_handoff_payload(None, task="My custom task")
        assert hp.task == "My custom task"

    async def test_raises_if_bootstrap_has_no_integration_key(self, _env: None) -> None:
        bootstrap_no_key = _mock_bootstrap(integration_key=None)  # type: ignore[arg-type]
        with (
            patch("agentkit.handoff.payload_builder.get_bootstrap", return_value=bootstrap_no_key),
            patch("agentkit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
        ):
            with pytest.raises(RuntimeError, match="bootstrap"):
                await build_handoff_payload(None)

    async def test_run_id_forwarded(self, _env: None) -> None:
        rid = uuid.uuid4()
        with (
            patch("agentkit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("agentkit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("agentkit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("agentkit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], []))),
        ):
            hp = await build_handoff_payload(None, run_id=rid)
        assert hp.run_id == rid

    async def test_integration_api_key_from_bootstrap(self, _env: None) -> None:
        with (
            patch("agentkit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap("my-int-key")),
            patch("agentkit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("agentkit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("agentkit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], []))),
        ):
            hp = await build_handoff_payload(None)
        assert hp.integration_api_key == "my-int-key"

    async def test_reasoning_extracted_from_blob(self, _env: None) -> None:
        with (
            patch("agentkit.handoff.payload_builder.get_bootstrap", return_value=_mock_bootstrap()),
            patch("agentkit.handoff.payload_builder.get_settings", return_value=_mock_settings()),
            patch("agentkit.handoff.payload_builder.list_all_trusted_endpoints", AsyncMock(return_value=[])),
            patch("agentkit.handoff.payload_builder._build_claims", AsyncMock(return_value=([], [], []))),
        ):
            hp = await build_handoff_payload({"reasoning": "because reasons"})
        assert hp.reasoning == "because reasons"
