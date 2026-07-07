"""Tests for the call_ref flow — mapping claims to intercepts by call_ref column."""

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcerykit.errors import SourceryKitStorageError
from sourcerykit.handoff.payload_builder import _resolve_claim
from sourcerykit.schemas import HandoffClaim

_call_ref_1 = str(uuid.uuid4())
_call_ref_2 = str(uuid.uuid4())

_resp_london = {"temperature_2m": 15.0, "unit": "celsius"}
_resp_paris = {"temperature_2m": 22.0, "unit": "celsius"}


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    from sourcerykit.config import get_settings, load_app_dir_config, load_local_env

    get_settings.cache_clear()
    load_app_dir_config.cache_clear()
    load_local_env.cache_clear()
    monkeypatch.setenv("PROVABLY_API_KEY", "k")
    monkeypatch.setenv("SOURCERYKIT_ORG_ID", str(uuid.uuid4()))
    monkeypatch.setenv("SOURCERYKIT_POSTGRES_URL", "postgresql://x")
    monkeypatch.setenv("SOURCERYKIT_PROVABLY_MCP_URL", "https://mcp.example.com")


def _mock_engine_for_call_ref(call_ref: str, response_payload: dict[str, Any]) -> MagicMock:
    """Return a mock engine that yields one intercept row matching call_ref."""
    mock_row = MagicMock()
    mock_row.id = uuid.uuid4()
    mock_row.request_payload = "{}"
    mock_row.raw_response = json.dumps(response_payload)
    mock_row.call_ref = call_ref

    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row
    mock_result.scalar.return_value = uuid.uuid4()

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_ctx
    mock_engine.begin.return_value = mock_ctx
    return mock_engine


class TestResolveClaimCallRef:
    async def test_call_ref_looks_up_by_call_ref_column(self) -> None:
        """When call_ref is present, _resolve_claim uses it to query the call_ref column."""
        raw = {
            "action_name": "get_weather_location",
            "call_ref": _call_ref_1,
            "claimed_value": [{"path": "$.temperature_2m", "value": "15.0"}],
            "verification_mode": "field_extraction",
        }

        mock_engine = _mock_engine_for_call_ref(_call_ref_1, _resp_london)
        mock_qid = uuid.uuid4()

        with (
            patch("sourcerykit.intercept._loader.get_engine", return_value=mock_engine),
            patch("sourcerykit.handoff.payload_builder.get_engine", return_value=mock_engine),
            patch(
                "sourcerykit.handoff.payload_builder.create_query_record_for_intercept",
                AsyncMock(return_value=(mock_qid, "https://example.com/q/1")),
            ),
        ):
            claim, qurl, qid = await _resolve_claim(uuid.uuid4(), raw, "demo")

        assert isinstance(claim, HandoffClaim)
        assert claim.call_ref == _call_ref_1
        assert claim.action_name == "get_weather_location"
        assert claim.query_id == mock_qid

    async def test_two_claims_with_different_call_refs_resolve_independently(self) -> None:
        """Two claims with different call_refs must not interfere with each other."""
        raw_london = {
            "action_name": "get_weather_location",
            "call_ref": _call_ref_1,
            "claimed_value": [{"path": "$.temperature_2m", "value": "15.0"}],
            "verification_mode": "field_extraction",
        }
        raw_paris = {
            "action_name": "get_weather_location",
            "call_ref": _call_ref_2,
            "claimed_value": [{"path": "$.temperature_2m", "value": "22.0"}],
            "verification_mode": "field_extraction",
        }

        mock_qid = uuid.uuid4()
        eng_london = _mock_engine_for_call_ref(_call_ref_1, _resp_london)
        eng_paris = _mock_engine_for_call_ref(_call_ref_2, _resp_paris)

        with (
            patch("sourcerykit.intercept._loader.get_engine", return_value=eng_london),
            patch("sourcerykit.handoff.payload_builder.get_engine", return_value=eng_london),
            patch(
                "sourcerykit.handoff.payload_builder.create_query_record_for_intercept",
                AsyncMock(return_value=(mock_qid, "https://example.com/q/1")),
            ),
        ):
            claim_london, _, _ = await _resolve_claim(uuid.uuid4(), raw_london, "demo")

        with (
            patch("sourcerykit.intercept._loader.get_engine", return_value=eng_paris),
            patch("sourcerykit.handoff.payload_builder.get_engine", return_value=eng_paris),
            patch(
                "sourcerykit.handoff.payload_builder.create_query_record_for_intercept",
                AsyncMock(return_value=(mock_qid, "https://example.com/q/2")),
            ),
        ):
            claim_paris, _, _ = await _resolve_claim(uuid.uuid4(), raw_paris, "demo")

        assert claim_london.call_ref == _call_ref_1
        assert claim_paris.call_ref == _call_ref_2
        assert claim_london.call_ref != claim_paris.call_ref

    async def test_missing_call_ref_raises(self) -> None:
        """Claims without call_ref must raise."""
        raw = {
            "action_name": "get_weather_location",
            "claimed_value": [{"path": "$.temperature_2m", "value": "15.0"}],
            "verification_mode": "field_extraction",
        }
        with pytest.raises(SourceryKitStorageError, match="missing required call_ref"):
            await _resolve_claim(uuid.uuid4(), raw, "demo")
