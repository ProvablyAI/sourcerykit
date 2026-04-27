# Documentation index

Reference docs for the `provably` Python SDK. For setup and API examples, see
the top-level [`README.md`](../README.md). For invariants and where to edit,
see [`CONTEXT.md`](../CONTEXT.md).

## Architecture

| Document | Purpose |
|---|---|
| [`architecture.md`](architecture.md) | Module map, dependency rules, I/O boundaries, and the public-vs-internal split. |

## Per-pillar deep dives

| Document | Pillar |
|---|---|
| [`intercept.md`](intercept.md) | Lifecycle of `init_interceptor` / `enable` / `disable`, the simulation hook, what gets stored where. |
| [`handoff.md`](handoff.md) | `HandoffPayload` v2 wire format, transport contract, the four verification modes, evaluator semantics. |
| [`trusted-endpoints.md`](trusted-endpoints.md) | Registry schema, URL normalization, policy enforcement, cross-org sharing. |

## Historical plans

| Document | Description |
|---|---|
| [`historical-plans/README.md`](historical-plans/README.md) | Index of post-execution plan records. |
| [`historical-plans/split-from-monorepo.md`](historical-plans/split-from-monorepo.md) | Carve-out from the `verifiable-state-demo` monorepo into this SDK (executed). |
