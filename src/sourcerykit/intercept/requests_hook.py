"""requests provider hook — intercept ``requests.adapters.HTTPAdapter.send``."""

import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

from requests.adapters import HTTPAdapter
from requests.models import PreparedRequest, Response

from sourcerykit.intercept._self_egress import is_self_egress
from sourcerykit.logger import get_logger

_log = get_logger(__name__)

_orig_adapter_send: Callable[..., Response] | None = None


def init_requests_hooks(
    record_fn: Callable[[str, str, dict[str, Any], dict[str, Any]], Coroutine[Any, Any, None]],
) -> None:
    """Patch ``requests.adapters.HTTPAdapter.send``."""
    global _orig_adapter_send
    if _orig_adapter_send is not None:
        return

    _orig_adapter_send = HTTPAdapter.send
    patched_send = _make_requests_wrapper(_orig_adapter_send, record_fn)
    setattr(HTTPAdapter, "send", patched_send)


def _make_requests_wrapper(
    orig: Callable[..., Response],
    record_fn: Callable[[str, str, dict[str, Any], dict[str, Any]], Coroutine[Any, Any, None]],
) -> Callable[..., Response]:
    def wrapped(self: HTTPAdapter, request: PreparedRequest, **kwargs: Any) -> Response:
        response = orig(self, request, **kwargs)

        if is_self_egress():
            return response

        url, method, payload = _requests_request_to_payload(request)
        is_stream = (
            kwargs.get("stream", False) or "text/event-stream" in response.headers.get("Content-Type", "").lower()
        )

        if not is_stream:
            try:
                raw = response.json()
            except Exception as e:
                _log.debug("requests_response_json_parse_failed", url=url, error=str(e))
                raw = {"text": response.text}
        else:
            raw = {"stream_logged": "stream_captured_via_requests"}

        _run_async(record_fn(url, method, payload, raw))

        return response

    return wrapped


def _requests_request_to_payload(req: PreparedRequest) -> tuple[str, str, dict[str, Any]]:
    """Extract parameters from a PreparedRequest object."""
    kwargs: dict[str, Any] = {}

    if body := req.body:
        if isinstance(body, bytes):
            text = body.decode(errors="replace")
        else:
            text = str(body)

        if "application/json" in req.headers.get("Content-Type", ""):
            try:
                kwargs["json"] = json.loads(text)
            except Exception as e:
                _log.debug("requests_request_json_parse_failed", error=str(e))
                kwargs["data"] = text
        else:
            kwargs["data"] = text

    payload = {k: kwargs[k] for k in ("json", "data") if k in kwargs}
    return str(req.url), str(req.method), payload


def _run_async(coroutine: Coroutine[Any, Any, None]) -> None:
    """Safely run an async coroutine from a synchronous context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coroutine)
        return

    if loop.is_running():
        asyncio.run_coroutine_threadsafe(coroutine, loop)
    else:
        loop.run_until_complete(coroutine)
