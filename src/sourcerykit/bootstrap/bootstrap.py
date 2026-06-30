from sourcerykit.bootstrap._cache import _BOOTSTRAP_INSTANCE, ProvablyBootstrapCache
from sourcerykit.config import get_settings
from sourcerykit.db._engine import get_engine
from sourcerykit.db._schema import ensure_schema
from sourcerykit.errors import (
    SourceryKitConfigError,
    SourceryKitStorageError,
)
from sourcerykit.intercept.interceptor import init_interceptor
from sourcerykit.logger import get_logger

_log = get_logger(__name__)


async def bootstrap_system() -> None:
    """System entry point called exactly once during container/server startup."""
    _log.info("system_bootstrap_started")

    # Validate configuration
    settings = get_settings()

    if not settings.postgres_url:
        raise SourceryKitConfigError("SOURCERYKIT_POSTGRES_URL is required. Run 'sourcerykit init' first.")

    # Initialize database schemas
    try:
        await ensure_schema(get_engine())
    except Exception as e:
        _log.error("bootstrap_db_schema_failed", error=str(e))
        raise SourceryKitStorageError("Failed to create database schema during bootstrap") from e

    # Populate from cached settings or run handshake
    if settings.has_bootstrap_ids:
        _log.info("bootstrap_using_cached_ids")
        _BOOTSTRAP_INSTANCE.load_from(settings)
    else:
        _log.info("bootstrap_running_handshake")
        await _BOOTSTRAP_INSTANCE.run_handshake(project_name=settings.project_name)

    init_interceptor()
    _log.info("system_bootstrap_completed")


def get_bootstrap() -> ProvablyBootstrapCache:
    """Synchronous gateway to access resolved IDs."""
    return _BOOTSTRAP_INSTANCE
