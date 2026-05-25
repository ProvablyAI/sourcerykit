"""HTTP intercept: record responses; optional simulation tamper (body hook) for allowlisted URLs only."""

from __future__ import annotations

import json
import threading
from collections.abc import Awaitable, Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

import httpx
import requests

try:
    import aiohttp as _aiohttp
except ImportError:
    _aiohttp = None  # type: ignore[assignment]

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
from provably.trusted_endpoints import _matches_registered, normalize_url_for_trust

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

    Entries support the same FastAPI/Express-style placeholders as the trusted-endpoint
    registry: ``{name}`` matches one path segment, ``{name:path}`` matches any subtree.
    A registered ``https://api.example.com/customers/{id}`` matches the concrete URL
    ``https://api.example.com/customers/42``. Plain URLs without ``{`` keep exact-match
    semantics.
    """
    global _url_allowlist
    if urls is None:
        _url_allowlist = None
    else:
        _url_allowlist = {normalize_url_for_trust(str(u or "").strip()) for u in urls if (u or "").strip()}
        _url_allowlist.discard("")


def _url_in_allowlist(nurl: str) -> bool:
    """Membership test for ``_url_allowlist`` that honors pattern entries.

    Exact match is checked first (O(1)). Only on a miss do we iterate over pattern entries
    (those containing ``{``) — plain-URL allowlists pay no per-request iteration cost.
    Caller must have already confirmed ``_url_allowlist is not None``.
    """
    assert _url_allowlist is not None
    if nurl in _url_allowlist:
        return True
    for entry in _url_allowlist:
        if "{" in entry and _matches_registered(nurl, entry):
            return True
    return False


@contextmanager
def intercept_context(*, agent_id: str, action_name: str, intercept_index: int = 0) -> Generator[None, None, None]:
    """Scoped tagging for HTTP traffic emitted inside the ``with`` block.

    Sets the underlying :class:`contextvars.ContextVar` values on enter and resets them
    on exit, so the tag does not leak into surrounding LLM calls running in the same
    :class:`asyncio.Task`.

    .. important::
       **Must be used as a ``with`` statement.** A bare call like
       ``intercept_context(agent_id="demo", action_name="get_weather")`` is a no-op
       (returns a context-manager object that is immediately discarded; the body never
       runs and no ContextVar is set). Subsequent intercepts will be tagged
       ``("unknown", "unknown")``.

    Use this for any HTTP emitted from inside an agent framework's tool function::

        @function_tool
        def get_temperature():
            with intercept_context(agent_id="demo", action_name="get_weather"):
                return requests.get(...).json()

    Nesting is supported: prior values are restored on exit, not cleared.

    Args:
        agent_id: Logical agent identifier; recorded in ``provably_intercepts.agent_id``.
            **Must match** the ``intercept_agent_id`` you later pass to
            :func:`provably.build_handoff_payload` (default ``"fetch_and_claim"``);
            otherwise the (agent_id, action_name) lookup misses and the claim ends up
            with no recorded request payload.
        action_name: Action name; recorded in ``provably_intercepts.action_name``.
        intercept_index: Per-action sequence number used by the simulation hook to address a
            specific intercept (e.g. "mutate the second response of action X"). Default ``0``.
    """
    t_agent = _ctx_agent_id.set(agent_id)
    t_action = _ctx_action_name.set(action_name)
    t_index = _ctx_intercept_index.set(intercept_index)
    try:
        yield
    finally:
        _ctx_intercept_index.reset(t_index)
        _ctx_action_name.reset(t_action)
        _ctx_agent_id.reset(t_agent)


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
    # Monkey-patching third-party libraries is the whole point of this module — silence
    # mypy's `method-assign` check at the patch sites (the policy decision is documented
    # in CONTEXT.md).
    requests.Session.send = _wrap_session_send(_orig["requests_session_send"])  # type: ignore[method-assign]
    httpx.Client.send = _wrap_client_send(_orig["httpx_client_send"])  # type: ignore[method-assign]
    httpx.AsyncClient.send = _wrap_async_client_send(_orig["httpx_async_client_send"])  # type: ignore[method-assign,assignment]
    # Soft-dep: aiohttp is not a hard dependency of this SDK. When present, patch the
    # central ClientSession._request choke point that every aiohttp call routes through
    # (LiteLLM's default transport, optional Google GenAI / Google ADK paths, etc.).
    if _aiohttp is not None:
        _orig["aiohttp_session_request"] = _aiohttp.ClientSession._request
        _aiohttp.ClientSession._request = _wrap_aiohttp_request(_orig["aiohttp_session_request"])  # type: ignore[method-assign,assignment]
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
    agent_id = _ctx_agent_id.get() or "unknown"
    action_name = _ctx_action_name.get() or "unknown"
    row_id = insert_intercept_row(
        url=url,
        method=method,
        request_payload=request_payload,
        raw=raw,
        agent_id=agent_id,
        action_name=action_name,
    )
    if row_id is not None:
        global _last_intercept_row_id
        with _intercept_lock:
            _last_intercept_row_id = row_id
            _action_row_ids[(agent_id, action_name)] = row_id


def _maybe_transform_body(raw: Any) -> Any:
    hook = _intercept_body_hook
    if hook is None:
        return raw
    return hook(_ctx_intercept_index.get(), raw)


def _attach(response: Any, url: str, method: str, req_kwargs: dict[str, Any]) -> Any:
    """Record an httpx/requests response and optionally mutate it via the simulation hook.

    Short-circuits immediately when inside a self-egress block or already in the middle of
    recording (re-entry guard prevents double-recording when module-level calls like
    ``httpx.get`` internally delegate to a patched ``Client.send``).

    For aiohttp responses, see :func:`_wrap_aiohttp_request` which awaits the body
    asynchronously before calling :func:`_record_and_maybe_tamper` directly.
    """
    if is_self_egress() or already_recording():
        return response
    return _record_and_maybe_tamper(response, url, method, req_kwargs, extract_raw(response))


def _record_and_maybe_tamper(response: Any, url: str, method: str, req_kwargs: dict[str, Any], raw: Any) -> Any:
    """Inside-the-gate recording path shared by sync (_attach) and async (aiohttp) callers.

    Callers must have already cleared self-egress / re-entry guards. ``raw`` is the
    pre-extracted body (sync from ``extract_raw``, or awaited for aiohttp).
    """
    req = request_payload_dict(url, method, req_kwargs)
    nurl = normalize_url_for_trust(str(url))
    in_allowlist = _url_allowlist is not None and _url_in_allowlist(nurl)
    if _url_allowlist is not None and not in_allowlist:
        return response
    if _enabled:
        _insert_row(url, req, raw, method=method)
    # Tamper hook fires only for explicit run endpoints; never for OpenRouter, Provably API,
    # cluster handoff posts (those run with allowlist cleared or off-list).
    mutated = _maybe_transform_body(raw) if in_allowlist else raw
    if mutated is raw:
        return response
    if isinstance(response, requests.Response):
        return RequestsJsonOverride(response, mutated)
    if isinstance(response, httpx.Response):
        return HttpxJsonOverride(response, mutated)
    # aiohttp.ClientResponse and other libraries: body override not supported, return as-is.
    return response


def _wrap_call(orig_fn: Callable[..., Any], method: str) -> Callable[..., Any]:
    """Wrap a module-level convenience function (e.g. httpx.get, requests.post).

    Sets ``recording_scope`` BEFORE calling the original function so that any
    lower-level ``Client.send`` / ``Session.send`` wrapper that fires during the
    same call sees ``already_recording() == True`` and skips duplicate recording.
    After the original returns, ``_attach`` runs in the outer scope (where
    ``already_recording()`` is now False again) to do the actual recording.
    """

    def wrapped(url: Any, *args: Any, **kwargs: Any) -> Any:
        with recording_scope():
            response = orig_fn(url, *args, **kwargs)
        return _attach(response, str(url), method, dict(kwargs))

    return wrapped


def _decode_body_into_kwargs(kwargs: dict[str, Any], body: bytes | str | None, content_type: str) -> None:
    """Decode a raw request body into the kwargs shape ``request_payload_dict`` understands.

    JSON bodies (when Content-Type contains ``application/json``) are parsed and stored under
    ``json``; everything else is decoded to text and stored under ``data``. Mutates ``kwargs``.
    """
    if body is None or body == b"":
        return
    text = body if isinstance(body, str) else body.decode(errors="replace")
    if "application/json" in content_type:
        try:
            kwargs["json"] = json.loads(text)
            return
        except Exception:  # noqa: BLE001
            pass
    kwargs["data"] = text


def _httpx_request_to_kwargs(req: httpx.Request) -> dict[str, Any]:
    """Extract httpx.Request metadata into the kwargs shape request_payload_dict understands."""
    kwargs: dict[str, Any] = {}
    params = dict(req.url.params)
    if params:
        kwargs["params"] = params
    _decode_body_into_kwargs(kwargs, req.content, req.headers.get("content-type", ""))
    return kwargs


def _requests_prepared_to_kwargs(req: requests.PreparedRequest) -> dict[str, Any]:
    """Extract PreparedRequest metadata into the kwargs shape request_payload_dict understands."""
    kwargs: dict[str, Any] = {}
    parsed = urlsplit(str(req.url or ""))
    if parsed.query:
        raw_params = parse_qs(parsed.query, keep_blank_values=True)
        # Flatten single-value lists to scalars (matches typical kwargs["params"] shape)
        kwargs["params"] = {k: (v[0] if len(v) == 1 else v) for k, v in raw_params.items()}
    content_type = req.headers.get("Content-Type", "") if req.headers else ""
    _decode_body_into_kwargs(kwargs, req.body, content_type or "")
    return kwargs


def _wrap_client_send(
    orig_send: Callable[..., httpx.Response],
) -> Callable[..., httpx.Response]:
    """Wrap httpx.Client.send to record responses via _attach."""

    def wrapped(self: httpx.Client, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        response = orig_send(self, request, **kwargs)
        return cast(
            httpx.Response,
            _attach(response, str(request.url), request.method, _httpx_request_to_kwargs(request)),
        )

    return wrapped


def _wrap_async_client_send(
    orig_send: Callable[..., Awaitable[httpx.Response]],
) -> Callable[..., Awaitable[httpx.Response]]:
    """Wrap httpx.AsyncClient.send to record responses via _attach."""

    async def wrapped(self: httpx.AsyncClient, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        response = await orig_send(self, request, **kwargs)
        return cast(
            httpx.Response,
            _attach(response, str(request.url), request.method, _httpx_request_to_kwargs(request)),
        )

    return wrapped


def _wrap_session_send(
    orig_send: Callable[..., requests.Response],
) -> Callable[..., requests.Response]:
    """Wrap requests.Session.send to record responses via _attach."""

    def wrapped(self: requests.Session, request: requests.PreparedRequest, **kwargs: Any) -> requests.Response:
        response = orig_send(self, request, **kwargs)
        return cast(
            requests.Response,
            _attach(
                response,
                str(request.url),
                request.method or "GET",
                _requests_prepared_to_kwargs(request),
            ),
        )

    return wrapped


_AIOHTTP_KWARG_KEYS = ("params", "json", "data")


def _aiohttp_kwargs_to_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Filter aiohttp _request kwargs down to the subset request_payload_dict cares about."""
    return {k: v for k, v in kwargs.items() if k in _AIOHTTP_KWARG_KEYS and v is not None}


def _wrap_aiohttp_request(
    orig_request: Callable[..., Awaitable[Any]],
) -> Callable[..., Awaitable[Any]]:
    """Wrap aiohttp.ClientSession._request — the central method every aiohttp call routes through.

    Async wrapper: awaits the original to get a ClientResponse, then awaits ``response.read()``
    to populate aiohttp's body cache (so user code calling ``.json()`` / ``.text()`` later
    still works), parses the body, and routes through ``_record_and_maybe_tamper``.

    Body override (the simulation tamper hook) is not supported for aiohttp responses — the
    response is returned as-is. Recording works in full.
    """

    async def wrapped(self: Any, method: str, str_or_url: Any, **kwargs: Any) -> Any:
        response = await orig_request(self, method, str_or_url, **kwargs)
        if is_self_egress() or already_recording():
            return response
        with recording_scope():
            try:
                body_bytes = await response.read()
            except Exception:  # noqa: BLE001
                body_bytes = b""
            content_type = response.headers.get("Content-Type", "") if response.headers else ""
            text = body_bytes.decode(errors="replace") if body_bytes else ""
            if "application/json" in content_type and text:
                try:
                    raw = json.loads(text)
                except Exception:  # noqa: BLE001
                    raw = {"text": text}
            else:
                raw = {"text": text}
            return _record_and_maybe_tamper(
                response,
                str(str_or_url),
                method,
                _aiohttp_kwargs_to_kwargs(kwargs),
                raw,
            )

    return wrapped
