"""Structured logging for AgentKit."""

import logging

import structlog
from structlog.typing import FilteringBoundLogger

_stdlib_root = logging.getLogger("agentkit")
_stdlib_root.addHandler(logging.NullHandler())

# Cache wrapped loggers, return the same object for the same name
loggers: dict[str, FilteringBoundLogger] = {}


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    """Return a wrapped logger for *name*.

    Args:
        name: Logger name, typically ``__name__``. Defaults to ``"agentkit"``.
    """
    key = name or "agentkit"
    if key not in loggers:
        loggers[key] = structlog.wrap_logger(logging.getLogger(key))
    return loggers[key]
