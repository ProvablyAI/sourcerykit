# Architecture
The SourceryKit SDK adds verifiable guardrails to Python agents by making outbound actions observable, enforceable, and auditable. Its modular architecture isolates responsibilities to ensure easy integration and security.

## Core Flow
SourceryKit intercepts an agent’s outbound HTTP calls, enforces endpoint policies, records interactions, and enables deterministic evaluation of claims.

<div align="center">
  <img src="https://raw.githubusercontent.com/ProvablyAI/sourcerykit/refs/heads/main/docs/images/architecture.svg" alt="architecture" width="550" />
</div>

## Component Overview

- **Agent**: The host Python application. It executes HTTP requests, submits claims for evaluation, and receives verifiable results with minimal changes to core logic.

- **Bootstrap System**: Handles one-time initialization, including database schema setup and resource registration, before the agent starts executing. See [README](../README.md).

- **HTTP Interceptor**: Intercepts outbound HTTP calls to enforce policies and record payloads. Untrusted requests are blocked before leaving the process. See [intercept](intercept.md).

- **Database Tables**:
  - **Trusted Endpoints**: A registry of allowed endpoints used by the Interceptor to validate outbound requests. See [trusted-endpoints](trusted-endpoints.md).
  - **Intercepts**: An append-only table storing detailed records of every outbound HTTP request and response. The Provably backend uses these records to generate cryptographic proofs. See [intercept](intercept.md).

- **Handoff Payload**: A structured data format used to pass claims about external calls between agents or services. See [handoff](handoff.md).

- **Evaluator**: Compares agent claims against authoritative records from the Provably backend, returning a deterministic verdict (`PASS`, `CAUGHT`, or `ERROR`). See [handoff](handoff.md).

- **Provably Backend**: The external service acting as the single source of truth for verifying agent claims by generating proofs from the Intercepts table.

---

**Next steps:**

- [Onboarding](onboarding.md) — one-time account, credentials, and database setup
- [End-to-End Walkthrough](example.md) — run the whole flow in code
- [Intercept](intercept.md) — how outbound HTTP calls are captured and recorded
- [Handoff](handoff.md) — building claims and reading the verdict
- [Trusted Endpoints](trusted-endpoints.md) — the outbound allow-list
