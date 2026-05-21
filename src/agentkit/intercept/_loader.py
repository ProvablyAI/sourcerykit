"""Read helpers for the ``provably_intercepts`` table."""

import json
from typing import Any

from agentkit.db.engine import get_engine
from agentkit.db.intercepts import select_intercepts_by_agent_id_and_action


async def load_latest_intercept_payload(
    agent_id: str,
    action_name: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return ``(request_payload, response_payload)`` for the most recent matching row.

    Missing rows return ``({}, None)``.
    """
    engine = get_engine()
    stmt = select_intercepts_by_agent_id_and_action(agent_id, action_name)

    async with engine.connect() as conn:
        result = await conn.execute(stmt)
        row = result.fetchone()

        if not row:
            return {}, None

        req = json.loads(row.request_payload) if row.request_payload else {}
        resp = json.loads(row.raw_response) if row.raw_response else None
        return req, resp
