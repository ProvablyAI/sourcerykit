"""Read helpers for the ``intercepts`` table."""

import json
from typing import Any
from uuid import UUID

from sourcerykit.db._engine import get_engine
from sourcerykit.db._intercepts import select_intercept_by_call_ref_stmt
from sourcerykit.errors import SourceryKitStorageError
from sourcerykit.logger import get_logger

_log = get_logger(__name__)


async def load_intercept_payload_by_call_ref(
    call_ref: UUID,
) -> tuple[dict[str, Any], dict[str, Any] | None, UUID]:
    """Return ``(request_payload, response_payload, row_id)`` for the row matching ``call_ref``.

    Raises ``SourceryKitStorageError`` if no row is found.
    """
    engine = get_engine()
    stmt = select_intercept_by_call_ref_stmt(call_ref)

    async with engine.connect() as conn:
        result = await conn.execute(stmt)
        row = result.fetchone()

    if not row:
        raise SourceryKitStorageError(f"No intercept found for call_ref={call_ref}")

    try:
        req = json.loads(row.request_payload) if row.request_payload else {}
    except json.JSONDecodeError as e:
        _log.error("intercept_request_payload_corrupt", call_ref=call_ref, error=str(e))
        raise SourceryKitStorageError("Stored request_payload is not valid JSON") from e

    try:
        resp = json.loads(row.raw_response) if row.raw_response else None
    except json.JSONDecodeError as e:
        _log.error("intercept_raw_response_corrupt", call_ref=call_ref, error=str(e))
        raise SourceryKitStorageError("Stored raw_response is not valid JSON") from e

    return req, resp, row.id
