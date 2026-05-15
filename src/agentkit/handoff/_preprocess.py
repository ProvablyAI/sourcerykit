"""Provably preprocess: ≥2-row padding on ``provably_intercepts`` + preprocess polling + proof wait."""

from agentkit.handoff._bootstrap import _BOOTSTRAP
from agentkit.logger import get_logger
from agentkit.provably import service

_log = get_logger(__name__)


async def preprocess_after_intercept_write() -> None:
    await run_preprocess()


async def run_preprocess() -> None:
    if _BOOTSTRAP.middleware_id is not None and _BOOTSTRAP.table_id is not None:
        await service.start_preprocess(_BOOTSTRAP.middleware_id, _BOOTSTRAP.table_id)
        await service.get_preprocess_completed(_BOOTSTRAP.middleware_id, _BOOTSTRAP.table_id)
    else:
        raise
