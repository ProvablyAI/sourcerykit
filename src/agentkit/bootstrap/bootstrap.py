from agentkit.bootstrap.provably import _BOOTSTRAP
from agentkit.db.engine import get_engine
from agentkit.db.schema import metadata
from agentkit.handoff._preprocess import run_preprocess
from provably import init_interceptor


async def bootstrap_system():
    async with get_engine().begin() as conn:
        await conn.run_sync(metadata.create_all)

    await _BOOTSTRAP.bootstrap()
    await run_preprocess()
    init_interceptor()
