import hashlib
import json
from typing import Any
from uuid import UUID

from sourcerykit.db._engine import get_engine
from sourcerykit.db._intercepts import insert_intercept
from sourcerykit.errors import SourceryKitTrustError
from sourcerykit.intercept._self_egress import is_self_egress
from sourcerykit.logger import get_logger
from sourcerykit.trusted_endpoints import is_endpoint_trusted
from sourcerykit.utils.validation import validate_length

_log = get_logger(__name__)


def hash_payload(raw: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()


async def add_intercept_row(
    url: str,
    method: str,
    request_payload: dict[str, Any],
    raw: dict[str, Any],
    agent_id: str,
    action_name: str,
    call_ref: UUID | None = None,
) -> UUID | None:
    # Validate identifiers that map to VARCHAR DB columns
    validate_length("agent_id", agent_id, max_len=255)
    validate_length("action_name", action_name, max_len=255)
    if is_self_egress():
        return None

    trusted = await is_endpoint_trusted(url)
    if not trusted:
        raise SourceryKitTrustError(f"endpoint not registered in trust registry: {url}")

    engine = get_engine()

    stmt = insert_intercept(
        agent_id,
        action_name,
        url,
        request_payload,
        raw,
        hash_payload(raw),
        call_ref=call_ref,
    )

    async with engine.begin() as conn:
        result = await conn.execute(stmt)
        row = result.fetchone()

    _log.info("intercept_stored", agent_id=agent_id, action_name=action_name, url=url, method=method)
    from sourcerykit.handoff._preprocess import run_preprocess  # noqa: PLC0415

    await run_preprocess()

    return row[0] if row else None
