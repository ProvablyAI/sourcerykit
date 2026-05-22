import hashlib
import json
from typing import Any
from uuid import UUID

from agentkit.db.engine import get_engine
from agentkit.db.intercepts import insert_intercept
from agentkit.errors import AgentKitTrustError
from agentkit.intercept._self_egress import is_self_egress
from agentkit.logger import get_logger
from agentkit.trusted_endpoints import is_endpoint_trusted

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
) -> UUID | None:
    if is_self_egress():
        return None

    trusted = await is_endpoint_trusted(url)
    if not trusted:
        raise AgentKitTrustError(f"endpoint not registered in trust registry: {url}")

    engine = get_engine()

    stmt = insert_intercept(
        agent_id,
        action_name,
        url,
        request_payload,
        raw,
        hash_payload(raw),
    )

    async with engine.begin() as conn:
        result = await conn.execute(stmt)
        row = result.fetchone()

    _log.info("intercept_stored", agent_id=agent_id, action_name=action_name, url=url, method=method)
    from agentkit.handoff._preprocess import run_preprocess  # noqa: PLC0415

    await run_preprocess()

    return row[0] if row else None
