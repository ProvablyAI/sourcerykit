"""Public Provably handoff API: runtime init."""

from __future__ import annotations

import os

from provably.handoff._bootstrap import (
    cache,
    cached_integration_api_key,
    ensure_bootstrap_cached,
    runtime_ready,
)
from provably.handoff._preprocess import (
    ensure_preprocess_intercept_padding,
    run_preprocess,
)

__all__ = [
    "cached_integration_api_key",
    "initialize_runtime",
    "runtime_ready",
]


def initialize_runtime(*, preprocess: bool = True) -> None:
    """One-time startup init. Must be called before enabling HTTP intercepts."""
    ensure_bootstrap_cached()
    if not preprocess:
        return
    postgres_url = os.getenv("POSTGRES_URL", "").strip()
    if postgres_url:
        ensure_preprocess_intercept_padding(postgres_url)
    run_preprocess(cache()["org_id"], cache()["middleware_id"], cache()["table_id"])
