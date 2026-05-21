"""httpx provider hook — intercept ``httpx.AsyncClient.send``."""

import json
from collections.abc import Awaitable, Callable
from typing import Any, cast

import httpx

from agentkit.intercept._self_egress import is_self_egress

_orig_async_client_send = None


def init_httpx_hooks(record_fn: Callable[[str, str, dict[str, Any], dict[str, Any]], Awaitable[None]]) -> None:
    """Patch ``httpx.AsyncClient.send``."""
    global _orig_async_client_send
    if _orig_async_client_send is not None:
        return
    _orig_async_client_send = httpx.AsyncClient.send
    patched_send = _make_async_wrapper(_orig_async_client_send, record_fn)
    httpx.AsyncClient.send = cast(Any, patched_send)


def _make_async_wrapper(
    orig: Callable[..., Awaitable[httpx.Response]],
    record_fn: Callable[[str, str, dict[str, Any], dict[str, Any]], Awaitable[None]],
) -> Callable[..., Awaitable[httpx.Response]]:
    async def wrapped(self, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        is_stream = kwargs.get("stream", False) or "text/event-stream" in request.headers.get("accept", "")
        response = await orig(self, request, **kwargs)

        if is_self_egress():
            return response

        url, method, payload = _httpx_request_to_payload(request)
        if not is_stream:
            try:
                raw = response.json()
            except Exception:
                raw = {"text": response.text}
            await record_fn(url, method, payload, raw)
            return response

        # Passive async stream
        orig_aiter = response.aiter_bytes
        chunks = []

        async def wrapped_aiter(*args, **p):
            async for chunk in orig_aiter(*args, **p):
                chunks.append(chunk)
                yield chunk
            try:
                full_text = b"".join(chunks).decode(errors="replace")
                await record_fn(url, method, payload, {"stream_logged": full_text})
            except Exception:
                pass

        response.aiter_bytes = wrapped_aiter
        return response

    return wrapped


def _httpx_request_to_payload(req: httpx.Request) -> tuple[str, str, dict[str, Any]]:
    """Extract metadata configuration payload parameters from an outbound Request."""
    kwargs: dict[str, Any] = {}
    if params := dict(req.url.params):
        kwargs["params"] = params

    if body := req.content:
        text = body.decode(errors="replace")
        if "application/json" in req.headers.get("content-type", ""):
            try:
                kwargs["json"] = json.loads(text)
            except Exception:
                kwargs["data"] = text
        else:
            kwargs["data"] = text

    payload = {k: kwargs[k] for k in ("params", "json", "data") if k in kwargs}
    return str(req.url), req.method, payload
