"""SQLAlchemy Core DML statements for the ``provably_intercepts`` table."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import Dialect, Insert, and_, column, create_engine, insert, select, text
from sqlalchemy.sql.selectable import Select

from agentkit.db._schema import provably_intercepts

_ENGINE = create_engine("postgresql://")
_PG: Dialect = _ENGINE.dialect
_t = provably_intercepts


def insert_intercept(
    agent_id: str,
    action_name: str,
    source_url: str,
    request_payload: dict[str, object],
    raw_response: dict[str, object],
    response_hash: str,
) -> Insert:
    """Return a SQLAlchemy Core INSERT statement for a new intercept row.

    Equivalent raw SQL::

        INSERT INTO provably_intercepts
          (agent_id, action_name, source_url, request_payload, raw_response, response_hash)
        VALUES (...)
        RETURNING id
    """
    return (
        insert(provably_intercepts)
        .values(
            agent_id=agent_id,
            action_name=action_name,
            source_url=source_url,
            request_payload=json.dumps(request_payload),
            raw_response=json.dumps(raw_response),
            response_hash=response_hash,
        )
        .returning(provably_intercepts.c.id)
    )


def select_intercept_by_id(row_id: UUID) -> str:
    """Return a SQL string that fetches a single row by primary key.

    SELECT * FROM provably_intercepts WHERE id = :row_id
    """
    stmt = select(text("*")).select_from(_t).where(column(_t.c.id.name) == row_id)
    return stmt.compile(dialect=_PG, compile_kwargs={"literal_binds": True}).string.replace("\n", "")


def select_intercepts_by_action(action_name: str) -> str:
    """Return a SQL string that fetches all rows matching ``action_name``.

    SELECT * FROM provably_intercepts WHERE action_name = :action_name
    """
    stmt = select(text("*")).select_from(_t).where(column(_t.c.action_name.name) == action_name)
    return stmt.compile(dialect=_PG, compile_kwargs={"literal_binds": True}).string.replace("\n", "")


def select_intercepts_by_agent_id_and_action(agent_id: str, action_name: str) -> Select[tuple[Any, ...]]:
    """Return a Select construct that fetches all rows matching ``row_id`` and ``action_name``.

    Equivalent raw SQL::

        SELECT * FROM provably_intercepts
        WHERE action_name = :action_name AND agent_id = :agent_id
    """
    return select(provably_intercepts).where(
        and_(provably_intercepts.c.action_name == action_name, provably_intercepts.c.agent_id == agent_id)
    )
