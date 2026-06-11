from sourcerykit.bootstrap._cache import _BOOTSTRAP_INSTANCE, ProvablyBootstrapCache
from sourcerykit.config import get_settings
from sourcerykit.db._engine import get_engine
from sourcerykit.db._schema import metadata
from sourcerykit.errors import SourceryKitBootstrapError, SourceryKitError, SourceryKitStorageError
from sourcerykit.intercept.interceptor import init_interceptor
from sourcerykit.logger import get_logger

_log = get_logger(__name__)


async def bootstrap_system() -> None:
    """System entry point called exactly once during container/server startup."""
    _log.info("system_bootstrap_started")

    # Validate configuration
    get_settings()

    # Initialize database schemas
    try:
        async with get_engine().begin() as conn:
            await conn.run_sync(metadata.create_all)
    except Exception as e:
        _log.error("bootstrap_db_schema_failed", error=str(e))
        raise SourceryKitStorageError("Failed to create database schema during bootstrap") from e

    # Initialize all required Provably resources
    try:
        await _BOOTSTRAP_INSTANCE.run_handshake()
    except SourceryKitError:
        raise
    except Exception as e:
        _log.error("bootstrap_handshake_failed_unexpected", error=str(e))
        raise SourceryKitBootstrapError("Unexpected error during Provably handshake") from e

    init_interceptor()
    _log.info("system_bootstrap_completed")


def get_bootstrap() -> ProvablyBootstrapCache:
    """Synchronous gateway to access resolved IDs."""
    return _BOOTSTRAP_INSTANCE
