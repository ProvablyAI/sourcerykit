"""Tests for sourcerykit.intercept.interceptor — async_intercept_context and related helpers."""

import uuid
from unittest.mock import patch

import pytest

from sourcerykit.intercept.interceptor import (
    _ctx_action_name,
    _ctx_agent_id,
    _ctx_call_ref,
    async_intercept_context,
)


@pytest.fixture(autouse=True)
def _reset_globals() -> None:
    """Reset global state in the interceptor module between tests."""
    pass


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
                await asyncio.sleep(0)
                results["a"] = _ctx_agent_id.get()

        async def task_b() -> None:
            async with async_intercept_context(agent_id="agent-b", action_name="act-b"):
                await asyncio.sleep(0)
                results["b"] = _ctx_agent_id.get()

        await asyncio.gather(task_a(), task_b())
        assert results["a"] == "agent-a"
        assert results["b"] == "agent-b"


# ---------------------------------------------------------------------------
# call_ref (UUID string yielded by async_intercept_context)
# ---------------------------------------------------------------------------


class TestCallRef:
    async def test_yields_uuid_string(self) -> None:
        async with async_intercept_context(agent_id="a", action_name="b") as ref:
            assert isinstance(ref, str)
            uuid.UUID(ref)  # must be valid UUID

    async def test_call_ref_unique_per_invocation(self) -> None:
        refs: list[str] = []
        async with async_intercept_context(agent_id="a", action_name="b") as ref1:
            refs.append(ref1)
        async with async_intercept_context(agent_id="a", action_name="b") as ref2:
            refs.append(ref2)
        assert refs[0] != refs[1]

    async def test_call_ref_contextvar_set_inside_block(self) -> None:
        async with async_intercept_context(agent_id="a", action_name="b") as ref:
            assert str(_ctx_call_ref.get()) == ref

    async def test_call_ref_contextvar_resets_after_exit(self) -> None:
        async with async_intercept_context(agent_id="a", action_name="b"):
            pass
        assert _ctx_call_ref.get() is None

    async def test_call_ref_isolation_across_concurrent_tasks(self) -> None:
        import asyncio

        refs: dict[str, str] = {}

        async def task_a() -> None:
            async with async_intercept_context(agent_id="a", action_name="act") as ref:
                await asyncio.sleep(0)
                refs["a"] = ref

        async def task_b() -> None:
            async with async_intercept_context(agent_id="b", action_name="act") as ref:
                await asyncio.sleep(0)
                refs["b"] = ref

        await asyncio.gather(task_a(), task_b())
        assert refs["a"] != refs["b"]


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
