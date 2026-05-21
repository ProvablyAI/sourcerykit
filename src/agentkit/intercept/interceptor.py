"""HTTP intercept: record LLM provider responses into Postgres."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from agentkit.intercept._aiohttp_hook import init_aiohttp_hooks
from agentkit.intercept._httpx_hook import init_httpx_hooks
from agentkit.intercept._storage import add_intercept_row
from agentkit.logger import get_logger

_log = get_logger(__name__)

_ctx_agent_id: ContextVar[str] = ContextVar("provably_agent_id", default="")
_ctx_action_name: ContextVar[str] = ContextVar("provably_action_name", default="")

_last_intercept_row_id: UUID | None = None
_action_row_ids: dict[tuple[str, str], UUID] = {}


@contextmanager
def intercept_context(*, agent_id: str, action_name: str) -> Generator[None, None, None]:
    """Scoped tagging context manager for tracking HTTP traffic."""
    t_agent = _ctx_agent_id.set(agent_id)
    t_action = _ctx_action_name.set(action_name)
    try:
        yield
    finally:
        _ctx_action_name.reset(t_action)
        _ctx_agent_id.reset(t_agent)


def take_last_intercept_row_id() -> UUID | None:
    """Pop the row UUID from the most recent intercept INSERT."""
    global _last_intercept_row_id
    rid = _last_intercept_row_id
    _last_intercept_row_id = None
    return rid


def get_intercept_row_id(agent_id: str, action_name: str) -> UUID | None:
    """Return the tracking database UUID for the last completed tuple."""
    return _action_row_ids.get((agent_id, action_name))


def clear_intercept_row_ids() -> None:
    """Reset the tracking registry map completely at the end of each run."""
    _action_row_ids.clear()


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
    except Exception as e:
        _log.debug(f"SDK logging telemetry safely bypassed: {str(e)}")


def init_interceptor() -> None:
    """Install monkey-patches on httpx.AsyncClient and aiohttp."""
    init_httpx_hooks(_record)
    init_aiohttp_hooks(_record)
