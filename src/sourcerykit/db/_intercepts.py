"""SQLAlchemy Core DML statements for the ``intercepts`` table."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import Dialect, Insert, column, create_mock_engine, insert, select, text
from sqlalchemy.sql.selectable import Select

from sourcerykit.db._schema import intercepts

_ENGINE = create_mock_engine("postgresql+psycopg://", executor=lambda *args, **kwargs: None)

_PG: Dialect = _ENGINE.dialect
_t = intercepts


def insert_intercept(
    agent_id: str,
    action_name: str,
    source_url: str,
    request_payload: dict[str, object],
    raw_response: dict[str, object],
    response_hash: str,
    call_ref: UUID | None = None,
) -> Insert:
    """Return a SQLAlchemy Core INSERT statement for a new intercept row.

    Equivalent raw SQL::

        INSERT INTO intercepts
          (agent_id, action_name, source_url, request_payload, raw_response, response_hash, call_ref)
        VALUES (...)
        RETURNING id
    """
    return (
        insert(intercepts)
        .values(
            agent_id=agent_id,
            action_name=action_name,
            source_url=source_url,
            request_payload=json.dumps(request_payload),
            raw_response=json.dumps(raw_response),
            response_hash=response_hash,
            call_ref=call_ref,
        )
        .returning(intercepts.c.id)
    )


def select_intercepts_by_action(action_name: str) -> str:
    """Return a SQL string that fetches all rows matching ``action_name``.

    SELECT * FROM intercepts WHERE action_name = :action_name
    """
    stmt = select(text("*")).select_from(_t).where(column(_t.c.action_name.name) == action_name)
    return stmt.compile(dialect=_PG, compile_kwargs={"literal_binds": True}).string.replace("\n", "")


def select_intercept_by_call_ref(call_ref: UUID) -> str:
    """Return a compiled SQL string that fetches the row matching the given call_ref."""
    stmt = select(text("*")).select_from(_t).where(column(_t.c.call_ref.name) == call_ref)
    return stmt.compile(dialect=_PG, compile_kwargs={"literal_binds": True}).string.replace("\n", "")


def select_intercept_by_call_ref_stmt(call_ref: UUID) -> Select[Any]:
    """Return a Select construct that fetches the row matching the given call_ref."""
    return select(text("*")).select_from(_t).where(column(_t.c.call_ref.name) == call_ref)
