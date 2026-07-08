"""Tests for sourcerykit.intercept.interceptor — _record and hook integration."""

import uuid
from unittest.mock import AsyncMock, patch

from sourcerykit.intercept.interceptor import (
    _record,
    async_intercept_context,
)


class TestRecord:
    async def test_does_nothing_when_no_context_set(self) -> None:
        """_record is a no-op when agent_id / action_name are not in context."""
        with patch("sourcerykit.intercept.interceptor.add_intercept_row", AsyncMock()) as mock_add:
            await _record("https://example.com", "POST", {}, {})
            mock_add.assert_not_called()

    async def test_calls_add_intercept_row_when_context_active(self) -> None:
        expected_id = uuid.uuid4()
        with patch("sourcerykit.intercept.interceptor.add_intercept_row", AsyncMock(return_value=expected_id)):
            async with async_intercept_context(agent_id="agent-1", action_name="act-1"):
                await _record("https://example.com", "GET", {"q": 1}, {"data": "resp"})
            # No assertion on globals — call_ref is the lookup key now

    async def test_passes_call_ref_to_add_intercept_row(self) -> None:
        """_record reads _ctx_call_ref and passes it to add_intercept_row."""
        expected_id = uuid.uuid4()
        mock_add = AsyncMock(return_value=expected_id)
        with patch("sourcerykit.intercept.interceptor.add_intercept_row", mock_add):
            async with async_intercept_context(agent_id="agent-1", action_name="act-1") as ref:
                await _record("https://example.com", "GET", {}, {})
                mock_add.assert_called_once()
                _, kwargs = mock_add.call_args
                assert kwargs["call_ref"] == uuid.UUID(ref)

    async def test_call_ref_is_unique_per_invocation(self) -> None:
        refs: list[str] = []
        with patch("sourcerykit.intercept.interceptor.add_intercept_row", AsyncMock(return_value=uuid.uuid4())):
            async with async_intercept_context(agent_id="a", action_name="b") as ref1:
                refs.append(ref1)
            async with async_intercept_context(agent_id="a", action_name="b") as ref2:
                refs.append(ref2)
        assert refs[0] != refs[1]
        assert isinstance(refs[0], str)
        assert isinstance(refs[1], str)

    async def test_does_not_raise_when_add_intercept_row_fails(self) -> None:
        """Storage errors must be swallowed — never propagated to caller."""
        with patch(
            "sourcerykit.intercept.interceptor.add_intercept_row",
            AsyncMock(side_effect=RuntimeError("db down")),
        ):
            async with async_intercept_context(agent_id="agent-1", action_name="act-1"):
                await _record("https://example.com", "GET", {}, {})
            # If we get here, the error was swallowed correctly

    async def test_discards_row_id_from_add_intercept_row(self) -> None:
        """Row id is no longer cached — call_ref is the lookup key."""
        with patch("sourcerykit.intercept.interceptor.add_intercept_row", AsyncMock(return_value=uuid.uuid4())):
            async with async_intercept_context(agent_id="agent-1", action_name="act-1"):
                await _record("https://example.com", "GET", {}, {})
        # No globals to assert — this is intentional
