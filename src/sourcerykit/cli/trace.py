import asyncio
import base64
import json
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import typer
from rich.markup import escape as rich_escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sourcerykit.cli.utils import console, require_settings
from sourcerykit.db._engine import get_engine
from sourcerykit.db._traces import (
    select_trace_by_id,
    select_trace_by_id_prefix,
    select_trace_intercepts_by_trace_id,
    select_traces_with_intercept_count,
)
from sourcerykit.provably._answer_model import QueryAnswer
from sourcerykit.provably.service import service
from sourcerykit.utils import extract_actual

trace = typer.Typer(no_args_is_help=True)

_JSON_LINES = 50


@trace.command(name="list")
def list_traces(
    limit: int = typer.Option(20, "--limit", "-n", help="rows per page"),
    page: int = typer.Option(1, "--page", "-p", help="page number (1-based)"),
) -> None:
    """Show all traces with intercept outcome counts."""
    require_settings()
    offset = max(0, (page - 1) * limit)
    rows = asyncio.run(_fetch_traces(limit, offset))

    if not rows:
        console.print("[yellow]No traces found.[/yellow]")
        return

    table = Table(title="Traces")
    table.add_column("ID", style="dim")
    table.add_column("Task", style="cyan")
    table.add_column("Created", style="white")
    table.add_column("Pass", style="green", justify="right")
    table.add_column("Caught", style="red", justify="right")
    table.add_column("Error", style="yellow", justify="right")

    for r in rows:
        table.add_row(
            str(r["id"])[:8],
            r["task"],
            str(r["created_at"]),
            str(r["pass"]),
            str(r["caught"]),
            str(r["error"]),
        )

    console.print(table)


@trace.command()
def show(
    id: str = typer.Argument(help="trace ID"),
    save_proof: Annotated[
        bool, typer.Option("--save-proof", help="download and save proofs to .provably files")
    ] = False,
    ui: Annotated[bool, typer.Option("--ui/--no-ui", help="open interactive dashboard in browser")] = True,
) -> None:
    """Show details of a single trace and its intercepts."""
    if ui:
        require_settings()
        from sourcerykit.ui.server import launch

        launch(trace_id=id)
        return
    require_settings()
    trace_id = _resolve_trace_id(id)
    trace_row, intercept_rows = asyncio.run(_fetch_trace_detail(trace_id))

    if not trace_row:
        console.print(f"[red]Trace {id} not found.[/red]")
        raise typer.Exit(code=1)

    # --- Summary badges ---
    counts: dict[str, int] = {"PASS": 0, "CAUGHT": 0, "ERROR": 0}
    for r in intercept_rows:
        o = r["outcome"]
        if o in counts:
            counts[o] += 1

    # --- Header panel ---
    title = trace_row["task"] or "Untitled trace"
    info = Text()
    info.append("ID: ", style="dim")
    info.append(str(trace_row["id"]), style="dim")
    info.append("  Created: ", style="dim")
    info.append(str(trace_row["created_at"]), style="dim")
    info.append("\n")
    info.append(f"{counts['PASS']} PASS", style=green)
    info.append(f"  {counts['CAUGHT']} CAUGHT", style=red)
    info.append(f"  {counts['ERROR']} ERROR", style=yellow)
    if trace_row.get("reasoning"):
        info.append("\n\n")
        info.append("Reasoning\n", style="bold")
        reasoning_text = Text(rich_escape(trace_row["reasoning"]), no_wrap=False)
        info.append_text(reasoning_text)
    console.print(Panel(info, title=f"[bold]{rich_escape(title)}[/bold]", border_style="dim", expand=False))

    if not intercept_rows:
        console.print("[yellow]No intercepts.[/yellow]")
        return

    # --- Fetch query data for secondary info ---
    query_ids = [r["query_id"] for r in intercept_rows]
    queries = asyncio.run(_fetch_queries(query_ids))

    # --- Per-claim cards ---
    for i, row in enumerate(intercept_rows, 1):
        outcome = row["outcome"] or ""
        style = _outcome_style(outcome)
        qid = row["query_id"]
        qdata = queries.get(qid)

        # --- Card header ---
        header = Text()
        header.append(f"#{i} ", style="dim")
        header.append(row["action_name"] or "", style="bold")
        header.append(f"  {outcome}", style=style)

        # --- Card body ---
        body = Text()
        body.append("  Source: ", style="dim")
        body.append(rich_escape(row["source_url"] or "N/A"), style="white")
        body.append("\n")
        body.append("  Mode:   ", style="dim")
        body.append(rich_escape(row["verification_mode"] or "N/A"), style="white")
        body.append("\n")
        if qid:
            try:
                query_url = service.query_record_url(qid)
                body.append("  Query:  ", style="dim")
                body.append(query_url, style="blue underline")
                body.append("\n")
            except Exception:
                pass
        body.append("\n")

        # --- Comparison section ---
        _append_comparison(body, row, outcome)

        # --- Secondary info (SQL, Proof, Result) ---
        _append_secondary(body, qdata)

        console.print(Panel(body, title=header, border_style=style, expand=False))

        # --- Save proof ---
        if save_proof and qdata:
            proof = qdata.get("proof")
            if isinstance(proof, dict):
                proof_id = proof.get("id")
                if proof_id:
                    filename = f"{trace_id}_{row['action_name']}_{i}.provably"
                    proof_bytes = asyncio.run(_download_proof(UUID(proof_id)))
                    envelope = _wrap_proof(
                        trace_id=str(trace_id),
                        intercept_id=str(row["id"]),
                        action_name=row["action_name"],
                        intercept_num=i,
                        proof_bytes=proof_bytes,
                    )
                    Path(filename).write_text(json.dumps(envelope, indent=2, default=str))
                    console.print(f"  [green]Saved to {filename}[/green]")

    console.print()


