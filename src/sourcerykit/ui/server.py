"""Local FastAPI server for the SourceryKit trace dashboard."""

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
    select_trace_by_id_prefix,
    select_trace_intercepts_by_trace_id,
)
from sourcerykit.provably.service import service
from sourcerykit.utils import extract_actual

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
async def get_trace(trace_id: str) -> dict[str, Any]:
    try:
        uid = UUID(trace_id)
    except ValueError:
        uid = await _resolve_prefix(trace_id)

    async with get_engine().connect() as conn:
        t = await conn.execute(select_trace_by_id(uid))
        trace_row = t.fetchone()
        if not trace_row:
            raise HTTPException(status_code=404, detail="Trace not found")
        trace = dict(trace_row._mapping)

        ti = await conn.execute(select_trace_intercepts_by_trace_id(uid))
        intercept_rows = [dict(row._mapping) for row in ti]

    intercepts = []
    for row in intercept_rows:
        qid = row.get("query_id")
        qid_str = str(qid) if qid else None
        actual_value = extract_actual(row.get("raw_response"), row.get("claimed_value"))
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
            "reasoning": trace["reasoning"],
            "created_at": trace["created_at"].isoformat() if trace.get("created_at") else None,
        },
        "intercepts": intercepts,
    }


async def _resolve_prefix(prefix: str) -> UUID:
    """Resolve a short prefix to a full UUID, or raise HTTPException."""
    async with get_engine().connect() as conn:
        result = await conn.execute(select_trace_by_id_prefix(prefix))
        rows = [dict(row._mapping) for row in result]

    if not rows:
        raise HTTPException(status_code=404, detail="Trace not found")
    if len(rows) > 1:
        raise HTTPException(
            status_code=409,
            detail=f'Ambiguous prefix "{prefix}" — matches {len(rows)} traces. Use a longer prefix.',
        )
    return UUID(str(rows[0]["id"]))


def launch(trace_id: str, host: str = "127.0.0.1", port: int = 8743) -> None:
    url = f"http://{host}:{port}/?id={trace_id}"
    print(f"Opening trace dashboard at {url}")

    # ponytail: open browser after uvicorn binds; 0.5s is enough for a local server
    threading.Timer(0.5, webbrowser.open, args=[url]).start()

    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="warning")
