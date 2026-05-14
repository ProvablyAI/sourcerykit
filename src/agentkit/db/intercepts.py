"""SQLAlchemy Core DML statements for the ``provably_intercepts`` table."""

from sqlalchemy import insert, select

from agentkit.db.schema import provably_intercepts


def insert_intercept(
    *,
    agent_id: str,
    action_name: str,
    source_url: str,
    request_payload: str,
    raw_response: str,
    response_hash: str,
):
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
            request_payload=request_payload,
            raw_response=raw_response,
            response_hash=response_hash,
        )
        .returning(provably_intercepts.c.id)
    )


def select_intercept_by_id(row_id: int):
    """Return a SELECT statement that fetches a single row by primary key.

    Equivalent raw SQL::

        SELECT * FROM provably_intercepts WHERE id = :row_id
    """
    return select(provably_intercepts).where(provably_intercepts.c.id == row_id)


def select_intercepts_by_action(action_name: str):
    """Return a SELECT statement that fetches all rows matching ``action_name``.

    Equivalent raw SQL::

        SELECT * FROM provably_intercepts WHERE action_name = :action_name
    """
    return select(provably_intercepts).where(provably_intercepts.c.action_name == action_name)
