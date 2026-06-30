"""Self-egress exemption: SDK-internal HTTP calls bypass intercept recording and trust checks."""

import contextvars
from collections.abc import Generator
from contextlib import contextmanager

_self_egress: contextvars.ContextVar[bool] = contextvars.ContextVar("provably_self_egress", default=False)


def is_self_egress() -> bool:
    """Return True if the current task/thread is inside a provably_self_egress() block."""
    return _self_egress.get()


@contextmanager
def provably_self_egress() -> Generator[None, None, None]:
    """Mark a block of code as SDK-internal egress: skip trust check AND skip recording.

    Used by handoff.transport, handoff.evaluator, handoff._bootstrap (via handoff._http)
    when they make their own httpx / requests calls so the SDK doesn't trip its own gate.
    """
    token = _self_egress.set(True)
    try:
        yield
    finally:
        _self_egress.reset(token)
