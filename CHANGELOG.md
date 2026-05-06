# Changelog

## Unreleased

- `trusted_endpoints`: registered URLs may now contain FastAPI/Express-style path placeholders. `{id}` matches exactly one path segment, `{rest:path}` matches any subtree. Plain URLs without `{` keep exact-match semantics — no migration needed for existing rows. Both `is_trusted_endpoint` and the snapshot tamper-check inside `evaluate_handoff` honor the new syntax. Closes #14.
- README: new "Getting `PROVABLY_API_KEY` and `PROVABLY_ORG_ID`" subsection walking through sign-up at app.provably.ai → create org → Integrations menu, plus a pointer to provably.ai/docs.
- **BREAKING:** removed `default_cluster_b_url()` and the `CLUSTER_B_URL` env var — leftovers from the langgraph-demo monorepo extraction with a `localhost:8082` default and opaque "cluster B" naming the SDK has no business assuming. `post_handoff(receiver_url, payload)` (positional arg renamed from `cluster_b_url`) takes the URL directly — supply it from your application's own configuration.

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
