"""SQLAlchemy Core DML statements for the ``traces`` and ``trace_intercepts`` tables."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import Insert, Select, String, Update, case, func, insert, select, update

from sourcerykit.db._schema import intercepts, trace_intercepts, traces


def insert_trace(task: str, answer: str) -> Insert:
    """Return a SQLAlchemy Core INSERT statement for a new trace row.

    Equivalent raw SQL::

        INSERT INTO traces (task, answer)
        VALUES (...)
        RETURNING id
    """
    return insert(traces).values(task=task, answer=answer).returning(traces.c.id)


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


def select_traces_with_intercept_count(limit: int = 20, offset: int = 0) -> Select[tuple[Any, ...]]:
    """Return a SELECT that lists traces with per-outcome intercept counts.

    Equivalent raw SQL::

        SELECT t.id, t.task, t.created_at,
               count(ti.id) AS total,
               count(ti.id) FILTER (WHERE ti.outcome = 'PASS') AS pass,
               count(ti.id) FILTER (WHERE ti.outcome = 'CAUGHT') AS caught,
               count(ti.id) FILTER (WHERE ti.outcome = 'ERROR') AS error
        FROM traces t
        LEFT JOIN trace_intercepts ti ON t.id = ti.trace_id
        GROUP BY t.id, t.task, t.created_at
        ORDER BY t.created_at DESC
    """
    return (
        select(
            traces.c.id,
            traces.c.task,
            traces.c.answer,
            traces.c.created_at,
            func.count(trace_intercepts.c.id).label("total"),
            func.count(case((trace_intercepts.c.outcome == "PASS", 1))).label("pass"),
            func.count(case((trace_intercepts.c.outcome == "CAUGHT", 1))).label("caught"),
            func.count(case((trace_intercepts.c.outcome == "ERROR", 1))).label("error"),
        )
        .select_from(traces.outerjoin(trace_intercepts, traces.c.id == trace_intercepts.c.trace_id))
        .group_by(traces.c.id, traces.c.task, traces.c.answer, traces.c.created_at)
        .order_by(traces.c.created_at.desc())
        .offset(offset)
        .limit(limit)
    )


def select_trace_by_id(trace_id: UUID) -> Select[tuple[Any, ...]]:
    """Return a SELECT for a single trace by ID."""
    return select(traces.c.id, traces.c.task, traces.c.answer, traces.c.created_at).where(traces.c.id == trace_id)


def select_trace_by_id_prefix(prefix: str) -> Select[tuple[Any, ...]]:
    """Return a SELECT for traces whose UUID starts with *prefix*."""
    return select(traces.c.id, traces.c.task, traces.c.answer, traces.c.created_at).where(
        func.cast(traces.c.id, String).like(f"{prefix}%")
    )


def select_trace_intercepts_by_trace_id(trace_id: UUID) -> Select[tuple[Any, ...]]:
    """Return a SELECT that lists intercepts for a trace, joined with intercept details.

    Equivalent raw SQL::

        SELECT ti.id, ti.query_id, ti.verification_mode, ti.claimed_value,
               ti.outcome, ti.details, ti.created_at,
               i.action_name, i.source_url
        FROM trace_intercepts ti
        JOIN intercepts i ON ti.intercept_id = i.id
        WHERE ti.trace_id = :trace_id
        ORDER BY ti.created_at
    """
    return (
        select(
            trace_intercepts.c.id,
            trace_intercepts.c.query_id,
            trace_intercepts.c.verification_mode,
            trace_intercepts.c.claimed_value,
            trace_intercepts.c.outcome,
            trace_intercepts.c.details,
            trace_intercepts.c.created_at,
            intercepts.c.action_name,
            intercepts.c.source_url,
            intercepts.c.raw_response,
        )
        .select_from(trace_intercepts.join(intercepts, trace_intercepts.c.intercept_id == intercepts.c.id))
        .where(trace_intercepts.c.trace_id == trace_id)
        .order_by(trace_intercepts.c.created_at)
    )
