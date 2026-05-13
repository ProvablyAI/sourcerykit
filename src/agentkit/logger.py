"""
Structured logging for AgentKit.

Wraps a standard logger with structlog to support contextvars (like run_id) and structured data.
"""

import logging

import structlog
from structlog.typing import FilteringBoundLogger

_stdlib_logger = logging.getLogger("agentkit")
_stdlib_logger.addHandler(logging.NullHandler())

logger = structlog.wrap_logger(_stdlib_logger)


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    """
    Returns a structured named logger.
    If name is None, it returns the base 'agentkit' logger.
    """
    if name:
        return structlog.wrap_logger(logging.getLogger(name))
    return logger
