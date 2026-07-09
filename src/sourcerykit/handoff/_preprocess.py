import asyncio

from sourcerykit.bootstrap.bootstrap import get_bootstrap
from sourcerykit.errors import SourceryKitBootstrapError
from sourcerykit.logger import get_logger
from sourcerykit.provably._errors import ProvablyAPIError
from sourcerykit.provably.service import service

_log = get_logger(__name__)
_preprocess_lock = asyncio.Lock()


async def run_preprocess() -> None:
    """Run preprocessing for the intercept table.

    Handles concurrent preprocessing gracefully: uses a lock to serialize
    calls, and if preprocessing is already in progress, waits for it to
    complete first, then starts a NEW run to include the newly inserted row.
    """
    async with _preprocess_lock:
        _log.info("preprocess_started")
        provably = get_bootstrap()

        middleware_id = provably.middleware_id
        table_id = provably.table_id

        if middleware_id is None or table_id is None:
            _log.error("preprocess_failed_incomplete_bootstrap")
            raise SourceryKitBootstrapError("Provably bootstrap incomplete: middleware_id and table_id are required")

        # 1. Check if preprocessing is already in progress. A never-preprocessed table has no
        # status record yet (404) — treat that as "not started" and start the first run.
        try:
            status = await service.get_preprocess_status_only(middleware_id, table_id)
        except ProvablyAPIError as e:
            if e.status_code != 404:
                raise
            status = "unknown"
        _log.info("preprocess_status_check", status=status)

        # 2. If in progress, wait for it to complete first
        if status in ("pending", "processing"):
            _log.info("preprocess_waiting_for_existing", status=status)
            await service.get_preprocess_completed(middleware_id, table_id)

        # 3. Start NEW preprocessing (to include our newly inserted row)
        _log.info("preprocess_starting_new")
        await service.start_preprocess(middleware_id, table_id)

        # 4. Wait for the new preprocessing to complete
        await service.get_preprocess_completed(middleware_id, table_id)
        _log.info("preprocess_completed")
