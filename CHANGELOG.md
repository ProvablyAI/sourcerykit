# Changelog

## 0.3.0

### OpenAI Agents SDK integration

- Added `examples/openai_agents/` — a runnable end-to-end demo that drives a
  real OpenRouter model call through the full Provably intercept → handoff →
  evaluate pipeline.  Model: `openai/gpt-4o-mini` (~$0.001/run); data API:
  Open-Meteo (no auth required).
- Added `tests/e2e/test_openai_agents_e2e.py` — six deterministic scenarios
  (A–F) using in-process `FakeHttpServer`s; zero network egress in CI.

### Broader HTTP interception surface

- `httpx.Client.send`, `httpx.AsyncClient.send`, and `requests.Session.send`
  are now patched in addition to the existing module-level shortcuts
  (`httpx.get`, `httpx.post`, `requests.get`, `requests.post`).  This means
  every outbound HTTP call from any framework — including the async agent loops
  used by the OpenAI Agents SDK — is intercepted without any user-side changes.
- A re-entry contextvar guard (`_reentry.already_recording`) prevents
  double-recording when a module-level call (e.g. `httpx.get`) internally
  delegates to the newly-patched `Client.send`.

### Trust gate fires on all HTTP methods (BREAKING-ISH)

- **Before this release** `_require_trusted_endpoint` was only called for GET
  requests.  It now fires unconditionally for every method (POST, PUT, PATCH,
  DELETE, etc.).
- **Migration:** register every outbound URL — including your LLM provider
  (e.g. `https://openrouter.ai/api/v1/chat/completions`) — in `trusted_endpoints`
  before running an agent.  Use `INSERT ... ON CONFLICT DO NOTHING` or the
  Provably dashboard to add rows.  See `examples/openai_agents/agent_run.py`
  for the pattern.

### New `provably_self_egress()` context manager

- Added `provably.intercept.provably_self_egress()` — a context manager that
  marks a block of code as SDK-internal egress.  Inside it, the trust gate is
  bypassed and no intercept rows are written.  All SDK self-egress sites
  (`handoff.transport`, `handoff.evaluator`, `handoff._bootstrap`) already wrap
  their own HTTP calls in this context, so the SDK never trips its own gate.
  Advanced users who make their own Provably API calls from within an agent loop
  can use this to avoid BLOCKED errors.

## 0.2.0

- Added `provably.configure_indexing(enable_indexing: bool)`: one-call bootstrap (`initialize_runtime` + `init_interceptor` + `enable` / `disable`) for sender agents.
- Added `provably.outcome_from_trace(trace)` and `provably.aggregate_outcome(payload)`: outcome helpers for extracting and rolling up verdicts.
- Added `provably.set_intercept_url_allowlist(urls)` to top-level namespace: scopes the simulation body hook to an explicit set of URLs.
- `Outcome` type now includes `"ERROR"` alongside `"PASS"` and `"CAUGHT"`.
- Bootstrap, preprocess, and HTTP error logging migrated from `print()` to structured `structlog` output.

## 0.1.0

Initial extraction from the `langraph-demo` monorepo.

- Added `provably.initialize_runtime` for one-time Provably bootstrap.
- Added `provably.intercept` (monkey-patches `requests` + `httpx`, stores rows in `provably_intercepts`, enforces trusted-endpoint allow-list on GET).
- Added `provably.handoff.types` (`HandoffPayload` v2, `HandoffClaim`, `HandoffProofAction`, `HandoffProofBundle`, `BenchmarkRow`).
- Added `provably.handoff.transport.post_handoff` and `default_cluster_b_url`.
- Added `provably.handoff.evaluator.evaluate_handoff` and per-claim modes (`verbatim`, `field_extraction`, `schema_type`, `range_threshold`).
- Added `provably.claim_contract` (re-exported from `provably.handoff.contract`): builds the LLM-facing JSON contract for emitting `HandoffClaim` claims, derived from `HandoffClaim` + `VerificationMode` so prompts cannot drift from the wire model.
- Added `provably.build_handoff_payload` and `provably.claim_contract` convenience builders.
- Added `provably.trusted_endpoints` (DDL, `is_trusted_endpoint`, `list_trusted_endpoints`, `check_claim_endpoints_are_trusted`, `normalize_url_for_trust`).
