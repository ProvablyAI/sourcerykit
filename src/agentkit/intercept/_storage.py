import hashlib
import json
from typing import Any

from agentkit.db import insert_intercept
from agentkit.db.engine import get_engine
from agentkit.handoff._preprocess import run_preprocess
from agentkit.intercept._self_egress import is_self_egress
from agentkit.logger import get_logger
from agentkit.trusted_endpoints import is_endpoint_trusted

_log = get_logger(__name__)


def hash_payload(raw: Any) -> str:
    return hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()


async def add_intercept_row(
    url: str,
    method: str,
    request_payload: dict[str, Any],
    raw: Any,
    agent_id: str,
    action_name: str,
) -> int | None:
    if is_self_egress():
        return None

    await is_endpoint_trusted(url)

    engine = get_engine()

    stmt = insert_intercept(
        agent_id,
        action_name,
        url,
        json.dumps(request_payload, sort_keys=True),
        json.dumps(raw),
        hash_payload(raw),
    )

    async with engine.begin() as conn:
        await conn.execute(stmt)

    _log.info("intercept_stored", agent_id=agent_id, action_name=action_name, url=url, method=method)
    await run_preprocess()

    # TODO: return row id
