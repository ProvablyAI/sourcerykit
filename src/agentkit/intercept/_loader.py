"""Read helpers for the ``provably_intercepts`` table."""

import json
from typing import Any

from agentkit.db.engine import get_engine
from agentkit.db.intercepts import select_intercepts_by_id_and_action


async def load_latest_intercept_payload(
    agent_id: str,
    action_name: str,
) -> tuple[dict[str, Any], Any]:
    """Return ``(request_payload, response_payload)`` for the most recent matching row.

    Both payloads are JSON-decoded when stored as strings; missing rows return ``({}, None)``.
    """
    engine = get_engine()
    stmt = select_intercepts_by_id_and_action(agent_id, action_name)

    async with engine.connect() as conn:
        result = await conn.execute(stmt)
        row = result.fetchone()

        if not row:
            return {}, None

        # Clean, modern named attribute access provided by SQLAlchemy Core rows
        request = _parse_json(row.request_payload, fallback={})
        response = _parse_json(row.raw_response, fallback=None)

        return request, response


def _parse_json(value: Any, fallback: Any) -> Any:
    """Safely decodes JSON strings, falling back to a default value if malformed or null."""
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    # If the database driver or SQLAlchemy already deserialized it into a dict/list
    return value if value is not None else fallback