# --- Helpers ---
green, red, yellow = "green", "red", "yellow"


def _outcome_style(outcome: str) -> str:
    return {"PASS": green, "CAUGHT": red, "ERROR": yellow}.get(outcome, "white")


def _resolve_trace_id(raw: str) -> UUID:
    """Resolve a full UUID or an unambiguous prefix to a UUID."""
    try:
        return UUID(raw)
    except ValueError:
        pass

    rows = asyncio.run(_query_trace_prefix(raw))
    if not rows:
        console.print(f'[red]No trace found matching prefix "{raw}".[/red]')
        raise typer.Exit(code=1)
    if len(rows) > 1:
        console.print(f'[red]Ambiguous prefix "{raw}" — matches {len(rows)} traces:[/red]')
        for r in rows:
            console.print(f"  {r['id']}  {rich_escape(r['task'] or '')}")
        console.print("[yellow]Use a longer prefix or the full UUID.[/yellow]")
        raise typer.Exit(code=1)
    return UUID(str(rows[0]["id"]))


async def _query_trace_prefix(prefix: str) -> list[dict[str, Any]]:
    async with get_engine().connect() as conn:
        result = await conn.execute(select_trace_by_id_prefix(prefix))
        return [dict(row._mapping) for row in result]


def _append_comparison(body: Text, row: dict[str, Any], outcome: str) -> None:
    """Append the claimed/actual comparison section to body text."""
    claimed_raw = row.get("claimed_value")
    pairs: list[dict[str, Any]] = []
    if claimed_raw:
        try:
            pairs = json.loads(claimed_raw) if isinstance(claimed_raw, str) else claimed_raw
        except (json.JSONDecodeError, TypeError):
            pairs = []

    if not pairs or not isinstance(pairs, list):
        return

    if outcome == "PASS":
        body.append("  ✓ Verified Values\n", style=green)
        for p in pairs:
            path = rich_escape(str(p.get("path", "?")))
            val = rich_escape(str(p.get("value", "?")))
            body.append(f"    {path}: {val}\n", style=green)

    elif outcome == "CAUGHT":
        actual = extract_actual(row.get("raw_response"), claimed_raw)
        body.append("  ✗ Claimed\n", style=red)
        for p in pairs:
            path = rich_escape(str(p.get("path", "?")))
            val = rich_escape(str(p.get("value", "?")))
            body.append(f"    {path}: {val}\n", style=red)
        body.append("  ✓ Actual\n", style=green)
        for p in pairs:
            path = rich_escape(str(p.get("path", "?")))
            val = rich_escape(str(actual.get(p.get("path", "?"), "N/A")))
            body.append(f"    {path}: {val}\n", style=green)

    details = row.get("details")
    if details and outcome in ("CAUGHT", "ERROR"):
        sym = "✗" if outcome == "CAUGHT" else "⚠"
        body.append(f"\n  {sym} {details}\n", style=_outcome_style(outcome))


