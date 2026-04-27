"""HTTP intercept: record responses; optional post-index body transform via :func:`set_intercept_body_hook`."""

from __future__ import annotations

import threading
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

import httpx
import requests

from provably.intercept._responses import (
    HttpxJsonOverride,
    RequestsJsonOverride,
    extract_raw,
)
from provably.intercept._storage import (
    insert_intercept_row,
    request_payload_dict,
)

_RequestsJsonOverride = RequestsJsonOverride
_HttpxJsonOverride = HttpxJsonOverride

_ctx_agent_id: ContextVar[str] = ContextVar("provably_agent_id", default="")
_ctx_action_name: ContextVar[str] = ContextVar("provably_action_name", default="")
_ctx_intercept_index: ContextVar[int] = ContextVar("provably_intercept_index", default=0)

_enabled = False
_initialized = False
_orig: dict[str, Any] = {}
_intercept_lock = threading.Lock()
_last_intercept_row_id: int | None = None
_intercept_body_hook: Callable[[int, Any], Any] | None = None


def set_intercept_body_hook(fn: Callable[[int, Any], Any] | None) -> None:
    """``(intercept_index, raw) -> body`` after insert, before the client sees the response; ``None`` clears."""
    global _intercept_body_hook
    _intercept_body_hook = fn


def set_interceptor_context(*, agent_id: str, action_name: str, intercept_index: int = 0) -> None:
    """Bind per-call context that subsequent intercepts will tag onto their inserted rows.

    Uses :class:`contextvars.ContextVar` so concurrent tasks/threads each see their own values.
    Call this immediately before invoking the agent action whose HTTP traffic should be tagged.

    Args:
        agent_id: Logical agent identifier; recorded in ``provably_intercepts.agent_id``.
        action_name: Action name; recorded in ``provably_intercepts.action_name``.
        intercept_index: Per-action sequence number used by the simulation hook to address a
            specific intercept (e.g. "mutate the second response of action X"). Default ``0``.
    """
    _ctx_agent_id.set(agent_id)
    _ctx_action_name.set(action_name)
    _ctx_intercept_index.set(intercept_index)


def take_last_intercept_row_id() -> int | None:
    """Pop the row id from the most recent ``provably_intercepts`` INSERT (single-shot, thread-safe)."""
    global _last_intercept_row_id
    with _intercept_lock:
        rid = _last_intercept_row_id
        _last_intercept_row_id = None
        return rid


def init_interceptor() -> None:
    """Install the SDK's monkey-patches on :mod:`requests` and :mod:`httpx` (idempotent).

    Replaces ``requests.get``/``requests.post`` and ``httpx.get``/``httpx.post`` with wrapped
    versions that record the response into ``provably_intercepts`` and optionally pass it
    through the simulation hook. The patch is one-way (use :func:`disable` to short-circuit
    rather than uninstall) and flips ``enabled=True``.
    """
    global _initialized, _enabled
    if _initialized:
        return
    _orig["requests_get"] = requests.get
    _orig["requests_post"] = requests.post
    _orig["httpx_get"] = httpx.get
    _orig["httpx_post"] = httpx.post
    requests.get = _wrap_call(_orig["requests_get"], "GET")
    requests.post = _wrap_call(_orig["requests_post"], "POST")
    httpx.get = _wrap_call(_orig["httpx_get"], "GET")
    httpx.post = _wrap_call(_orig["httpx_post"], "POST")
    _initialized = True
    _enabled = True


def enable() -> None:
    """Turn intercept recording on, calling :func:`init_interceptor` first on cold start."""
    global _enabled
    if not _initialized:
        init_interceptor()
    _enabled = True


def disable() -> None:
    """Stop recording intercepts; patches stay installed but become a passthrough."""
    global _enabled
    _enabled = False


def is_enabled() -> bool:
    """Return whether intercept recording is currently on."""
    return _enabled


def _insert_row(url: str, request_payload: dict[str, Any], raw: Any, *, method: str = "GET") -> None:
    if not _enabled:
        return
    row_id = insert_intercept_row(
        url=url,
        method=method,
        request_payload=request_payload,
        raw=raw,
        agent_id=_ctx_agent_id.get() or "unknown",
        action_name=_ctx_action_name.get() or "unknown",
    )
    if row_id is not None:
        global _last_intercept_row_id
        with _intercept_lock:
            _last_intercept_row_id = row_id


def _maybe_transform_body(raw: Any) -> Any:
    hook = _intercept_body_hook
    if hook is None:
        return raw
    return hook(_ctx_intercept_index.get(), raw)


def _attach(response: Any, url: str, method: str, req_kwargs: dict[str, Any]) -> Any:
    raw = extract_raw(response)
    req = request_payload_dict(url, method, req_kwargs)
    if _enabled:
        _insert_row(url, req, raw, method=method)
    mutated = _maybe_transform_body(raw)
    if mutated is raw:
        return response
    if isinstance(response, requests.Response):
        return _RequestsJsonOverride(response, mutated)
    if isinstance(response, httpx.Response):
        return _HttpxJsonOverride(response, mutated)
    return response


def _wrap_call(orig_fn, method: str):
    def wrapped(url, *args, **kwargs):
        response = orig_fn(url, *args, **kwargs)
        return _attach(response, str(url), method, dict(kwargs))

    return wrapped
