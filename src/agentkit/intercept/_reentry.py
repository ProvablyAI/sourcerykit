"""Re-entry guard: prevent double-recording when module-level calls delegate to Client.send."""

import contextvars

_in_intercept: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "provably_in_intercept", default=False
)


def already_recording() -> bool:
    """Return True if the current task/thread is already inside an intercept wrapper."""
    return _in_intercept.get()


class recording_scope:
    """Context manager that marks the current task/thread as 'currently inside an intercept
    wrapper', so deeper layers (e.g. Client.send when called from httpx.get) can skip
    duplicate recording."""

    def __enter__(self) -> "recording_scope":
        self._token = _in_intercept.set(True)
        return self

    def __exit__(self, *exc: object) -> None:
        _in_intercept.reset(self._token)
