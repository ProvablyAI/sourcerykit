"""Tests for ``intercept_context`` and the ContextVar-leak it fixes.

The leak: ``set_interceptor_context`` writes to a ContextVar with no reset. Inside an
agent loop the tool function and the subsequent LLM call run in the same asyncio.Task,
so the tag set inside the tool keeps applying to LLM calls fired after the tool
returns. ``intercept_context`` is the scoped fix.
"""

from __future__ import annotations

import asyncio

import provably.intercept.interceptor as interceptor
from provably.intercept import intercept_context, set_interceptor_context


def _reset_ctx() -> None:
    """Bring ContextVars back to defaults for test isolation (no SDK API for this — by design)."""
    set_interceptor_context(agent_id="", action_name="", intercept_index=0)


def test_intercept_context_sets_values_inside_block() -> None:
    _reset_ctx()
    try:
        with intercept_context(agent_id="ag-1", action_name="get_weather", intercept_index=2):
            assert interceptor._ctx_agent_id.get() == "ag-1"
            assert interceptor._ctx_action_name.get() == "get_weather"
            assert interceptor._ctx_intercept_index.get() == 2
    finally:
        _reset_ctx()


def test_intercept_context_resets_to_default_on_exit() -> None:
    """When called with no prior values, exit restores the default empty/zero state."""
    _reset_ctx()
    try:
        with intercept_context(agent_id="ag-1", action_name="get_weather"):
            pass
        assert interceptor._ctx_agent_id.get() == ""
        assert interceptor._ctx_action_name.get() == ""
        assert interceptor._ctx_intercept_index.get() == 0
    finally:
        _reset_ctx()


def test_intercept_context_restores_prior_values_on_exit() -> None:
    """Nesting: exit restores whatever values were set BEFORE the context manager entered."""
    _reset_ctx()
    try:
        set_interceptor_context(agent_id="outer-ag", action_name="outer-action", intercept_index=7)
        with intercept_context(agent_id="inner-ag", action_name="inner-action", intercept_index=99):
            assert interceptor._ctx_action_name.get() == "inner-action"
        assert interceptor._ctx_agent_id.get() == "outer-ag"
        assert interceptor._ctx_action_name.get() == "outer-action"
        assert interceptor._ctx_intercept_index.get() == 7
    finally:
        _reset_ctx()


def test_intercept_context_resets_even_on_exception() -> None:
    _reset_ctx()
    try:
        try:
            with intercept_context(agent_id="x", action_name="y"):
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert interceptor._ctx_agent_id.get() == ""
        assert interceptor._ctx_action_name.get() == ""
    finally:
        _reset_ctx()


# ---------------------------------------------------------------------------
# Regression: agent-loop scenario (LLM → tool → LLM in one asyncio.Task).
#
# We make three "HTTP calls" — a fake LLM POST, a tool GET that tags itself as
# ``get_weather``, then a second LLM POST. We capture what tag each "call" sees by
# reading the ContextVar (which is exactly what _insert_row does).
# ---------------------------------------------------------------------------


def _record_what_insert_row_would_see() -> tuple[str, str]:
    """Mirror of interceptor._insert_row's tag-reading logic."""
    return (
        interceptor._ctx_agent_id.get() or "unknown",
        interceptor._ctx_action_name.get() or "unknown",
    )


async def _agent_loop_with_set_interceptor_context() -> list[tuple[str, str]]:
    """Reproduces the bug: tool calls set_interceptor_context fire-and-forget."""
    rows: list[tuple[str, str]] = []
    rows.append(_record_what_insert_row_would_see())          # LLM turn 1
    # tool body:
    set_interceptor_context(agent_id="demo", action_name="get_weather")
    rows.append(_record_what_insert_row_would_see())          # tool GET — tagged correctly
    # tool returns; agent continues with another LLM call in the SAME task:
    rows.append(_record_what_insert_row_would_see())          # LLM turn 2
    return rows


async def _agent_loop_with_intercept_context() -> list[tuple[str, str]]:
    """Same scenario, but the tool uses the scoped intercept_context manager."""
    rows: list[tuple[str, str]] = []
    rows.append(_record_what_insert_row_would_see())          # LLM turn 1
    # tool body:
    with intercept_context(agent_id="demo", action_name="get_weather"):
        rows.append(_record_what_insert_row_would_see())      # tool GET — tagged correctly
    # tool returns; tag is reset:
    rows.append(_record_what_insert_row_would_see())          # LLM turn 2
    return rows


def test_set_interceptor_context_leaks_into_subsequent_calls() -> None:
    """Documents the bug — turn-2 LLM call inherits the tool's action_name.

    This is the failure mode that produces wrong ``claim_urls`` (LLM URL instead of the
    data-API URL) in handoff payloads built by ``payload_builder``, and the always-CAUGHT
    outcome in ``evaluate_handoff`` (because the wrong intercept row gets indexed)."""
    _reset_ctx()
    try:
        rows = asyncio.run(_agent_loop_with_set_interceptor_context())
        # turn 1: untagged
        assert rows[0] == ("unknown", "unknown")
        # tool: tagged
        assert rows[1] == ("demo", "get_weather")
        # turn 2: STILL tagged → this is the leak that produces wrong claim_urls / always-CAUGHT
        assert rows[2] == ("demo", "get_weather"), (
            "Expected leak to persist with set_interceptor_context — if this assertion "
            "starts failing it means set_interceptor_context now scopes itself, in which "
            "case the deprecation note in its docstring should be removed."
        )
    finally:
        _reset_ctx()


def test_intercept_context_does_not_leak_into_subsequent_calls() -> None:
    """The fix: turn-2 LLM call goes back to ``"unknown"`` after the tool's ``with`` block."""
    _reset_ctx()
    try:
        rows = asyncio.run(_agent_loop_with_intercept_context())
        assert rows[0] == ("unknown", "unknown")           # turn 1
        assert rows[1] == ("demo", "get_weather")          # tool
        assert rows[2] == ("unknown", "unknown")           # turn 2 — fixed
    finally:
        _reset_ctx()
