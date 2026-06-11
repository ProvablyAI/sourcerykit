"""Tests for sourcerykit.intercept._storage — hash_payload and add_intercept_row."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcerykit.errors import SourceryKitTrustError
from sourcerykit.intercept._storage import add_intercept_row, hash_payload

# ---------------------------------------------------------------------------
# hash_payload
# ---------------------------------------------------------------------------


class TestHashPayload:
    def test_returns_string(self) -> None:
        result = hash_payload({"key": "value"})
        assert isinstance(result, str)

    def test_deterministic_for_same_input(self) -> None:
        payload = {"b": 2, "a": 1}
        assert hash_payload(payload) == hash_payload(payload)

    def test_key_order_does_not_affect_hash(self) -> None:
        p1 = {"a": 1, "b": 2}
        p2 = {"b": 2, "a": 1}
        assert hash_payload(p1) == hash_payload(p2)

    def test_different_payloads_produce_different_hashes(self) -> None:
        assert hash_payload({"a": 1}) != hash_payload({"a": 2})


# ---------------------------------------------------------------------------
# add_intercept_row
# ---------------------------------------------------------------------------


def _make_engine_begin_mock(returned_id: uuid.UUID | None = None) -> MagicMock:
    mock_row = MagicMock()
    mock_row.__getitem__ = MagicMock(return_value=returned_id)

    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_row if returned_id is not None else None

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_ctx
    return mock_engine


class TestAddInterceptRow:
    async def test_returns_none_during_self_egress(self) -> None:
        with patch("sourcerykit.intercept._storage.is_self_egress", return_value=True):
            result = await add_intercept_row(
                url="https://example.com",
                method="GET",
                request_payload={},
                raw={},
                agent_id="agent-1",
                action_name="action-a",
            )
        assert result is None

    async def test_raises_trust_error_when_endpoint_not_trusted(self) -> None:
        with (
            patch("sourcerykit.intercept._storage.is_self_egress", return_value=False),
            patch("sourcerykit.intercept._storage.is_endpoint_trusted", AsyncMock(return_value=False)),
        ):
            with pytest.raises(SourceryKitTrustError, match="endpoint not registered"):
                await add_intercept_row(
                    url="https://untrusted.com",
                    method="GET",
                    request_payload={},
                    raw={},
                    agent_id="agent-1",
                    action_name="action-a",
                )

    async def test_returns_row_id_on_success(self) -> None:
        expected_id = uuid.uuid4()
        engine = _make_engine_begin_mock(returned_id=expected_id)
        with (
            patch("sourcerykit.intercept._storage.is_self_egress", return_value=False),
            patch("sourcerykit.intercept._storage.is_endpoint_trusted", AsyncMock(return_value=True)),
            patch("sourcerykit.intercept._storage.get_engine", return_value=engine),
            patch("sourcerykit.handoff._preprocess.run_preprocess", AsyncMock()),
        ):
            result = await add_intercept_row(
                url="https://trusted.com",
                method="POST",
                request_payload={"q": 1},
                raw={"resp": "ok"},
                agent_id="agent-1",
                action_name="action-a",
            )
        assert result == expected_id

    async def test_raises_value_error_for_long_agent_id(self) -> None:
        with pytest.raises(ValueError, match="agent_id"):
            await add_intercept_row(
                url="https://x.com",
                method="GET",
                request_payload={},
                raw={},
                agent_id="a" * 256,
                action_name="action",
            )

    async def test_raises_value_error_for_long_action_name(self) -> None:
        with pytest.raises(ValueError, match="action_name"):
            await add_intercept_row(
                url="https://x.com",
                method="GET",
                request_payload={},
                raw={},
                agent_id="agent",
                action_name="x" * 256,
            )
