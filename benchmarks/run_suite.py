#!/usr/bin/env python3
"""Microbenchmark suite for provably-sdk hot paths (no Postgres, no network).

Run from repo root:
  uv run python benchmarks/run_suite.py
  uv run python benchmarks/run_suite.py --out benchmarks/results/abc1234.json

Output is JSON for diffing across branches/commits.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

# Repo root / src on path when executed as `python benchmarks/run_suite.py`
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from provably.handoff import eval_modes  # noqa: E402
from provably.handoff import evaluator as handoff_evaluator  # noqa: E402
from provably.handoff import json_utils  # noqa: E402
from provably.handoff.types import HandoffClaim  # noqa: E402
from provably.intercept import interceptor  # noqa: E402
from provably import trusted_endpoints  # noqa: E402


def _git_ref() -> str:
    if os.environ.get("PERF_GIT_REF"):
        return os.environ["PERF_GIT_REF"].strip()
    try:
        return subprocess.check_output(
            ["git", "-C", str(_ROOT), "describe", "--always", "--dirty"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _median_ns(fn: Callable[[], Any], *, iters: int, repeats: int = 5) -> float:
    samples: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter_ns()
        for _ in range(iters):
            fn()
        samples.append((time.perf_counter_ns() - t0) / iters)
    return float(statistics.median(samples))


def _bench(name: str, fn: Callable[[], Any], *, iters: int, repeats: int = 5) -> dict[str, Any]:
    return {
        "name": name,
        "median_ns_per_call": round(_median_ns(fn, iters=iters, repeats=repeats), 3),
        "iters": iters,
        "repeats": repeats,
    }


def _fake_response(body: object) -> object:
    class _R:
        def __init__(self, b: object) -> None:
            self._b = b

        def json(self) -> object:
            return self._b

        @property
        def text(self) -> str:
            return json.dumps(self._b)

    return _R(body)


def run_all() -> dict[str, Any]:
    small = {"id": 1, "name": "Acme", "ok": True}
    medium = {
        "items": [{"sku": f"x{i:04d}", "qty": i, "price": i * 1.5} for i in range(50)],
        "meta": {"page": 1, "total": 50, "tags": ["a", "b", "c"]},
    }
    url = "https://api.example.com/v1/foo"
    fake = _fake_response(small)

    schema = {
        "type": "object",
        "properties": {
            "page": {"type": "integer"},
            "total": {"type": "integer"},
        },
        "required": ["page", "total"],
    }
    claim_verbatim = HandoffClaim(action_name="v", claimed_value=medium, verification_mode="verbatim")
    claim_field = HandoffClaim(
        action_name="f",
        claimed_value=50,
        json_path="$.meta.total",
        verification_mode="field_extraction",
    )
    claim_schema = HandoffClaim(
        action_name="s",
        claimed_value={"page": 1, "total": 50},
        json_path="$.meta",
        expected_json_schema=schema,
        verification_mode="schema_type",
    )
    claim_range = HandoffClaim(
        action_name="r",
        claimed_value=50,
        json_path="$.meta.total",
        range_min=0,
        range_max=100,
        verification_mode="range_threshold",
    )
    record: dict[str, Any] = {
        "query": {
            "result": {
                "type": "resultset",
                "value": {
                    "columns": [{"name": "raw_response"}],
                    "rows": [[json.dumps(medium)]],
                },
            },
            "proof": {"execution_time_ms": 12.3, "verification_time_ms": 4.5},
        }
    }

    benches: list[dict[str, Any]] = []

    benches.append(
        _bench(
            "normalize_url_for_trust",
            lambda: trusted_endpoints.normalize_url_for_trust(url),
            iters=20_000,
        )
    )
    benches.append(
        _bench(
            "canonical_json_small",
            lambda: json_utils.canonical_json(small),
            iters=20_000,
        )
    )
    benches.append(
        _bench(
            "canonical_json_medium",
            lambda: json_utils.canonical_json(medium),
            iters=10_000,
        )
    )
    benches.append(
        _bench(
            "evaluate_claim_verbatim",
            lambda: eval_modes.evaluate_claim(claim_verbatim, medium),
            iters=3_000,
        )
    )
    benches.append(
        _bench(
            "evaluate_claim_field_extraction",
            lambda: eval_modes.evaluate_claim(claim_field, medium),
            iters=5_000,
        )
    )
    benches.append(
        _bench(
            "evaluate_claim_schema_type",
            lambda: eval_modes.evaluate_claim(claim_schema, medium),
            iters=1_000,
        )
    )
    benches.append(
        _bench(
            "evaluate_claim_range_threshold",
            lambda: eval_modes.evaluate_claim(claim_range, medium),
            iters=5_000,
        )
    )
    benches.append(
        _bench(
            "extract_indexed_from_query_record",
            lambda: handoff_evaluator.extract_indexed_from_query_record(record),
            iters=15_000,
        )
    )

    # Interceptor path without DB: patch _insert_row to no-op, disable recording gate for insert.
    saved_enabled = interceptor._enabled
    saved_allowlist = interceptor._url_allowlist
    saved_hook = interceptor._intercept_body_hook
    interceptor._enabled = False
    interceptor._url_allowlist = None
    interceptor._intercept_body_hook = None

    def _attach_once() -> None:
        interceptor._attach(fake, url, "GET", {})

    try:
        benches.append(_bench("interceptor_attach_no_db", _attach_once, iters=30_000))
    finally:
        interceptor._enabled = saved_enabled
        interceptor._url_allowlist = saved_allowlist
        interceptor._intercept_body_hook = saved_hook

    return {
        "schema_version": 1,
        "scenario": "cpu_hotpaths_v1",
        "git_ref": _git_ref(),
        "python": os.environ.get("PERF_PYTHON", sys.version.split()[0]),
        "platform": platform.platform(),
        "benchmarks": benches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        help="Write JSON results to this path (parent dirs created).",
    )
    args = parser.parse_args()
    payload = run_all()
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    sys.stdout.write(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
