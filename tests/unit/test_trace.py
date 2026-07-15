"""Tests for sourcerykit.cli.trace."""

import json
import uuid
from unittest.mock import patch

import pytest
import typer

from sourcerykit.cli.trace import (
    _pretty_json,
    _proof_summary,
    _resolve_trace_id,
    _wrap_proof,
    list_traces,
    show,
)

_TRACE_ID = uuid.uuid4()
_INTERCEPT_ID = uuid.uuid4()
_QUERY_ID = uuid.uuid4()


def _make_trace_row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": _TRACE_ID,
        "task": "test-task",
        "reasoning": "",
        "created_at": "2026-01-01T00:00:00",
        "pass": 1,
        "caught": 0,
        "error": 0,
    }
    base.update(overrides)
    return base


def _make_intercept_row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": _INTERCEPT_ID,
        "query_id": _QUERY_ID,
        "verification_mode": "hash",
        "claimed_value": "42",
        "outcome": "PASS",
        "details": "ok",
        "created_at": "2026-01-01T00:00:01",
        "action_name": "insert",
        "source_url": "https://example.com",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# list_traces
# ---------------------------------------------------------------------------


class TestListTraces:
    def test_empty(self) -> None:
        with (
            patch("sourcerykit.cli.trace.require_settings"),
            patch("sourcerykit.cli.trace.asyncio.run", return_value=[]),
            patch("sourcerykit.cli.trace.console") as mock_console,
        ):
            list_traces(limit=20, page=1)
        mock_console.print.assert_called_once()
        assert "No traces" in str(mock_console.print.call_args)

    def test_with_rows(self) -> None:
        rows = [_make_trace_row()]
        with (
            patch("sourcerykit.cli.trace.require_settings"),
            patch("sourcerykit.cli.trace.asyncio.run", return_value=rows),
            patch("sourcerykit.cli.trace.console") as mock_console,
        ):
            list_traces(limit=20, page=1)
        mock_console.print.assert_called_once()

    def test_pagination_offset(self) -> None:
        with (
            patch("sourcerykit.cli.trace.require_settings"),
            patch("sourcerykit.cli.trace.asyncio.run", return_value=[]) as mock_run,
            patch("sourcerykit.cli.trace.console"),
        ):
            list_traces(limit=10, page=3)
        mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


class TestShow:
    def test_not_found(self) -> None:
        with (
            patch("sourcerykit.cli.trace.require_settings"),
            patch("sourcerykit.cli.trace.asyncio.run", return_value=(None, [])),
            patch("sourcerykit.cli.trace.console") as mock_console,
        ):
            with pytest.raises(typer.Exit):
                show(id=str(_TRACE_ID), ui=False)
        assert "not found" in str(mock_console.print.call_args).lower()

    def test_no_intercepts(self) -> None:
        trace_row = _make_trace_row()
        with (
            patch("sourcerykit.cli.trace.require_settings"),
            patch("sourcerykit.cli.trace.asyncio.run", return_value=(trace_row, [])),
            patch("sourcerykit.cli.trace.console") as mock_console,
        ):
            show(id=str(_TRACE_ID), ui=False)
        assert any("No intercepts" in str(c) for c in mock_console.print.call_args_list)

    def test_with_intercepts(self) -> None:
        trace_row = _make_trace_row()
        intercept_row = _make_intercept_row()
        with (
            patch("sourcerykit.cli.trace.require_settings"),
            patch("sourcerykit.cli.trace.asyncio.run") as mock_run,
            patch("sourcerykit.cli.trace.console"),
        ):
            mock_run.side_effect = [
                (trace_row, [intercept_row]),
                {_QUERY_ID: {"sql_query": "SELECT 1", "proof": None, "result": None}},
            ]
            show(id=str(_TRACE_ID), ui=False)

    def test_reasoning_printed_when_present(self) -> None:
        trace_row = _make_trace_row(reasoning="because reasons")
        with (
            patch("sourcerykit.cli.trace.require_settings"),
            patch("sourcerykit.cli.trace.asyncio.run", return_value=(trace_row, [])),
            patch("sourcerykit.cli.trace.console") as mock_console,
        ):
            show(id=str(_TRACE_ID), ui=False)
        printed = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "because reasons" in printed

    def test_invalid_uuid(self) -> None:
        with (
            patch("sourcerykit.cli.trace.require_settings"),
            patch("sourcerykit.cli.trace._resolve_trace_id", side_effect=typer.Exit(code=1)),
            patch("sourcerykit.cli.trace.console"),
        ):
            with pytest.raises(typer.Exit):
                show(id="not-a-uuid", ui=False)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class TestWrapProof:
    def test_json_proof(self) -> None:
        proof_bytes = b'{"status": "ok"}'
        result = _wrap_proof(
            trace_id="t1",
            intercept_id="i1",
            action_name="insert",
            intercept_num=1,
            proof_bytes=proof_bytes,
        )
        assert result["proof"] == {"status": "ok"}
        assert result["trace_id"] == "t1"

    def test_binary_proof(self) -> None:
        proof_bytes = b"\x00\x01\x02"
        result = _wrap_proof(
            trace_id="t1",
            intercept_id="i1",
            action_name="insert",
            intercept_num=1,
            proof_bytes=proof_bytes,
        )
        assert "proof_base64" in result
        assert "proof" not in result


class TestProofSummary:
    def test_full(self) -> None:
        proof = {"status": "verified", "verification_status": "PASS", "execution_time_ms": 42}
        s = _proof_summary(proof)
        assert "verified" in s
        assert "PASS" in s
        assert "42" in s

    def test_missing_keys(self) -> None:
        s = _proof_summary({})
        assert "N/A" in s


class TestPrettyJson:
    def test_short(self) -> None:
        assert _pretty_json({"a": 1}) == json.dumps({"a": 1}, indent=2)

    def test_truncated(self) -> None:
        big = {f"k{i}": i for i in range(100)}
        result = _pretty_json(big, max_lines=5)
        assert "…" in result


# ---------------------------------------------------------------------------
# _resolve_trace_id
# ---------------------------------------------------------------------------


class TestResolveTraceId:
    def test_full_uuid(self) -> None:
        result = _resolve_trace_id(str(_TRACE_ID))
        assert result == _TRACE_ID

    def test_prefix_single_match(self) -> None:
        prefix = str(_TRACE_ID)[:8]
        row = {"id": _TRACE_ID, "task": "t", "reasoning": "", "created_at": "2026-01-01"}
        with patch("sourcerykit.cli.trace.asyncio.run", return_value=[row]):
            result = _resolve_trace_id(prefix)
        assert result == _TRACE_ID

    def test_prefix_no_match(self) -> None:
        with (
            patch("sourcerykit.cli.trace.asyncio.run", return_value=[]),
            patch("sourcerykit.cli.trace.console"),
        ):
            with pytest.raises(typer.Exit):
                _resolve_trace_id("deadbeef")

    def test_prefix_ambiguous(self) -> None:
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        prefix = str(id1)[:8]
        rows = [
            {"id": id1, "task": "a", "reasoning": "", "created_at": "2026-01-01"},
            {"id": id2, "task": "b", "reasoning": "", "created_at": "2026-01-02"},
        ]
        with (
            patch("sourcerykit.cli.trace.asyncio.run", return_value=rows),
            patch("sourcerykit.cli.trace.console") as mock_console,
        ):
            with pytest.raises(typer.Exit):
                _resolve_trace_id(prefix)
        printed = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert str(id1) in printed
        assert str(id2) in printed
