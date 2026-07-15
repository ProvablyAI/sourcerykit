"""Local FastAPI server for the SourceryKit trace dashboard."""

import json
import logging
import threading
import webbrowser
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sourcerykit.db._engine import get_engine
from sourcerykit.db._traces import (
    select_trace_by_id,
    select_trace_intercepts_by_trace_id,
)
from sourcerykit.evaluator._eval_modes import _get_by_json_path
from sourcerykit.provably.service import service

_log = logging.getLogger(__name__)

_DASHBOARD_HTML = Path(__file__).parent / "dashboard.html"
_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="SourceryKit Trace Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_methods=["GET"],
)

app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_DASHBOARD_HTML, media_type="text/html")


@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: UUID) -> dict[str, Any]:
    async with get_engine().connect() as conn:
        t = await conn.execute(select_trace_by_id(trace_id))
        trace_row = t.fetchone()
        if not trace_row:
            raise HTTPException(status_code=404, detail="Trace not found")
        trace = dict(trace_row._mapping)

        ti = await conn.execute(select_trace_intercepts_by_trace_id(trace_id))
        intercept_rows = [dict(row._mapping) for row in ti]

    intercepts = []
    for row in intercept_rows:
        qid = row.get("query_id")
        qid_str = str(qid) if qid else None
        actual_value = _extract_actual(row.get("raw_response"), row.get("claimed_value"))
        intercepts.append(
            {
                "id": str(row["id"]),
                "action_name": row["action_name"],
                "source_url": row["source_url"],
                "query_id": qid_str,
                "query_url": service.query_record_url(qid) if qid else None,
                "verification_mode": row["verification_mode"],
                "claimed_value": row["claimed_value"],
                "outcome": row["outcome"],
                "details": row["details"],
                "actual_value": actual_value,
            }
        )

    return {
        "trace": {
            "id": str(trace["id"]),
            "task": trace["task"],
            "created_at": trace["created_at"].isoformat() if trace.get("created_at") else None,
        },
        "intercepts": intercepts,
    }


def _extract_actual(raw_response: str | None, claimed_value: str | None) -> dict[str, Any]:
    """Extract actual values from stored raw_response for each claimed path."""
    if not raw_response:
        return {}
    try:
        data = json.loads(raw_response)
    except (json.JSONDecodeError, TypeError):
        return {}

    if not claimed_value:
        return {}
    try:
        pairs = json.loads(claimed_value) if isinstance(claimed_value, str) else claimed_value
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(pairs, list) or not pairs:
        return {}

    result: dict[str, Any] = {}
    for entry in pairs:
        path = entry.get("path", "$") if isinstance(entry, dict) else "$"
        try:
            result[path] = _get_by_json_path(data, path)
        except (KeyError, IndexError, TypeError):
            result[path] = None
    return result


def launch(trace_id: str, host: str = "127.0.0.1", port: int = 8743) -> None:
    url = f"http://{host}:{port}/?id={trace_id}"
    print(f"Opening trace dashboard at {url}")

    # ponytail: open browser after uvicorn binds; 0.5s is enough for a local server
    threading.Timer(0.5, webbrowser.open, args=[url]).start()

    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="warning")
