"""Read helpers for the ``provably_intercepts`` table."""

import json
from typing import Any

from agentkit.db._engine import get_engine
from agentkit.db._intercepts import select_intercepts_by_agent_id_and_action
from agentkit.errors import AgentKitStorageError
from agentkit.logger import get_logger

_log = get_logger(__name__)


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

        try:
            req = json.loads(row.request_payload) if row.request_payload else {}
        except json.JSONDecodeError as e:
            _log.error("intercept_request_payload_corrupt", agent_id=agent_id, action_name=action_name, error=str(e))
            raise AgentKitStorageError("Stored request_payload is not valid JSON") from e

        try:
            resp = json.loads(row.raw_response) if row.raw_response else None
        except json.JSONDecodeError as e:
            _log.error("intercept_raw_response_corrupt", agent_id=agent_id, action_name=action_name, error=str(e))
            raise AgentKitStorageError("Stored raw_response is not valid JSON") from e

        return req, resp
