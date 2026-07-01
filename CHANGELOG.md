# Changelog

## Unreleased

### Tooling
- Integrated `bump-my-version` for automated version management

### Maintenance
- Updated `requests` dependency version in lockfile
- Cleaned up project metadata in `pyproject.toml`
- Updated README badges for PyPI, license, and CI status

## 1.0.0b3

### Non-interactive flags
- Added non-interactive mode to init, feedback, endpoints remove, and config set via new CLI flags (--email, --password, --postgres-url, --project-name, --register, --yes, --description, --attach-file, --api-key)

### Bug fixes
- Fixed missing await on is_endpoint_trusted() when removing endpoints
- Replaced bare raise with SourceryKitTrustError in remove_trusted_endpoint

## 1.0.0b2

### Documentation & Assets
- **Fixed PyPI asset rendering** — Switched logo and architecture diagram links to absolute raw URLs so they render properly on PyPI.
- **Fixed alert block formatting** — Replaced GitHub-specific `> [!IMPORTANT]` tags with standard markdown emojis to prevent broken rendering on PyPI.
- **Updated documentation links** — Added explicit links to `provably.ai/docs`, hands-on cookbooks, and the end-to-end walkthrough guide.


## 1.0.0b1

Major release following a full repository refactor. The package is now published as **`sourcerykit`**.

### Breaking changes

- **Package renamed** — all imports change from `provably` to `sourcerykit`. (#44)
- **`set_interceptor_context` removed** — replaced by the `intercept_context()` context manager, which correctly scopes the `ContextVar` and prevents leaks across requests. (#44)
- **Database schema redesigned** — `provably_intercepts` and `trusted_endpoints` now use `UUID` primary keys (was `SERIAL`) with updated column types (e.g. `indexed_average` stored as `TEXT`). Run `alembic upgrade head` (migration `000` drops old tables, `001`/`002` recreate them). (#44)

### Architecture & tooling

- **Async architecture** — HTTP client migrated to `httpx` async; database layer upgraded to async SQLAlchemy. (#44)
- **Alembic migrations** — schema changes are managed via versioned Alembic scripts. (#44)
- **Authentication service** — `SourceryKitAuthService` handles account and organisation management against the Provably API. (#44)
- **CLI setup wizard** — interactive `sourcerykit init` command for first-time account, org, and database configuration. (#44)
- **Test coverage gate** — `pytest-cov` enforces a 60 % floor on the unit suite in CI. (#44)

### Examples & onboarding

- **Cookbooks** — runnable examples using Claude Agent SDK, OpenAI Agents SDK and Langchain Agent SDK. (#44)
- **Skill** (`init-sourcerykit`) — step-by-step guided onboarding skill for adding SourceryKit to an existing agent project. (#44)
- **SDK documentation** — full developer docs (Sphinx) covering interception, handoffs, trusted endpoints, and verification modes. (#44)

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
