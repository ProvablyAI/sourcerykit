"""HTTP intercept: record LLM provider responses into Postgres."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from sourcerykit.intercept._aiohttp_hook import init_aiohttp_hooks
from sourcerykit.intercept._httpx_hook import init_httpx_hooks
from sourcerykit.intercept._storage import add_intercept_row
from sourcerykit.intercept.requests_hook import init_requests_hooks
from sourcerykit.logger import get_logger
from sourcerykit.utils.validation import validate_length

_log = get_logger(__name__)

_ctx_agent_id: ContextVar[str] = ContextVar("provably_agent_id", default="")
_ctx_action_name: ContextVar[str] = ContextVar("provably_action_name", default="")

_last_intercept_row_id: UUID | None = None
_action_row_ids: dict[tuple[str, str], UUID] = {}


@asynccontextmanager
async def async_intercept_context(*, agent_id: str, action_name: str) -> AsyncGenerator[None, None]:
    """Scoped tagging context manager for tracking HTTP traffic (async)."""
    # Validate user-provided identifiers before setting context
    validate_length("agent_id", agent_id, max_len=255)
    validate_length("action_name", action_name, max_len=255)

    _log.debug("intercept_context_entered", agent_id=agent_id, action_name=action_name)
    t_agent = _ctx_agent_id.set(agent_id)
    t_action = _ctx_action_name.set(action_name)
    try:
        yield
    finally:
        _ctx_action_name.reset(t_action)
        _ctx_agent_id.reset(t_agent)
        _log.debug("intercept_context_exited", agent_id=agent_id, action_name=action_name)


def take_last_intercept_row_id() -> UUID | None:
    """Pop the row UUID from the most recent intercept INSERT."""
    global _last_intercept_row_id
    rid = _last_intercept_row_id
    _last_intercept_row_id = None
    return rid


def get_intercept_row_id(agent_id: str, action_name: str) -> UUID | None:
    """Return the tracking database UUID for the last completed tuple."""
    return _action_row_ids.get((agent_id, action_name))


async def _record(url: str, method: str, request_payload: dict[str, Any], raw: dict[str, Any]) -> None:
    """Persist an intercepted request/response pair and cache the returned row id."""
    agent_id = _ctx_agent_id.get()
    action_name = _ctx_action_name.get()
    if not agent_id or not action_name:
        return

    try:
        row_id = await add_intercept_row(
            url=url,
            method=method,
            request_payload=request_payload,
            raw=raw,
            agent_id=agent_id,
            action_name=action_name,
        )
        if row_id is not None:
            _action_row_ids[(agent_id, action_name)] = row_id
            global _last_intercept_row_id
            _last_intercept_row_id = row_id
    except Exception:
        _log.exception("intercept_record_failed", agent_id=agent_id, action_name=action_name)


def init_interceptor() -> None:
    """Install monkey-patches on httpx.AsyncClient, aiohttp and requests."""
    init_httpx_hooks(_record)
    init_aiohttp_hooks(_record)
    init_requests_hooks(_record)
    _log.info("intercept_hooks_installed")
