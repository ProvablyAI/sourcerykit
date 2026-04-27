# Changelog

## 0.2.0

- Added `provably.configure_indexing(enable_indexing: bool)`: one-call bootstrap (`initialize_runtime` + `init_interceptor` + `enable` / `disable`) for sender agents.
- Added `provably.handoff.outcomes` with `outcome_from_trace(trace)` and `aggregate_outcome(payload)`; both re-exported as `provably.outcome_from_trace` and `provably.aggregate_outcome`.

## 0.1.0 (unreleased)

Initial extraction from the `langraph-demo` monorepo.

- Added `provably.initialize_runtime` for one-time Provably bootstrap.
- Added `provably.intercept` (monkey-patches `requests` + `httpx`, stores rows in `provably_intercepts`, enforces trusted-endpoint allow-list on GET).
- Added `provably.handoff.types` (`HandoffPayload` v2, `HandoffClaim`, `HandoffProofAction`, `HandoffProofBundle`, `BenchmarkRow`).
- Added `provably.handoff.transport.post_handoff` and `default_cluster_b_url`.
- Added `provably.handoff.evaluator.evaluate_handoff` and per-claim modes (`verbatim`, `field_extraction`, `schema_type`, `range_threshold`).
- Added `provably.claim_contract` (re-exported from `provably.handoff.contract`): builds the LLM-facing JSON contract for emitting `HandoffClaim` claims, derived from `HandoffClaim` + `VerificationMode` so prompts cannot drift from the wire model. Callers pass deployment config (`action_names`, `wrapper_fields`, `extra_rules`).
- Added `provably.trusted_endpoints` (DDL, `is_trusted_endpoint`, `list_trusted_endpoints`, `check_claim_endpoints_are_trusted`, `normalize_url_for_trust`).
