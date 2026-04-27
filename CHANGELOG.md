# Changelog

## 0.1.0 (unreleased)

Initial extraction from the `langraph-demo` monorepo.

- Added `provably.initialize_runtime` for one-time Provably bootstrap.
- Added `provably.intercept` (monkey-patches `requests` + `httpx`, stores rows in `provably_intercepts`, enforces trusted-endpoint allow-list on GET).
- Added `provably.handoff.types` (`HandoffPayload` v2, `HandoffClaim`, `HandoffProofAction`, `HandoffProofBundle`, `BenchmarkRow`).
- Added `provably.handoff.transport.post_handoff` and `default_cluster_b_url`.
- Added `provably.handoff.evaluator.evaluate_handoff` and per-claim modes (`verbatim`, `field_extraction`, `schema_type`, `range_threshold`).
- Added `provably.trusted_endpoints` (DDL, `is_trusted_endpoint`, `list_trusted_endpoints`, `check_claim_endpoints_are_trusted`, `normalize_url_for_trust`).
