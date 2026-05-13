"""Tests for ``intercept_context`` and the ContextVar-leak it prevents.

The leak: a naked ``ContextVar.set()`` inside an agent loop's tool function persists past
the tool boundary into subsequent LLM calls running in the same ``asyncio.Task``, because
async tasks share their ContextVar cell unless an explicit ``reset(token)`` is paired with
the original ``set``. ``intercept_context`` is the scoped fix.
"""

from __future__ import annotations

import asyncio

import agentkit.intercept.interceptor as interceptor
from agentkit.intercept import intercept_context


def _reset_ctx_for_test_isolation() -> None:
    """Bring the ContextVars back to their declared defaults between tests."""
    interceptor._ctx_agent_id.set("")
    interceptor._ctx_action_name.set("")
    interceptor._ctx_intercept_index.set(0)


def test_intercept_context_sets_values_inside_block() -> None:
    _reset_ctx_for_test_isolation()
    try:
        with intercept_context(agent_id="ag-1", action_name="get_weather", intercept_index=2):
            assert interceptor._ctx_agent_id.get() == "ag-1"
            assert interceptor._ctx_action_name.get() == "get_weather"
            assert interceptor._ctx_intercept_index.get() == 2
    finally:
        _reset_ctx_for_test_isolation()


def test_intercept_context_resets_to_default_on_exit() -> None:
    """When called with no prior values, exit restores the default empty/zero state."""
    _reset_ctx_for_test_isolation()
    try:
        with intercept_context(agent_id="ag-1", action_name="get_weather"):
            pass
        assert interceptor._ctx_agent_id.get() == ""
        assert interceptor._ctx_action_name.get() == ""
        assert interceptor._ctx_intercept_index.get() == 0
    finally:
        _reset_ctx_for_test_isolation()


def test_intercept_context_restores_prior_values_on_exit() -> None:
    """Nesting: exit restores whatever values were set BEFORE the context manager entered."""
    _reset_ctx_for_test_isolation()
    try:
        with intercept_context(agent_id="outer", action_name="outer-action", intercept_index=7):
            with intercept_context(agent_id="inner", action_name="inner-action", intercept_index=99):
                assert interceptor._ctx_action_name.get() == "inner-action"
            assert interceptor._ctx_agent_id.get() == "outer"
            assert interceptor._ctx_action_name.get() == "outer-action"
            assert interceptor._ctx_intercept_index.get() == 7
    finally:
        _reset_ctx_for_test_isolation()


def test_intercept_context_resets_even_on_exception() -> None:
    _reset_ctx_for_test_isolation()
    try:
        try:
            with intercept_context(agent_id="x", action_name="y"):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert interceptor._ctx_agent_id.get() == ""
        assert interceptor._ctx_action_name.get() == ""
    finally:
        _reset_ctx_for_test_isolation()


# ---------------------------------------------------------------------------
# Regression: agent-loop scenario (LLM → tool → LLM in one asyncio.Task).
#
# We simulate three "HTTP calls" by reading the ContextVars (which is exactly what
# ``_insert_row`` does at intercept time). The "tool" body sets the tag using
# ``intercept_context``; the second LLM call must NOT inherit the tool's tag.
# ---------------------------------------------------------------------------


def _read_what_insert_row_would_record() -> tuple[str, str]:
    return (
        interceptor._ctx_agent_id.get() or "unknown",
        interceptor._ctx_action_name.get() or "unknown",
    )


async def _agent_loop_with_naked_set() -> list[tuple[str, str]]:
    """Demonstrates WHY the context manager exists: a fire-and-forget ``ContextVar.set``
    inside the tool persists into the subsequent LLM call in the same Task."""
    rows: list[tuple[str, str]] = []
    rows.append(_read_what_insert_row_would_record())          # LLM turn 1
    # tool body uses naked .set() (the buggy pattern):
    interceptor._ctx_agent_id.set("demo")
    interceptor._ctx_action_name.set("get_weather")
    rows.append(_read_what_insert_row_would_record())          # tool GET
    # tool returns; agent continues with another LLM call in the SAME task:
    rows.append(_read_what_insert_row_would_record())          # LLM turn 2
    return rows


async def _agent_loop_with_intercept_context() -> list[tuple[str, str]]:
    """The fix: scoping with ``intercept_context`` resets the tag on tool exit."""
    rows: list[tuple[str, str]] = []
    rows.append(_read_what_insert_row_would_record())          # LLM turn 1
    with intercept_context(agent_id="demo", action_name="get_weather"):
        rows.append(_read_what_insert_row_would_record())      # tool GET
    rows.append(_read_what_insert_row_would_record())          # LLM turn 2
    return rows


def test_naked_ctx_var_set_leaks_into_subsequent_calls() -> None:
    """Documents WHY ``intercept_context`` must reset on exit. If an agent loop sets a
    ContextVar directly inside a tool, the tag persists into the next LLM call in the
    same asyncio.Task — producing wrong ``claim_urls`` and always-CAUGHT outcomes
    downstream."""
    _reset_ctx_for_test_isolation()
    try:
        rows = asyncio.run(_agent_loop_with_naked_set())
        assert rows[0] == ("unknown", "unknown")               # turn 1
        assert rows[1] == ("demo", "get_weather")              # tool
        assert rows[2] == ("demo", "get_weather"), (           # turn 2 — leaks
            "Naked ContextVar.set should leak into subsequent calls in the same Task. "
            "If this assertion ever starts failing it means asyncio's ContextVar "
            "semantics changed, in which case revisit the rationale for "
            "intercept_context."
        )
    finally:
        _reset_ctx_for_test_isolation()


def test_intercept_context_does_not_leak_into_subsequent_calls() -> None:
    """The fix: turn-2 LLM call goes back to ``"unknown"`` after the tool's ``with`` block."""
    _reset_ctx_for_test_isolation()
    try:
        rows = asyncio.run(_agent_loop_with_intercept_context())
        assert rows[0] == ("unknown", "unknown")           # turn 1
        assert rows[1] == ("demo", "get_weather")          # tool
        assert rows[2] == ("unknown", "unknown")           # turn 2 — fixed
    finally:
        _reset_ctx_for_test_isolation()
