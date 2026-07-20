# Changelog

## Unreleased

### Breaking changes
- **`SourceryKitAgentResponse.reasoning` renamed to `.answer`** — the field, database column, `HandoffPayload`, and all related APIs now use `answer`. Update your agent code, structured output bindings, and any queries against the `traces` table.

### Features
- **Answer field on traces** — `SourceryKitAgentResponse.answer` is stored in the `traces` table (migration `005`) and displayed in both the CLI and UI dashboard.
- **CLI `trace show --ui/--no-ui`** — default opens the interactive dashboard in the browser; `--no-ui` prints the CLI panel output. Trace ID prefixes are accepted (unambiguous prefix resolution).
- **Dashboard activity section** — trace activity log with outcome counts.
- **CLI `upgrade` command** — `sourcerykit upgrade` checks for a newer package version on PyPI, offers to install it, and runs pending database migrations.

### Refactoring
- **CLI `trace show` presentation** — header and summary wrapped in a styled Rich panel.

### Maintenance
- **Alembic migrations shipped with package** — migration scripts are now included in the pip wheel via `force-include`, enabling `sourcerykit upgrade` for non-repo installs.

### Documentation
- Updated CLI docs with `--ui/--no-ui` option.
- Added migration guides (`docs/migrations/`) with README index, expanded v1.0 guide, and updated README migration links.

## 1.0.1

### Bug fixes
- Fix preprocessing edge case — handle new tables by safely catching the 404 Not Found response when no initial preprocessing status record exists yet.

## 1.0.0

### Breaking changes
- **`take_last_intercept_row_id` removed** — `call_ref` is now the sole intercept resolution mechanism.
- **`call_ref` required** — claims without a `call_ref` (or `sourcerykit_ref` in `claimed_value`) now raise.

### Features
- **Multi-tool-call support** — `call_ref` column on `intercepts` + `sourcerykit_ref` on `ClaimedValue` enable correct mapping when the same tool is called multiple times.
- **Auto-grouping** — `build_handoff_payload` splits `claimed_value` entries by `sourcerykit_ref` automatically. No manual grouping or `call_ref` mapping needed.
- **Mock HTTP server** — lightweight test utility for local endpoint testing.

### Bug fixes
- Improved `evaluate_claim` value comparison with JSON parsing for arrays and dicts.

### Refactoring
- Implemented locking mechanism for concurrent preprocessing.
- Updated claim evaluation and error handling for `sourcerykit_ref`.

### Documentation
- Added multi-agent cookbook examples (LangGraph, CrewAI).

## 1.0.0b5

### Tooling
- Improved `make bump-pr` for automated version management

### Documentation
- Added `AGENTS.md`, a landing page for AI agents
- Added `llms.txt`, a web convention entry point that mirrors the `AGENTS.md` pointers
- Added `docs/onboarding.md`, a one-time setup guide

## 1.0.0b4

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
