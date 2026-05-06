"""Intercept phase: monkey-patch ``requests`` + ``httpx`` and record responses into Postgres."""

from ._loader import load_latest_intercept_payload as load_latest_intercept_payload
from ._self_egress import provably_self_egress as provably_self_egress
from .interceptor import (
    clear_intercept_row_ids as clear_intercept_row_ids,
)
from .interceptor import (
    disable,
    enable,
    init_interceptor,
    intercept_context,
    is_enabled,
    set_intercept_body_hook,
    set_intercept_url_allowlist,
    set_interceptor_context,
    take_last_intercept_row_id,
)
from .interceptor import (
    get_intercept_row_id as get_intercept_row_id,
)

__all__ = [
    "disable",
    "enable",
    "init_interceptor",
    "intercept_context",
    "is_enabled",
    "provably_self_egress",
    "set_intercept_body_hook",
    "set_intercept_url_allowlist",
    "set_interceptor_context",
    "take_last_intercept_row_id",
]
