"""Structured logging helpers backing the SDK.

Configures ``structlog`` to emit JSON-per-line to stdout and merge ``contextvars`` (so callers can
bind ``run_id`` / request-scoped fields once per entry point and have them appear on every log).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging() -> None:
    """Install the SDK's JSON structlog configuration on the root logger.

    Mutates global logging state; later calls overwrite earlier configuration. Call once at
    process startup before the first log.
    """
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """Return a bound structlog logger; pass ``__name__`` from the caller for module-scoped logs.

    The return type is :class:`~typing.Any` because :func:`structlog.get_logger` returns a
    dynamically-bound logger whose surface is stub-only and not consistently typed across
    structlog versions; callers should treat it as a duck-typed logger.
    """
    return structlog.get_logger(name)
