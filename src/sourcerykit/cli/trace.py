import asyncio
import base64
import json
from pathlib import Path
from typing import Any
from uuid import UUID

import typer
from rich.table import Table

from sourcerykit.cli.utils import console, require_settings
from sourcerykit.db._engine import get_engine
from sourcerykit.db._traces import (
    select_trace_by_id,
    select_trace_intercepts_by_trace_id,
    select_traces_with_intercept_count,
)
from sourcerykit.provably._answer_model import QueryAnswer
from sourcerykit.provably.service import service

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
            str(r["id"]),
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
    save_proof: bool = typer.Option(False, "--save-proof", help="download and save proofs to .provably files"),
) -> None:
    """Show details of a single trace and its intercepts."""
    require_settings()
    trace_id = UUID(id)
    trace_row, intercept_rows = asyncio.run(_fetch_trace_detail(trace_id))

    if not trace_row:
        console.print(f"[red]Trace {id} not found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold]Trace[/bold] {trace_row['id']}")
    console.print(f"  Task:    {trace_row['task']}")
    console.print(f"  Created: {trace_row['created_at']}")

    if not intercept_rows:
        console.print("\n[yellow]No intercepts.[/yellow]")
        return

    query_ids = [r["query_id"] for r in intercept_rows]
    queries = asyncio.run(_fetch_queries(query_ids))

    table = Table(title="Intercepts")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Action", style="cyan")
    table.add_column("Source", style="white")
    table.add_column("Mode", style="white")
    table.add_column("Claimed", style="white")
    table.add_column("Outcome")

    for i, row in enumerate(intercept_rows, 1):
        outcome = row["outcome"] or ""
        outcome_style = {"PASS": "green", "CAUGHT": "red", "ERROR": "yellow"}.get(outcome, "white")
        table.add_row(
            str(i),
            row["action_name"],
            row["source_url"],
            row["verification_mode"],
            row["claimed_value"] or "",
            f"[{outcome_style}]{outcome}[/{outcome_style}]",
        )

    console.print(table)

    for i, (row, qid) in enumerate(zip(intercept_rows, query_ids), 1):
        qdata = queries.get(qid)
        _print_intercept_detail(i, row, qdata)

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
                    console.print(f"             [green]Saved to {filename}[/green]")
        elif qdata:
            proof = qdata.get("proof")
            if isinstance(proof, dict):
                console.print("             [dim]Run with --save-proof to download the full proof.[/dim]")


# --- Helpers ---
def _print_intercept_detail(i: int, row: dict[str, Any], qdata: dict[str, Any] | None) -> None:
    """Print intercept detail block."""
    outcome = row["outcome"] or ""
    outcome_style = {"PASS": "green", "CAUGHT": "red", "ERROR": "yellow"}.get(outcome, "white")
    console.print(f"\n  [dim]{i}.[/dim] {row['action_name']} → [{outcome_style}]{outcome}[/{outcome_style}]")

    if not qdata:
        console.print("     SQL:    [dim]N/A[/dim]")
        console.print("     Proof:  [dim]N/A[/dim]")
        console.print("     Result: [dim]N/A[/dim]")
        return

    sql = qdata.get("sql_query") or ""
    console.print(f"     SQL:    {sql}")

    proof = qdata.get("proof")
    if isinstance(proof, dict):
        console.print(f"     Proof:  {_proof_summary(proof)}")
    elif proof is not None:
        console.print(f"     Proof:  {proof}")
    else:
        console.print("     Proof:  [dim]N/A[/dim]")

    result_raw = qdata.get("result")
    if result_raw is not None:
        try:
            result_val = QueryAnswer.model_validate(result_raw).flatten()
        except Exception:
            result_val = result_raw
        console.print(f"     Result: {_pretty_json(result_val)}")
    else:
        console.print("     Result: [dim]N/A[/dim]")


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
    status = proof.get("status", "N/A")
    verified = proof.get("verification_status", "N/A")
    exec_ms = proof.get("execution_time_ms", "?")
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
