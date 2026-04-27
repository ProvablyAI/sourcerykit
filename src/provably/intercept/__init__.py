"""Intercept phase: monkey-patch ``requests`` + ``httpx`` and record responses into Postgres."""

from ._loader import load_latest_intercept_payload
from .interceptor import (
    clear_intercept_row_ids,
    disable,
    enable,
    get_intercept_row_id,
    init_interceptor,
    is_enabled,
    set_intercept_body_hook,
    set_intercept_url_allowlist,
    set_interceptor_context,
    take_last_intercept_row_id,
)

__all__ = [
    "clear_intercept_row_ids",
    "disable",
    "enable",
    "get_intercept_row_id",
    "init_interceptor",
    "is_enabled",
    "load_latest_intercept_payload",
    "set_intercept_body_hook",
    "set_intercept_url_allowlist",
    "set_interceptor_context",
    "take_last_intercept_row_id",
]
