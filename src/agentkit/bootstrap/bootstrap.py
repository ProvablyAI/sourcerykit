from agentkit.bootstrap.provably import _BOOTSTRAP_INSTANCE, ProvablyBootstrapCache
from agentkit.db.engine import get_engine
from agentkit.db.schema import metadata
from agentkit.intercept import init_interceptor
from agentkit.logger import get_logger

_log = get_logger(__name__)


async def bootstrap_system() -> None:
    """System entry point called exactly once during container/server startup."""
    _log.info("system_bootstrap_started")

    # Initialize database schemas
    async with get_engine().begin() as conn:
        await conn.run_sync(metadata.create_all)

    # Initialize all required Provably resources
    await _BOOTSTRAP_INSTANCE.run_handshake()

    # Run preprocess
    from agentkit.handoff._preprocess import run_preprocess

    await run_preprocess()

    # 4. Initialize interceptor
    init_interceptor()
    _log.info("system_bootstrap_completed")


def get_bootstrap() -> ProvablyBootstrapCache:
    """Synchronous gateway to access resolved IDs."""
    return _BOOTSTRAP_INSTANCE
