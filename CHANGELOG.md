# Changelog

## 1.0.0

Major release following a full repository refactor. The package is now published as **`sourcerykit`**.

### Breaking changes

- **Package renamed** — all imports change from `provably` to `sourcerykit`. (#41)
- **`set_interceptor_context` removed** — replaced by the `intercept_context()` context manager, which correctly scopes the `ContextVar` and prevents leaks across requests. (#41)
- **Database schema redesigned** — `provably_intercepts` and `trusted_endpoints` now use `UUID` primary keys (was `SERIAL`) with updated column types (e.g. `indexed_average` stored as `TEXT`). Run `alembic upgrade head` (migration `000` drops old tables, `001`/`002` recreate them). (#41)

### Architecture & tooling

- **Async architecture** — HTTP client migrated to `httpx` async; database layer upgraded to async SQLAlchemy. (#41)
- **Alembic migrations** — schema changes are managed via versioned Alembic scripts. (#41)
- **Authentication service** — `SourceryKitAuthService` handles account and organisation management against the Provably API. (#41)
- **CLI setup wizard** — interactive `sourcerykit init` command for first-time account, org, and database configuration. (#41)
- **Test coverage gate** — `pytest-cov` enforces a 60 % floor on the unit suite in CI. (#41)

### Examples & onboarding

- **Cookbooks** — runnable examples using Claude Agent SDK, OpenAI Agents SDK and Langchain Agent SDK. (#41)
- **Skill** (`init-sourcerykit`) — step-by-step guided onboarding skill for adding SourceryKit to an existing agent project. (#41)
- **SDK documentation** — full developer docs (Sphinx) covering interception, handoffs, trusted endpoints, and verification modes. (#41)

## 0.2.0

- Added `configure_indexing(enable_indexing)`: one-call bootstrap (`initialize_runtime` + `init_interceptor` + enable/disable) for sender agents.
- Added `outcome_from_trace(trace)` and `aggregate_outcome(payload)` helpers for extracting and rolling up verdicts.
- Added `set_intercept_url_allowlist(urls)` to top-level namespace; scopes the simulation body hook to an explicit set of URLs.
- `Outcome` now includes `"ERROR"` alongside `"PASS"` and `"CAUGHT"`.
- Logging migrated from `print()` to structured `structlog` output.

## 0.1.0

Init.

- `initialize_runtime` for one-time bootstrap.
- `intercept` module: monkey-patches `requests` and `httpx`, records rows in `provably_intercepts`, enforces trusted-endpoint allow-list.
- `handoff` module: `HandoffPayload`, `HandoffClaim`, `post_handoff`, and `evaluate_handoff` with per-claim verification modes (`verbatim`, `field_extraction`, `schema_type`, `range_threshold`).
- `claim_contract` builder: generates the LLM-facing JSON contract from `HandoffClaim` + `VerificationMode`.
- `trusted_endpoints`: `is_trusted_endpoint`, `list_trusted_endpoints`, `check_claim_endpoints_are_trusted`.
