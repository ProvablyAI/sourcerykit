---
name: Split provably_package out of the verifiable-state-demo monorepo
overview: "Carve `provably_package/` out of the `verifiable-state-demo` monorepo into this standalone repository (intended PyPI distribution: `provably-sdk`, import path: `provably`). The monorepo became a consumer of the SDK via a local editable install; PyPI publish is pending. Scope was intentionally lean: init, intercept, handoff, evaluator, trusted endpoints."
status: executed
---

## Outcome

The SDK is now a separate git repository
([`ProvablyAI/provably-python-sdk`](https://github.com/ProvablyAI/provably-python-sdk))
with `provably-sdk` reserved as its intended PyPI distribution name (publish
pending — see `.github/workflows/publish.yml`). The
[`verifiable-state-demo`](https://github.com/ProvablyAI/verifiable-state-demo)
monorepo declares the dependency as `provably-sdk>=0.1.0,<0.2` and overrides
its source to a local editable path during development:

```toml
# verifiable-state-demo/pyproject.toml
[tool.uv.sources]
provably-sdk = { path = "../provably-python-sdk", editable = true }
```

```
Before                                After
------                                -----
verifiable-state-demo/                verifiable-state-demo/                 provably-python-sdk/
  provably_package/   (in-repo)  ->     (deleted)                              src/provably/
  agents/                               agents/                                tests/
  simulations/                          simulations/                           docs/
  pyproject.toml                        pyproject.toml (depends on             pyproject.toml
                                         provably-sdk>=0.1.0,<0.2)             README.md, CONTEXT.md, CHANGELOG.md
                                                                              .github/workflows/{ci,publish}.yml
```

## What shipped in the SDK (v0.1)

Lean, per the "init + intercept + handoff + eval + trusted endpoints" rule.

- `provably.handoff.client` — `initialize_runtime` (only).
- `provably.intercept` — interceptor + storage + responses (whole subpackage).
- `provably.handoff` — `types`, `transport`, `evaluator`, `eval_modes`,
  `json_utils`, `_bootstrap`, `_discovery`, `_http`, `_preprocess`,
  `_resources`.
- `provably.trusted_endpoints`.
- `provably.log`, `provably.common.env` (internal utilities).

Public surface in `src/provably/__init__.py` re-exports `initialize_runtime`,
`post_handoff`, `evaluate_handoff`, the `Handoff*` types, the intercept
controls, and the trusted-endpoint helpers.

## What stayed in the monorepo

- `demo_audit.py` + `_demo_audit_schema.py` — moved into `agents/pipeline/`
  (demo-only audit-trail; not part of the SDK).
- `validator.py` — deleted (dead code; zero imports anywhere).
- `run_handoff_verification` and `_fetch_source_url` — deleted entirely. The
  proof-generation path is therefore inert in the demo until a replacement is
  built.

## Decisions locked in

- **PyPI name** (intended; publish pending): `provably-sdk`. **Import
  path**: `provably`. Source layout: `src/provably/`.
- **License**: `pyproject.toml` declares `license = { text = "Proprietary" }`.
  `LICENSE.md` was copied from the monorepo's git remote into the new repo
  root.
- **Public-surface trim**: `run_handoff_verification` and `_fetch_source_url`
  removed from `handoff/client.py` and from `__init__.py` re-exports.
- **Config model**: env-vars only for v0.1. A typed `Provably(...)` client is
  a v0.2 issue (#2).
- **SDK dependencies**: `httpx>=0.26`, `requests>=2.31`, `jsonschema>=4.0`,
  `pydantic>=2.6`, `psycopg2-binary>=2.9`, `structlog>=24.1`. No `fastapi`,
  no `langgraph*`, no LLM-vendor SDKs.
- **Test boundary (strict)**: only pure SDK logic (intercept, handoff
  transport, evaluator, trusted endpoints) lives in this repo's test suite.
  LangGraph / simulation / agent-pipeline tests stay in the monorepo. The
  suite is split into `tests/unit/` (mocked, fast) and `tests/e2e/` (real
  loopback HTTP server, real `requests` + `httpx` patches).

## Known tension: psycopg2 / `POSTGRES_URL` in the SDK

Three SDK modules still open Postgres directly in v0.1, so `psycopg2-binary`
and `POSTGRES_URL` had to stay in the SDK surface:

- `provably.intercept._storage` — `_require_trusted_endpoint`, `_write_row`.
- `provably.trusted_endpoints` — `check_claim_endpoints_are_trusted`.
- `provably.handoff._preprocess` — `ensure_preprocess_intercept_padding`.

Issue [#1](https://github.com/ProvablyAI/provably-python-sdk/issues/1) tracks
refactoring these to accept a caller-provided connection (or factory),
making `psycopg2-binary` an optional `[postgres]` extra, and removing
`POSTGRES_URL` from the SDK env surface.

## Monorepo changes (consumer side)

- Deleted `provably_package/`.
- Moved `demo_audit.py` + `_demo_audit_schema.py` into `agents/pipeline/`.
- Rewrote ~25 call sites: `from provably_package... -> from provably...`
  across `agents/`, `simulations/`, `scripts/`, `tests/`, `docs/`.
- Deleted every `run_handoff_verification` call site.
- `pyproject.toml`:
  - Removed `provably_package*` from `[tool.setuptools.packages.find].include`.
  - Removed `jsonschema>=4.0` (no longer used directly by the monorepo).
  - Added `provably-sdk>=0.1.0,<0.2` to `dependencies`.
  - Added a `[tool.uv.sources]` override pointing `provably-sdk` at the
    sibling `provably-python-sdk/` directory (editable). This is what
    actually resolves the dependency until the package is published.
  - Added `[tool.uv.sources] provably-sdk = { path = "../provably-python-sdk", editable = true }`
    for local development.

## Publishing

- First publish = tag `v0.1.0` on this repo. Deferred — local editable path
  dep used in the meantime.
- `publish.yml` is a stub gated on manual `workflow_dispatch`.

## GitHub issues

SDK-scoped issues from the monorepo were re-opened against this repo:

- `#3` Formalize interceptor activation as the last step of `initialize_runtime()`.
- `#4` Intercept index vNext: capture intent and execution context.
- `#5` Intercept index vNext: structured worked / failed feedback.
- `#6` Trusted endpoint registry: schema, enforcement model, cross-org sharing.

Plus two fresh tracking issues:

- `#1` v0.2: DB connection injection — drop `psycopg2-binary` + `POSTGRES_URL` from SDK.
- `#2` v0.2: typed `Provably(...)` client replacing env-var globals.

## Risks / things to watch

- The interceptor monkey-patches global `requests.get/post` + `httpx.get/post`.
  Documented in [`docs/intercept.md`](../intercept.md).
- The SDK must not grow a dep on `fastapi` / `langgraph` — that would defeat
  the whole split. Documented in [`docs/architecture.md`](../architecture.md)
  and [`CONTEXT.md`](../../CONTEXT.md).
- `run_handoff_verification` is deleted entirely (no relocation). The Provably
  proof-generation path is inert in the demo until a replacement is built.
