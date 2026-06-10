"""Tests for agentkit.intercept.interceptor — _record and hook integration."""

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

import agentkit.intercept.interceptor as interceptor_mod
from agentkit.intercept.interceptor import (
    _record,
    async_intercept_context,
)


@pytest.fixture(autouse=True)
def _reset_globals() -> None:
    interceptor_mod._last_intercept_row_id = None
    interceptor_mod._action_row_ids.clear()


class TestRecord:
    async def test_does_nothing_when_no_context_set(self) -> None:
        """_record is a no-op when agent_id / action_name are not in context."""
        with patch("agentkit.intercept.interceptor.add_intercept_row", AsyncMock()) as mock_add:
            await _record("https://example.com", "POST", {}, {})
            mock_add.assert_not_called()

    async def test_stores_row_id_when_context_active(self) -> None:
        expected_id = uuid.uuid4()
        with patch("agentkit.intercept.interceptor.add_intercept_row", AsyncMock(return_value=expected_id)):
            async with async_intercept_context(agent_id="agent-1", action_name="act-1"):
                await _record("https://example.com", "GET", {"q": 1}, {"data": "resp"})

        assert interceptor_mod._last_intercept_row_id == expected_id
        assert interceptor_mod._action_row_ids.get(("agent-1", "act-1")) == expected_id

    async def test_does_not_raise_when_add_intercept_row_fails(self) -> None:
        """Storage errors must be swallowed — never propagated to caller."""
        with patch(
            "agentkit.intercept.interceptor.add_intercept_row",
            AsyncMock(side_effect=RuntimeError("db down")),
        ):
            async with async_intercept_context(agent_id="agent-1", action_name="act-1"):
                await _record("https://example.com", "GET", {}, {})
            # If we get here, the error was swallowed correctly

    async def test_row_id_is_none_when_add_returns_none(self) -> None:
        with patch("agentkit.intercept.interceptor.add_intercept_row", AsyncMock(return_value=None)):
            async with async_intercept_context(agent_id="agent-1", action_name="act-1"):
                await _record("https://example.com", "GET", {}, {})
        # last_intercept_row_id should still be None if row_id was None
        assert interceptor_mod._last_intercept_row_id is None

    async def test_multiple_records_update_action_row_ids(self) -> None:
        ids = [uuid.uuid4(), uuid.uuid4()]
        call_count = 0

        async def fake_add(**kwargs: Any) -> uuid.UUID:
            nonlocal call_count
            result = ids[call_count]
            call_count += 1
            return result

        with patch("agentkit.intercept.interceptor.add_intercept_row", fake_add):
            async with async_intercept_context(agent_id="agent-1", action_name="act-1"):
                await _record("https://a.com", "GET", {}, {})
                await _record("https://b.com", "GET", {}, {})

        # Last ID wins for the (agent_id, action_name) pair
        assert interceptor_mod._action_row_ids.get(("agent-1", "act-1")) == ids[1]
        assert interceptor_mod._last_intercept_row_id == ids[1]
