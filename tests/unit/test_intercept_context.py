"""Tests for sourcerykit.intercept.interceptor — async_intercept_context and related helpers."""

import uuid
from unittest.mock import patch

import pytest

import sourcerykit.intercept.interceptor as interceptor_mod
from sourcerykit.intercept.interceptor import (
    _ctx_action_name,
    _ctx_agent_id,
    async_intercept_context,
    get_intercept_row_id,
    take_last_intercept_row_id,
)


@pytest.fixture(autouse=True)
def _reset_globals() -> None:
    """Reset global state in the interceptor module between tests."""
    interceptor_mod._last_intercept_row_id = None
    interceptor_mod._action_row_ids.clear()


class TestAsyncInterceptContext:
    async def test_sets_context_vars_within_block(self) -> None:
        async with async_intercept_context(agent_id="agent-1", action_name="action-a"):
            assert _ctx_agent_id.get() == "agent-1"
            assert _ctx_action_name.get() == "action-a"

    async def test_resets_context_vars_after_block(self) -> None:
        async with async_intercept_context(agent_id="agent-1", action_name="action-a"):
            pass
        assert _ctx_agent_id.get() == ""
        assert _ctx_action_name.get() == ""

    async def test_resets_to_outer_values_when_nested(self) -> None:
        async with async_intercept_context(agent_id="outer", action_name="outer-action"):
            async with async_intercept_context(agent_id="inner", action_name="inner-action"):
                assert _ctx_agent_id.get() == "inner"
            # Restored to outer after inner exits
            assert _ctx_agent_id.get() == "outer"

    async def test_resets_even_if_exception_raised(self) -> None:
        with pytest.raises(ValueError):
            async with async_intercept_context(agent_id="agent-1", action_name="action-a"):
                raise ValueError("boom")
        assert _ctx_agent_id.get() == ""
        assert _ctx_action_name.get() == ""

    async def test_raises_value_error_for_empty_agent_id(self) -> None:
        with pytest.raises(ValueError):
            async with async_intercept_context(agent_id="", action_name="action-a"):
                pass

    async def test_raises_value_error_for_long_action_name(self) -> None:
        with pytest.raises(ValueError):
            async with async_intercept_context(agent_id="a", action_name="x" * 256):
                pass

    async def test_context_isolation_across_concurrent_tasks(self) -> None:
        """ContextVars must be isolated per task — no cross-task leakage."""
        import asyncio

        results: dict[str, str] = {}

        async def task_a() -> None:
            async with async_intercept_context(agent_id="agent-a", action_name="act-a"):
                await asyncio.sleep(0)  # yield to allow task_b to run
                results["a"] = _ctx_agent_id.get()

        async def task_b() -> None:
            async with async_intercept_context(agent_id="agent-b", action_name="act-b"):
                await asyncio.sleep(0)
                results["b"] = _ctx_agent_id.get()

        await asyncio.gather(task_a(), task_b())
        assert results["a"] == "agent-a"
        assert results["b"] == "agent-b"


# ---------------------------------------------------------------------------
# take_last_intercept_row_id
# ---------------------------------------------------------------------------


class TestTakeLastInterceptRowId:
    def test_returns_none_when_no_row_recorded(self) -> None:
        assert take_last_intercept_row_id() is None

    def test_returns_row_id_and_clears_it(self) -> None:
        rid = uuid.uuid4()
        interceptor_mod._last_intercept_row_id = rid
        result = take_last_intercept_row_id()
        assert result == rid
        # Must be cleared after take
        assert interceptor_mod._last_intercept_row_id is None

    def test_second_call_returns_none(self) -> None:
        interceptor_mod._last_intercept_row_id = uuid.uuid4()
        take_last_intercept_row_id()
        assert take_last_intercept_row_id() is None


# ---------------------------------------------------------------------------
# get_intercept_row_id
# ---------------------------------------------------------------------------


class TestGetInterceptRowId:
    def test_returns_none_for_unknown_pair(self) -> None:
        assert get_intercept_row_id("agent", "action") is None

    def test_returns_stored_row_id(self) -> None:
        rid = uuid.uuid4()
        interceptor_mod._action_row_ids[("agent-1", "act-1")] = rid
        assert get_intercept_row_id("agent-1", "act-1") == rid

    def test_does_not_clear_entry(self) -> None:
        rid = uuid.uuid4()
        interceptor_mod._action_row_ids[("agent-1", "act-1")] = rid
        get_intercept_row_id("agent-1", "act-1")
        assert get_intercept_row_id("agent-1", "act-1") == rid


# ---------------------------------------------------------------------------
# init_interceptor
# ---------------------------------------------------------------------------


class TestInitInterceptor:
    def test_installs_hooks_without_error(self) -> None:
        with (
            patch("sourcerykit.intercept.interceptor.init_httpx_hooks") as mock_httpx,
            patch("sourcerykit.intercept.interceptor.init_aiohttp_hooks") as mock_aiohttp,
            patch("sourcerykit.intercept.interceptor.init_requests_hooks") as mock_requests,
        ):
            from sourcerykit.intercept.interceptor import init_interceptor

            init_interceptor()
            mock_httpx.assert_called_once()
            mock_aiohttp.assert_called_once()
            mock_requests.assert_called_once()
