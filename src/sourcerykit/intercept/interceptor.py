"""HTTP intercept: record LLM provider responses into Postgres."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any
from uuid import UUID, uuid4

from sourcerykit.intercept._aiohttp_hook import init_aiohttp_hooks
from sourcerykit.intercept._httpx_hook import init_httpx_hooks
from sourcerykit.intercept._storage import add_intercept_row
from sourcerykit.intercept.requests_hook import init_requests_hooks
from sourcerykit.logger import get_logger
from sourcerykit.utils.validation import validate_length

_log = get_logger(__name__)

_ctx_agent_id: ContextVar[str] = ContextVar("provably_agent_id", default="")
_ctx_action_name: ContextVar[str] = ContextVar("provably_action_name", default="")
_ctx_call_ref: ContextVar[UUID | None] = ContextVar("provably_call_ref", default=None)


@asynccontextmanager
async def async_intercept_context(*, agent_id: str, action_name: str) -> AsyncGenerator[str, None]:
    """Scoped tagging context manager for tracking HTTP traffic (async).

    Yields a unique ``call_ref`` (UUID) that identifies this specific
    intercept invocation.  The caller should include it in the claim so that
    ``build_handoff_payload`` can map the claim to the correct intercept row.
    """
    validate_length("agent_id", agent_id, max_len=255)
    validate_length("action_name", action_name, max_len=255)

    call_ref = uuid4()

    _log.debug("intercept_context_entered", agent_id=agent_id, action_name=action_name, call_ref=str(call_ref))
    t_agent = _ctx_agent_id.set(agent_id)
    t_action = _ctx_action_name.set(action_name)
    t_ref = _ctx_call_ref.set(call_ref)
    try:
        yield str(call_ref)
    finally:
        _ctx_call_ref.reset(t_ref)
        _ctx_action_name.reset(t_action)
        _ctx_agent_id.reset(t_agent)
        _log.debug("intercept_context_exited", agent_id=agent_id, action_name=action_name, call_ref=str(call_ref))


async def _record(url: str, method: str, request_payload: dict[str, Any], raw: dict[str, Any]) -> None:
    """Persist an intercepted request/response pair and cache the returned row id."""
    agent_id = _ctx_agent_id.get()
    action_name = _ctx_action_name.get()
    if not agent_id or not action_name:
        return

    call_ref = _ctx_call_ref.get()

    try:
        await add_intercept_row(
            url=url,
            method=method,
            request_payload=request_payload,
            raw=raw,
            agent_id=agent_id,
            action_name=action_name,
            call_ref=call_ref,
        )
    except Exception:
        _log.exception("intercept_record_failed", agent_id=agent_id, action_name=action_name)


def init_interceptor() -> None:
    """Install monkey-patches on httpx.AsyncClient, aiohttp and requests."""
    init_httpx_hooks(_record)
    init_aiohttp_hooks(_record)
    init_requests_hooks(_record)
    _log.info("intercept_hooks_installed")
