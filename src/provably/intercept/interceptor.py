"""HTTP intercept: record responses; optional simulation tamper (body hook) for allowlisted URLs only."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

import httpx
import requests

from provably.intercept._reentry import already_recording, recording_scope
from provably.intercept._responses import (
    HttpxJsonOverride,
    RequestsJsonOverride,
    extract_raw,
)
from provably.intercept._self_egress import is_self_egress
from provably.intercept._storage import (
    insert_intercept_row,
    request_payload_dict,
)
from provably.trusted_endpoints import normalize_url_for_trust

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
# (agent_id, action_name) -> row_id; lets payload_builder build per-claim WHERE id = N queries
_action_row_ids: dict[tuple[str, str], int] = {}
_intercept_body_hook: Callable[[int, Any], Any] | None = None
# When not ``None``, only these normalized URLs are recorded and passed to the body hook
# (simulation trusted endpoints), not e.g. OpenRouter or internal Provably API traffic.
_url_allowlist: set[str] | None = None


def set_intercept_body_hook(fn: Callable[[int, Any], Any] | None) -> None:
    """``(intercept_index, raw) -> body`` for allowlisted run URLs only; ``None`` clears.

    See :func:`set_intercept_url_allowlist` — internal traffic never invokes this hook.
    """
    global _intercept_body_hook
    _intercept_body_hook = fn


def set_intercept_url_allowlist(urls: list[str] | None) -> None:
    """Scope which URLs are simulation *tamper* targets (``normalize_url_for_trust`` per item).

    The post-index body hook (:func:`set_intercept_body_hook`) runs only for URLs in this set.
    When the allowlist is ``None``, recording may still apply to all outbound traffic (legacy),
    but the tamper hook does not run — so internal calls (e.g. handoff POST to Cluster B) are
    never paused for user edit.

    Pass ``None`` to clear. Pass a list to restrict tamper to the run's dashboard endpoints;
    URLs not in the set are not recorded and pass through unchanged.
    """
    global _url_allowlist
    if urls is None:
        _url_allowlist = None
    else:
        _url_allowlist = {
            normalize_url_for_trust(str(u or "").strip()) for u in urls if (u or "").strip()
        }
        _url_allowlist.discard("")


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


def get_intercept_row_id(agent_id: str, action_name: str) -> int | None:
    """Return the ``provably_intercepts.id`` for the last INSERT with this (agent_id, action_name).

    Used by the handoff payload builder so the SQL proof query can filter on the integer PK
    (``WHERE id = N``) — a single ``=`` predicate that Provably's query engine always accepts,
    avoiding ``AND`` or string-function operators that some engine versions reject.
    """
    with _intercept_lock:
        return _action_row_ids.get((agent_id, action_name))


def clear_intercept_row_ids() -> None:
    """Reset the (agent_id, action_name) → row_id registry; call at end of each run."""
    global _action_row_ids
    with _intercept_lock:
        _action_row_ids = {}


def init_interceptor() -> None:
    """Install the SDK's monkey-patches on :mod:`requests` and :mod:`httpx` (idempotent).

    Replaces ``requests.get``/``requests.post`` and ``httpx.get``/``httpx.post`` with wrapped
    versions that record the response into ``provably_intercepts`` and optionally pass it
    through the simulation hook. Also patches ``httpx.Client.send``, ``httpx.AsyncClient.send``,
    and ``requests.Session.send`` as lower-level choke points so instance-based and async
    usage is also intercepted. The patch is one-way (use :func:`disable` to short-circuit
    rather than uninstall) and flips ``enabled=True``.
    """
    global _initialized, _enabled
    if _initialized:
        return
    _orig["requests_get"] = requests.get
    _orig["requests_post"] = requests.post
    _orig["httpx_get"] = httpx.get
    _orig["httpx_post"] = httpx.post
    _orig["httpx_client_send"] = httpx.Client.send
    _orig["httpx_async_client_send"] = httpx.AsyncClient.send
    _orig["requests_session_send"] = requests.Session.send
    # Module-level convenience patches (kept for backward compatibility)
    requests.get = _wrap_call(_orig["requests_get"], "GET")
    requests.post = _wrap_call(_orig["requests_post"], "POST")
    httpx.get = _wrap_call(_orig["httpx_get"], "GET")
    httpx.post = _wrap_call(_orig["httpx_post"], "POST")
    # Lower-level instance method patches (cover async, Client(), Session())
    requests.Session.send = _wrap_session_send(_orig["requests_session_send"])
    httpx.Client.send = _wrap_client_send(_orig["httpx_client_send"])
    httpx.AsyncClient.send = _wrap_async_client_send(_orig["httpx_async_client_send"])
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
            _action_row_ids[(_ctx_agent_id.get() or "unknown", _ctx_action_name.get() or "unknown")] = row_id


def _maybe_transform_body(raw: Any) -> Any:
    hook = _intercept_body_hook
    if hook is None:
        return raw
    return hook(_ctx_intercept_index.get(), raw)


def _attach(response: Any, url: str, method: str, req_kwargs: dict[str, Any]) -> Any:
    """Record the response and optionally mutate it via the simulation hook.

    Short-circuits immediately when inside a self-egress block or already in the middle of
    recording (re-entry guard prevents double-recording when module-level calls like
    ``httpx.get`` internally delegate to a patched ``Client.send``).
    """
    if is_self_egress() or already_recording():
        return response
    raw = extract_raw(response)
    req = request_payload_dict(url, method, req_kwargs)
    nurl = normalize_url_for_trust(str(url))
    if _url_allowlist is not None and nurl not in _url_allowlist:
        return response
    # Recording: any request that passed the allowlist gate (including legacy mode when
    # allowlist is None — all outbound traffic).
    if _enabled:
        _insert_row(url, req, raw, method=method)
    # Simulation tamper hook: only for explicit run endpoints, never for OpenRouter,
    # Provably API, cluster handoff posts, etc. (those run with allowlist cleared or off-list).
    tamper = _url_allowlist is not None and nurl in _url_allowlist
    mutated = _maybe_transform_body(raw) if tamper else raw
    if mutated is raw:
        return response
    if isinstance(response, requests.Response):
        return _RequestsJsonOverride(response, mutated)
    if isinstance(response, httpx.Response):
        return _HttpxJsonOverride(response, mutated)
    return response


def _wrap_call(orig_fn, method: str):
    """Wrap a module-level convenience function (e.g. httpx.get, requests.post).

    Sets ``recording_scope`` BEFORE calling the original function so that any
    lower-level ``Client.send`` / ``Session.send`` wrapper that fires during the
    same call sees ``already_recording() == True`` and skips duplicate recording.
    After the original returns, ``_attach`` runs in the outer scope (where
    ``already_recording()`` is now False again) to do the actual recording.
    """

    def wrapped(url, *args, **kwargs):
        with recording_scope():
            response = orig_fn(url, *args, **kwargs)
        # recording_scope has exited; _attach will record this call
        return _attach(response, str(url), method, dict(kwargs))

    return wrapped


def _httpx_request_to_kwargs(req: httpx.Request) -> dict[str, Any]:
    """Extract request metadata from an httpx.Request into the kwargs shape request_payload_dict understands."""
    kwargs: dict[str, Any] = {}
    # Query params
    params = dict(req.url.params)
    if params:
        kwargs["params"] = params
    # Body: try to parse as JSON if Content-Type is application/json
    content_type = req.headers.get("content-type", "")
    if req.content and "application/json" in content_type:
        try:
            kwargs["json"] = json.loads(req.content)
        except Exception:  # noqa: BLE001
            kwargs["content"] = req.content.decode(errors="replace")
    elif req.content:
        kwargs["data"] = req.content.decode(errors="replace")
    return kwargs


def _requests_prepared_to_kwargs(req: requests.PreparedRequest) -> dict[str, Any]:
    """Extract request metadata from a requests.PreparedRequest into the kwargs shape request_payload_dict understands."""
    from urllib.parse import parse_qs, urlsplit

    kwargs: dict[str, Any] = {}
    # Query params from URL
    url_str = str(req.url or "")
    parsed = urlsplit(url_str)
    if parsed.query:
        raw_params = parse_qs(parsed.query, keep_blank_values=True)
        # Flatten single-value lists to scalars (matches typical kwargs["params"] shape)
        kwargs["params"] = {k: (v[0] if len(v) == 1 else v) for k, v in raw_params.items()}
    # Body
    content_type = (req.headers or {}).get("Content-Type", "") or ""
    body = req.body
    if body is not None:
        if "application/json" in content_type:
            try:
                body_str = body if isinstance(body, str) else body.decode(errors="replace")
                kwargs["json"] = json.loads(body_str)
            except Exception:  # noqa: BLE001
                kwargs["data"] = body if isinstance(body, str) else body.decode(errors="replace")
        else:
            kwargs["data"] = body if isinstance(body, str) else body.decode(errors="replace")
    return kwargs


def _wrap_client_send(orig_send):
    """Wrap httpx.Client.send to record responses via _attach."""

    def wrapped(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        response = orig_send(self, request, **kwargs)
        return _attach(response, str(request.url), request.method, _httpx_request_to_kwargs(request))

    return wrapped


def _wrap_async_client_send(orig_send):
    """Wrap httpx.AsyncClient.send to record responses via _attach."""

    async def wrapped(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        response = await orig_send(self, request, **kwargs)
        return _attach(response, str(request.url), request.method, _httpx_request_to_kwargs(request))

    return wrapped


def _wrap_session_send(orig_send):
    """Wrap requests.Session.send to record responses via _attach."""

    def wrapped(self, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        response = orig_send(self, request, **kwargs)
        return _attach(response, str(request.url), request.method or "GET", _requests_prepared_to_kwargs(request))

    return wrapped
