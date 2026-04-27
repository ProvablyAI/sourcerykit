"""Public Provably handoff API: one-shot runtime initialization."""

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
    """One-time SDK bootstrap; call once at process startup before enabling HTTP intercepts.

    Reads ``PROVABLY_RUST_BE_URL``, ``PROVABLY_API_KEY``, ``PROVABLY_ORG_ID`` and (when
    ``preprocess=True``) ``POSTGRES_URL``. Registers a Provably middleware, onboards the
    configured Postgres database, ensures the ``provably_intercepts`` collection exists, and
    caches an integration API key. With ``preprocess=True`` (default) it also pads the
    intercepts table to ≥2 rows and runs preprocess to completion. Idempotent per process via
    a module-level cache.

    Args:
        preprocess: When ``False``, skip table padding + preprocess (useful for unit tests or
            for callers that want to drive preprocess on their own schedule).

    Raises:
        ValueError: A required env var is missing.
        RuntimeError: Provably API returned an unrecoverable error during bootstrap.
    """
    ensure_bootstrap_cached()
    if not preprocess:
        return
    postgres_url = os.getenv("POSTGRES_URL", "").strip()
    if postgres_url:
        ensure_preprocess_intercept_padding(postgres_url)
    run_preprocess(cache()["org_id"], cache()["middleware_id"], cache()["table_id"])
