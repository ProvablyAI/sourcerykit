"""SQLAlchemy Core DML statements for the ``traces`` and ``trace_intercepts`` tables."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import Insert, Update, insert, update

from sourcerykit.db._schema import trace_intercepts, traces


def insert_trace(task: str) -> Insert:
    """Return a SQLAlchemy Core INSERT statement for a new trace row.

    Equivalent raw SQL::

        INSERT INTO traces (task)
        VALUES (...)
        RETURNING id
    """
    return insert(traces).values(task=task).returning(traces.c.id)


def insert_trace_intercept(
    trace_id: UUID,
    intercept_id: UUID,
    query_id: UUID,
    verification_mode: str,
    claimed_value: Any,
) -> Insert:
    """Return a SQLAlchemy Core INSERT statement for a new trace_intercept row.

    Equivalent raw SQL::

        INSERT INTO trace_intercepts
          (trace_id, intercept_id, query_id, verification_mode,
           claimed_value, outcome, detail)
        VALUES (...)
        RETURNING id
    """
    return (
        insert(trace_intercepts)
        .values(
            trace_id=trace_id,
            intercept_id=intercept_id,
            query_id=query_id,
            verification_mode=verification_mode,
            claimed_value=json.dumps(claimed_value, default=lambda o: o.model_dump())
            if claimed_value is not None
            else None,
        )
        .returning(trace_intercepts.c.id)
    )


def update_trace_intercept_outcome(id: UUID, outcome: str, details: str) -> Update:
    """Return a SQLAlchemy Core UPDATE statement to update outcome and details.

    Equivalent raw SQL::

        UPDATE trace_intercepts
        SET outcome = :outcome, details = :details
        WHERE id = :id
    """
    return (
        update(trace_intercepts)
        .where(
            trace_intercepts.c.id == id,
        )
        .values(outcome=outcome, details=details)
    )
