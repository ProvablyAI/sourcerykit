# CONTEXT — `provably-sdk` (agent contract)

Human-facing setup: **`README.md`**. **This file** is for anyone (or any agent)
changing behavior in this SDK: what must stay true, where code lives, and how
pieces talk. Prefer editing code over guessing.

## Scope (locked for v0.1)

The SDK ships **five pillars and only five**:

1. **`init`** — one-time runtime bootstrap (`provably.handoff.client.initialize_runtime`).
2. **`intercept`** — global `requests` / `httpx` monkey-patch + storage of
   intercepted rows + simulation hook.
3. **`handoff`** — Pydantic `HandoffPayload` v2 + JSON transport
   (`post_handoff`).
4. **`eval`** — deterministic evaluator (`evaluate_handoff`) with four
   verification modes.
5. **`trusted_endpoints`** — registry DDL, normalization, and the policy edge.

Anything outside these five is **out of scope** for the SDK and lives in
consumer repos. In particular: agent orchestration (LangGraph, OpenAI Agents,
etc.), web servers (FastAPI / Flask), dashboards, deployment configuration,
and demo audit trails.

## Repository shape

```
provably-python-sdk/
  pyproject.toml            name="provably-sdk", import path="provably", src layout
  README.md                 install + quickstart + public surface
  CONTEXT.md                this file
  CHANGELOG.md
  LICENSE.md
  src/provably/
    __init__.py             public surface; only re-exports the documented API
    log.py                  structlog wrapper used SDK-internally
    common/env.py           env-var helpers
    trusted_endpoints.py    registry DDL + normalization + policy check
    intercept/              global requests/httpx monkey-patch + storage
    handoff/                types, transport, evaluator, eval modes, bootstrap
  tests/
    conftest.py             docs the two-layer setup
    unit/                   fast, hermetic; mocks for httpx + psycopg2
    e2e/                    real loopback http.server; real requests + httpx
  docs/                     architecture, per-pillar deep dives, historical plans
  .github/workflows/        ci.yml (active, runs lint + tests + docker), publish.yml (manual stub)
  Dockerfile                multi-stage: builder → test → runtime
  docker-compose.yml        sdk container + Postgres for integration tests
  .dockerignore
```

## Dependency rules

