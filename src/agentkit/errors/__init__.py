"""AgentKit exception hierarchy.

All exceptions raised by this library are subclasses of :class:`AgentKitError`.
"""

__all__ = [
    "AgentKitError",
    "AgentKitConfigError",
    "AgentKitBootstrapError",
    "AgentKitStorageError",
    "AgentKitTrustError",
]


class AgentKitError(Exception):
    """Base class for all AgentKit library errors."""


class AgentKitConfigError(AgentKitError):
    """Raised when configuration is invalid or missing (e.g. malformed env vars)."""


class AgentKitBootstrapError(AgentKitError):
    """Raised when the Provably bootstrap or handshake process fails."""


class AgentKitStorageError(AgentKitError):
    """Raised when a database or storage operation fails."""


class AgentKitTrustError(AgentKitError):
    """Raised when a request targets an endpoint not registered in the trust registry."""
