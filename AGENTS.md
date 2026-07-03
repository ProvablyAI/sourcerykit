# AGENTS.md

SourceryKit is the Python SDK for [Provably](https://provably.ai): verifiable guardrails
for AI agents — it records outbound HTTP calls, enforces endpoint policies, and checks an
agent's claims against what those calls actually returned, so a hallucinated value is
**caught** instead of shipped.

This is the landing page for AI agents. Read the gate below, then follow the breadcrumb to
the one page you need. Each doc is focused — load only what the task requires.

## Install

```bash
pip install sourcerykit    # Python 3.12+
```

## ⚠️ Gate: one human step during setup

Setup is agent-drivable except one step: account registration triggers an **email
verification link that only a human can click**. Until it is clicked, login fails and
nothing downstream works.

→ **[docs/onboarding.md](docs/onboarding.md)** — the full one-time setup (non-interactive
commands, the verification step, database requirements).

## Pick your path

| You want to… | Go to |
|---|---|
| Set up credentials for the first time | [docs/onboarding.md](docs/onboarding.md) |
| Run the whole flow end to end | [docs/example.md](docs/example.md) |
| Copy a runnable agent integration | [cookbooks/openai_agents](cookbooks/openai_agents) · [cookbooks/claude_agent](cookbooks/claude_agent) · [cookbooks/langchain_agent](cookbooks/langchain_agent) |
| Look up a function, type, or error | [docs/src/api.md](docs/src/api.md) |
| Use the CLI (`init`, `doctor`, `endpoints`, `trace`) | [docs/cli.md](docs/cli.md) |
| Record/inspect HTTP calls (`async_intercept_context`) | [docs/intercept.md](docs/intercept.md) |
| Build the handoff payload + claims, read the verdict | [docs/handoff.md](docs/handoff.md) |
| Allow-list outbound endpoints | [docs/trusted-endpoints.md](docs/trusted-endpoints.md) |
| Understand how the pieces fit | [docs/architecture.md](docs/architecture.md) |
| Migrate from the old `provably` SDK | [docs/migrations/v1_0/v1_0.md](docs/migrations/v1_0/v1_0.md) |

The **cookbooks are the ground truth** for a correct integration: a real agent produces the
claim as structured output (`SourceryKitAgentResponse`); the claim is never computed by hand.

## The flow at a glance

```
bootstrap_system()              # init: schema, handshake, HTTP interceptor — call first, once
insert_trusted_endpoint(url)    # allow-list each outbound endpoint
async_intercept_context(...)    # wrap the tool's HTTP call — records it
SourceryKitAgentResponse        # the agent's structured output (reasoning + claimed_values)
build_handoff_payload(...)      # compile claims; intercept_agent_id must match the agent_id above
evaluate_handoff(payload)       # -> {"outcome": "PASS" | "CAUGHT" | "ERROR", "per_claim": [...]}
```

Outcomes:

- `PASS` — every claim matched the recorded data.
- `CAUGHT` — a claim did not match the recorded data, or its endpoint was not trusted.
- `ERROR` — nothing was verified (for example, zero claims could be resolved). Verifying
  zero claims is always `ERROR`, never a pass.

Async throughout — `await` every SDK call. Recorded traffic: `httpx`, `aiohttp`, and
`requests`. `action_name` is the join key between the intercepted call and the claim — it
must match.
