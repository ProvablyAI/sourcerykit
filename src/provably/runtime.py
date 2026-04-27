from __future__ import annotations

from provably.handoff.client import initialize_runtime
from provably.intercept import disable, enable, init_interceptor

__all__ = ["configure_indexing"]


def configure_indexing(enable_indexing: bool) -> None:
    """One-call bootstrap for senders.

    True: bootstrap runtime, install the HTTP interceptor, enable recording.
    False: install the interceptor in passthrough mode (patched but disabled).
    """
    if enable_indexing:
        initialize_runtime()
        init_interceptor()
        enable()
    else:
        init_interceptor()
        disable()
