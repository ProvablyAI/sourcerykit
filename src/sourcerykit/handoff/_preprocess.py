from sourcerykit.bootstrap.bootstrap import get_bootstrap
from sourcerykit.errors import SourceryKitBootstrapError
from sourcerykit.logger import get_logger
from sourcerykit.provably.service import service

_log = get_logger(__name__)


async def run_preprocess() -> None:
    _log.info("preprocess_started")
    provably = get_bootstrap()

    middleware_id = provably.middleware_id
    table_id = provably.table_id

    if middleware_id is not None and table_id is not None:
        await service.start_preprocess(middleware_id, table_id)
        await service.get_preprocess_completed(middleware_id, table_id)
    else:
        _log.error("preprocess_failed_incomplete_bootstrap")
        raise SourceryKitBootstrapError("Provably bootstrap incomplete: middleware_id and table_id are required")