def _append_secondary(body: Text, qdata: dict[str, Any] | None) -> None:
    """Append dimmed SQL / Proof / Result below a claim card body."""
    if not qdata:
        return
    body.append("\n  ── Query Details ──\n", style="dim")

    sql = rich_escape(qdata.get("sql_query") or "N/A")
    body.append("  SQL:    ", style="dim")
    body.append_text(Text(sql, style="dim", no_wrap=False))
    body.append("\n")

    proof = qdata.get("proof")
    if isinstance(proof, dict):
        body.append(f"  Proof:  {_proof_summary(proof)}\n", style="dim")
    elif proof is not None:
        body.append("  Proof:  ", style="dim")
        body.append_text(Text(rich_escape(str(proof)), style="dim", no_wrap=False))
        body.append("\n")
    else:
        body.append("  Proof:  N/A\n", style="dim")

    result_raw = qdata.get("result")
    if result_raw is not None:
        try:
            result_val = QueryAnswer.model_validate(result_raw).flatten()
        except Exception:
            result_val = result_raw
        body.append("  Result:\n", style="dim")
        body.append_text(Text(_pretty_json(result_val), style="dim", no_wrap=False))
        body.append("\n")
    else:
        body.append("  Result: N/A\n", style="dim")


def _wrap_proof(
    trace_id: str,
    intercept_id: str,
    action_name: str,
    intercept_num: int,
    proof_bytes: bytes,
) -> dict[str, Any]:
    """Wrap proof bytes in a JSON envelope with trace metadata."""
    envelope: dict[str, Any] = {
        "trace_id": trace_id,
        "intercept_id": intercept_id,
        "action_name": action_name,
        "intercept_num": intercept_num,
    }
    try:
        envelope["proof"] = json.loads(proof_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        envelope["proof_base64"] = base64.b64encode(proof_bytes).decode()
    return envelope


def _proof_summary(proof: dict[str, Any]) -> str:
    status = rich_escape(str(proof.get("status", "N/A")))
    verified = rich_escape(str(proof.get("verification_status", "N/A")))
    exec_ms = rich_escape(str(proof.get("execution_time_ms", "?")))
    return (
        f"\n             Status:     {status}"
        f"\n             Verified:   {verified}"
        f"\n             Exec time:  {exec_ms}ms"
    )


def _pretty_json(data: Any, max_lines: int = _JSON_LINES) -> str:
    text = json.dumps(data, indent=2, default=str)
    lines = text.splitlines()
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + "\n             …"
    return text


async def _fetch_traces(limit: int, offset: int = 0) -> list[dict[str, Any]]:
    async with get_engine().connect() as conn:
        result = await conn.execute(select_traces_with_intercept_count(limit=limit, offset=offset))
        return [dict(row._mapping) for row in result]


async def _fetch_trace_detail(trace_id: UUID) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    async with get_engine().connect() as conn:
        t = await conn.execute(select_trace_by_id(trace_id))
        trace_row = t.fetchone()
        if not trace_row:
            return None, []
        ti = await conn.execute(select_trace_intercepts_by_trace_id(trace_id))
        return dict(trace_row._mapping), [dict(row._mapping) for row in ti]


async def _fetch_queries(query_ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
    async def _get(qid: UUID) -> tuple[UUID, dict[str, Any] | None]:
        try:
            return qid, await service.get_query(qid)
        except Exception:
            return qid, None

    results = await asyncio.gather(*(_get(qid) for qid in query_ids))
    return {qid: data for qid, data in results if data is not None}


async def _download_proof(proof_id: UUID) -> bytes:
    return await service.get_query_proof(proof_id)
