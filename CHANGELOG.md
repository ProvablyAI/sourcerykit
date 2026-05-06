# Changelog

## Unreleased

- `trusted_endpoints`: registered URLs may now contain FastAPI/Express-style path placeholders. `{id}` matches exactly one path segment, `{rest:path}` matches any subtree. Plain URLs without `{` keep exact-match semantics — no migration needed for existing rows. Both `is_trusted_endpoint` and the snapshot tamper-check inside `evaluate_handoff` honor the new syntax. Closes #14.
- `set_intercept_url_allowlist`: now accepts the same `{id}` / `{rest:path}` placeholders as `trusted_endpoints` (parity, single matching helper used by both code paths). A registered `https://api.example.com/customers/{id}` covers the concrete `https://api.example.com/customers/42` for both intercept recording and the simulation tamper hook. Plain URLs without `{` keep exact-match semantics — zero migration. Closes #20.
- `json_path` (used by `field_extraction` / `schema_type` / `range_threshold`): now supports array indexing. Use bracket form (`items[0].subject`, `[0].status`) or numeric-segment fallback (`items.0.subject`). Out-of-range indices raise `IndexError` and surface as `CAUGHT` with `"out of range"` in the detail. Pure-dict paths are unchanged. Closes #23.
- README: new "Getting `PROVABLY_API_KEY` and `PROVABLY_ORG_ID`" subsection walking through sign-up at app.provably.ai → create org → Integrations menu, plus a pointer to provably.ai/docs.
- **BREAKING:** removed `default_cluster_b_url()` and the `CLUSTER_B_URL` env var — leftovers from the langgraph-demo monorepo extraction with a `localhost:8082` default and opaque "cluster B" naming the SDK has no business assuming. `post_handoff(receiver_url, payload)` (positional arg renamed from `cluster_b_url`) takes the URL directly — supply it from your application's own configuration.

## 0.3.0

### aiohttp interception (soft dependency)

- `aiohttp.ClientSession._request` is now patched when `aiohttp` is importable.
  The intercept SDK does **not** add `aiohttp` as a hard dependency — the patch
  installs only when the user's environment already has it.
- This unlocks **LiteLLM** (which uses `aiohttp` as its default transport since
  v1.71+) and any framework that opts into an `aiohttp` extra (Google GenAI,
  Google ADK, etc.).
- Body override (the simulation tamper hook) is not supported for
  `aiohttp.ClientResponse` — recording fires in full but the response is
  returned unchanged.

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
