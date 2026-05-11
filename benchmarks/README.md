# SDK performance: branch workflow and recording

This folder defines **how** to land perf work in small reviewable slices, **measure** each change against a fixed baseline, and **record** numbers so regressions are visible later.

## Principles

1. **One theme per branch** — easier review, bisect, and revert.
2. **Baseline before changes** — tag or JSON snapshot on `main` (or your integration branch) so every PR can say “vs baseline X”.
3. **Same harness everywhere** — `run_suite.py` outputs JSON; `compare.py` prints deltas. No ad-hoc `timeit` in chat.
4. **Record in two places** — machine JSON (artifacts, optional commits) + human summary in the PR (table or pasted `compare` output).

## Suggested git branches

Create branches from a common baseline (e.g. `main` at tag `perf/baseline-YYYY-MM-DD` or commit SHA).

| Branch name (example) | Change theme |
|----------------------|--------------|
| `perf/baseline-record` | No code change: only run `run_suite.py`, save `results/baseline-<sha>.json`, open PR with numbers (optional). |
| `perf/eval-jsonschema-cache` | Cache `Draft202012Validator` (or equivalent) in `schema_type` path — largest CPU win on eval. |
| `perf/eval-canonical-dedup` | Reuse `canonical_json` results in `eval_modes` (`_base_verdict` + mode-specific compare). |
| `perf/intercept-skip-normalize` | Skip `normalize_url_for_trust` when URL allowlist is unset; optional `lru_cache` on normalize. |
| `perf/intercept-hash-single-dumps` | Single `json.dumps(..., sort_keys=True)` for hash + row in `_storage._write_row`. |
| `perf/db-connection-pool` | Pool or shared connection for trust check + insert (requires care with threads). |
| `perf/preprocess-async` | Move `preprocess_after_intercept_write` off the hot path (queue + debounce). |

Merge order: start with **pure CPU / no behavior risk** (`canonical` dedup, `normalize` skip, single `dumps`), then **jsonschema cache**, then **I/O architecture** (pool, async preprocess). Each merge to `main` (or `develop`) re-runs the suite and updates the “current” snapshot.

## How to measure

From the repo root, with the package installed (so `structlog`, `httpx`, etc. resolve):

```bash
uv sync --extra dev
uv run python benchmarks/run_suite.py --out benchmarks/results/$(git rev-parse --short HEAD).json
```

Without `uv`:

```bash
python3.11 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python benchmarks/run_suite.py --out benchmarks/results/$(git rev-parse --short HEAD).json
```

Or without writing a file:

```bash
uv run python benchmarks/run_suite.py | tee /tmp/perf.json
```

Compare two runs (baseline first argument, candidate second):

```bash
uv run python benchmarks/compare.py benchmarks/results/abc1234.json benchmarks/results/def5678.json
```

Environment variables (optional, for stable CI):

- `PERF_GIT_REF` — override ref string embedded in JSON (default: `git describe --always`).
- `PERF_PYTHON` — override Python version label in JSON.

## What the suite covers

`run_suite.py` measures **CPU-only** hot paths that do not need Postgres or the Provably API:

- `trusted_endpoints.normalize_url_for_trust`
- `intercept._attach` / `_record_and_maybe_tamper` (DB and insert patched out)
- `handoff.json_utils.canonical_json` on small/medium payloads
- `handoff.eval_modes.evaluate_claim` for verbatim / field_extraction / schema_type / range_threshold
- `handoff.evaluator.extract_indexed_from_query_record` (fixture)

It does **not** replace profiling for DB connect time or network polling; for those, add a separate scenario (e.g. Docker Compose + `pytest-benchmark` or a script that times N intercepts against a local Postgres) and store results in the same `results/` naming scheme with a `scenario` field in the JSON (extend the runner when you add that).

## Recording improvements

1. **Before** a change: save `results/baseline-<shortsha>.json` (or attach to ticket).
2. **After** each branch: save `results/<shortsha>-<branch-slug>.json`.
3. In the PR description, paste the output of `compare.py baseline.json candidate.json`.
4. Optionally add a row to `benchmarks/CHANGELOG-PERF.md` (date, branch, key metric deltas).

Committed JSON under `results/` is optional; many teams only attach artifacts on the PR. If you do commit, prefer **tagged baselines** (`baseline-v1.json`) over every commit.

## CI (optional)

`.github/workflows/benchmarks.yml` runs on `workflow_dispatch` and uploads `perf-*.json` as a workflow artifact so you can download and compare without a local machine.

## Reducing measurement noise

Microbenchmarks fluctuate with CPU frequency, background load, and thermal state. For PRs:

- Run baseline and candidate **back-to-back** on the same machine.
- Treat **changes under about 5%** on small benchmarks as noise unless repeated.
- For contentious changes, run the suite **three times** per side and compare medians of the medians (or use a dedicated bench host / CI artifact).

## Extending the suite

When you optimize a new path:

1. Add a named benchmark in `run_suite.py` (`BENCHMARKS` dict or similar).
2. Document expected direction (faster/slower) in the PR.
3. If behavior could change, add or extend **unit tests** in `tests/` — perf branches must not weaken correctness.
