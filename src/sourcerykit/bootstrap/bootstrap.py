from sourcerykit.bootstrap._cache import _BOOTSTRAP_INSTANCE, ProvablyBootstrapCache
from sourcerykit.config import get_settings, save_local_env
from sourcerykit.db._engine import get_engine
from sourcerykit.db._schema import ensure_schema
from sourcerykit.errors import (
    SourceryKitConfigError,
    SourceryKitStorageError,
)
from sourcerykit.intercept.interceptor import init_interceptor
from sourcerykit.logger import get_logger
from sourcerykit.provably.service import service as provably_service

_log = get_logger(__name__)


async def bootstrap_system() -> None:
    """System entry point called exactly once during container/server startup."""
    _log.info("system_bootstrap_started")

    # Validate configuration
    settings = get_settings()

    if not settings.postgres_url:
        raise SourceryKitConfigError("SOURCERYKIT_POSTGRES_URL is required. Run 'sourcerykit init' first.")

    # Check sandbox health — recreate if expired
    sandbox, is_sandbox = await provably_service.get_sandbox_status(settings.postgres_url)
    if is_sandbox and sandbox:
        status = sandbox.get("status", "").lower()
        if status not in ("active", "provisioning"):
            _log.warning("sandbox_expired", status=status)
            org_id = settings.org_id
            if org_id:
                _log.info("sandbox_recreating")
                new_uri = await provably_service.create_sandbox(org_id)
                save_local_env(SOURCERYKIT_POSTGRES_URL=new_uri)
                _log.info("sandbox_recreated_reloading")
                settings = get_settings()
            else:
                _log.warning("sandbox_recreate_skipped_no_org")

    # Initialize database schemas (skip for sandbox — backend manages tables)
    if not is_sandbox:
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
