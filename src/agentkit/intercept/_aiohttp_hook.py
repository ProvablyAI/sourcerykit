"""aiohttp provider hook — intercept ``aiohttp.ClientSession._request``."""

import json
from collections.abc import Awaitable, Callable
from typing import Any, cast

import aiohttp

from agentkit.intercept._self_egress import is_self_egress
from agentkit.logger import get_logger

_log = get_logger(__name__)

_orig_request = None
_AIOHTTP_KWARG_KEYS = ("params", "json", "data")


def init_aiohttp_hooks(record_fn: Callable[[str, str, dict[str, Any], dict[str, Any]], Awaitable[None]]) -> None:
    """Patch ``aiohttp.ClientSession._request``."""
    global _orig_request
    if _orig_request is not None:
        return

    _orig_request = aiohttp.ClientSession._request

    patched_send = _make_aiohttp_wrapper(_orig_request, record_fn)
    aiohttp.ClientSession._request = cast(Any, patched_send)


def _make_aiohttp_wrapper(
    orig: Callable[..., Awaitable[Any]],
    record_fn: Callable[[str, str, dict[str, Any], dict[str, Any]], Awaitable[None]],
) -> Callable[..., Awaitable[Any]]:
    async def wrapped(self, method: str, str_or_url: Any, **kwargs: Any) -> Any:
        response = await orig(self, method, str_or_url, **kwargs)
        if is_self_egress():
            return response

        content_type = response.headers.get("Content-Type", "").lower()
        is_stream = (
            "text/event-stream" in content_type or response.headers.get("Transfer-Encoding", "").lower() == "chunked"
        )

        url_str = str(str_or_url)
        payload: dict[str, Any] = {k: kwargs[k] for k in _AIOHTTP_KWARG_KEYS if k in kwargs and kwargs[k] is not None}

        if is_stream:
            await record_fn(url_str, method, payload, {"stream": "stream_captured_via_aiohttp"})
            return response

        try:
            body_bytes = await response.read()
            text = body_bytes.decode(errors="replace") if body_bytes else ""
            raw = json.loads(text) if "application/json" in content_type and text else {"text": text}
        except Exception as e:
            _log.warning("aiohttp_body_parse_failed", url=url_str, error=str(e))
            raw = {"text": "non_json_or_exhausted_payload"}

        await record_fn(url_str, method, payload, raw)
        return response

    return wrapped