| What is allowed in `src/provably/` | What is forbidden |
|---|---|
| stdlib | `fastapi`, `flask`, any web framework |
| `httpx`, `requests` | `langgraph`, `langchain`, `crewai`, `autogen` |
| `pydantic`, `jsonschema` | `openai`, `anthropic`, any LLM-vendor SDK |
| `psycopg2-binary` (v0.1 only — see issue #1) | `uvicorn`, `gunicorn`, any server |
| `structlog` | `python-dotenv`, app-level config helpers |

CI should fail any PR that adds a forbidden import to `src/provably/`. Until a
ruff rule is configured, a `grep -R "from fastapi\|import langgraph\|import openai\|import anthropic"
src/` check is sufficient.

## Public surface

The contract lives in `src/provably/__init__.py`. **Everything in `__all__` is a
public API and changing its signature is a breaking change.** Anything that
starts with an underscore, or any module imported via `from provably.handoff._x`
etc., is internal and may change without notice.

When adding a new public symbol:

1. Define it in the relevant subpackage.
2. Re-export it from `src/provably/__init__.py` and add it to `__all__`.
3. Document it in `README.md` (and the relevant `docs/<pillar>.md`).
4. Add at least one unit test and, where the symbol crosses an I/O boundary,
   one e2e test.
5. Add a `CHANGELOG.md` entry under the next unreleased version.

## I/O boundaries (memorize these)

The SDK touches the outside world in exactly four places. Every external call
must go through one of them. Adding a fifth is a design decision, not an
implementation detail.

| Module | What it does | How |
|---|---|---|
| `provably.intercept._storage` | Insert into `provably_intercepts` | `psycopg2.connect(POSTGRES_URL)` |
| `provably.trusted_endpoints` | Read / write `trusted_endpoints` table | `psycopg2.connect(POSTGRES_URL)` (in `check_claim_endpoints_are_trusted`); caller-provided `conn` elsewhere |
| `provably.handoff._preprocess` | One-time intercept-table padding at startup | `psycopg2.connect(POSTGRES_URL)` |
| `provably.handoff.evaluator` + `provably.handoff.transport` + `provably.handoff._bootstrap` | All HTTP egress | `httpx.Client` / `httpx.post` |

The interceptor monkey-patches `requests` and `httpx` for everyone *else* in
the process; SDK-internal HTTP calls always use `httpx` directly so they are
not double-counted.

## Configuration contract (v0.1)

The SDK reads from environment variables only. The full set is documented in
`README.md`. Changing this contract — adding, removing, or renaming a variable
the SDK reads — is a breaking change.

The v0.2 plan is to introduce a typed `Provably(...)` client that owns this
configuration explicitly (issue #2). When that lands, the env-var path should
remain functional via a default singleton.

## Test boundary (strict)

`tests/unit/` is the fast inner loop. It must:

- Run in under one second total.
- Use no real Postgres connection.
- Use no real network sockets.
- Mock at the `httpx.Client` / `psycopg2.connection` boundary, not deeper.

`tests/e2e/` is the contract layer. It must:

- Drive the **real** monkey-patched `requests` and `httpx` against a real
  loopback `http.server`.
- Patch only the storage layer (`provably.intercept.interceptor._insert_row`)
  to keep the suite Postgres-free.
- Stay deterministic: no real DNS, no public network, no time-dependent
  assertions.

A new pillar without at least one unit test **and** one e2e test is not
considered done.

## Docker

The repo is dockerised so any contributor (or CI) can reproduce the test
matrix without a local Python toolchain.

- **`Dockerfile`** — three stages:
  - `builder` builds the wheel/sdist from `src/` into `/dist`.
  - `test` installs the wheel + dev tools and defaults to `ruff check && pytest -q`.
  - `runtime` is a slim image with only the wheel installed, suitable as a
    base for services that consume the SDK.
- **`docker-compose.yml`** — pairs the `test` image with a Postgres 16
  service (`db`) and wires `POSTGRES_URL` into the `sdk` container, so
  future integration tests that exercise the real psycopg2 path can use it
  without extra plumbing.
- **CI** — `.github/workflows/ci.yml` has a `docker` job that builds both
  `test` and `runtime` targets and runs them, so the Docker layout cannot
  silently rot.

If you change `pyproject.toml` (deps, optional extras, name, license,
build-system), bump the Docker layer that copies that file and run
`docker run --rm provably-sdk:test` locally before pushing.

## When you are about to break things

- **Removing or renaming a public symbol** — bump the minor version and add a
  deprecation shim under the old name. Document the migration in
  `CHANGELOG.md`.
- **Changing the wire format of `HandoffPayload`** — bump
  `handoff_contract_version` (currently `"2.0"`) and document both versions
  during the transition.
- **Adding a Postgres dependency to a new module** — don't. Open an issue
  blocked on #1; v0.2 inverts this so callers pass a connection in.
- **Adding an LLM SDK dependency** — also don't. The SDK stays vendor-neutral.

## Out of scope

- Agent frameworks. The SDK has zero awareness of LangGraph nodes, OpenAI
  Agents, CrewAI roles, etc. Consumers wire those up themselves.
- Dashboards, runners, simulation orchestrators. These belong to the consumer
  monorepo (e.g.
  [`verifiable-state-demo`](https://github.com/ProvablyAI/verifiable-state-demo)).
- Demo-only audit trails. The `demo_audit` table lives in the consumer
  monorepo (`agents/pipeline/demo_audit.py`), not in this SDK.

## Long-form history

See [`docs/historical-plans/`](docs/historical-plans/) — in particular
[`split-from-monorepo.md`](docs/historical-plans/split-from-monorepo.md), which
records why this SDK was carved out of the demo monorepo and what was
deliberately left behind.
