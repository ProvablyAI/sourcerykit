#!/usr/bin/env python3
"""Compare two JSON outputs from benchmarks/run_suite.py.

Usage:
  uv run python benchmarks/compare.py baseline.json candidate.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"expected object in {path}")
    return data


def _by_name(payload: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for b in payload.get("benchmarks", []):
        if isinstance(b, dict) and "name" in b and "median_ns_per_call" in b:
            out[str(b["name"])] = float(b["median_ns_per_call"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("baseline", type=Path)
    ap.add_argument("candidate", type=Path)
    args = ap.parse_args()

    base = _load(args.baseline)
    cand = _load(args.candidate)
    b_base = _by_name(base)
    b_cand = _by_name(cand)

    names = sorted(set(b_base) | set(b_cand))
    if not names:
        print("no benchmarks to compare", file=sys.stderr)
        return 1

    print(f"baseline:   {base.get('git_ref', '?')}  ({args.baseline})")
    print(f"candidate:  {cand.get('git_ref', '?')}  ({args.candidate})")
    print()
    w = max(len(n) for n in names)
    hdr = f"{'benchmark'.ljust(w)}  {'baseline_ns':>14}  {'candidate_ns':>14}  {'delta_%':>10}"
    print(hdr)
    print("-" * len(hdr))

    for name in names:
        x = b_base.get(name)
        y = b_cand.get(name)
        if x is None or y is None:
            print(f"{name.ljust(w)}  {repr(x):>14}  {repr(y):>14}  {'n/a':>10}")
            continue
        if x == 0:
            delta = 0.0 if y == 0 else float("inf")
        else:
            delta = (y - x) / x * 100.0
        print(f"{name.ljust(w)}  {x:14.1f}  {y:14.1f}  {delta:10.1f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
