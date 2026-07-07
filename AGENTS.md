# AGENTS.md

SourceryKit is the Python SDK for [Provably](https://provably.ai): verifiable guardrails
for AI agents — it records outbound HTTP calls, enforces endpoint policies, and checks an
agent's claims against what those calls actually returned, so a hallucinated value is
**caught** instead of shipped.

## Where to go next

| Your situation | Do this |
|---|---|
| First time — no Provably credentials yet | Run setup: [docs/onboarding.md](docs/onboarding.md). One human step (an email-verification click); everything else is agent-drivable. |
| Integrating SourceryKit into an agent | Open the cookbook matching your framework ([below](#cookbooks-runnable-examples)), mirror its structure, then swap in your own tool and claims. |
| Want to see one full run first | [docs/example.md](docs/example.md) — end-to-end walkthrough. |
| Got an unexpected `CAUGHT` or `ERROR` | Read [the outcomes below](#the-flow-at-a-glance), then [docs/handoff.md](docs/handoff.md). |
| Need a signature, type, or CLI flag | [docs/src/api.md](docs/src/api.md) · [docs/cli.md](docs/cli.md) |

**Cookbooks are the ground truth — mirror one, never hand-roll the claim.** Everything else
is supporting docs; load only what a task needs.

## Cookbooks (runnable examples)

Same weather-verify flow in three frameworks. Each fetches the London temperature from
open-meteo, returns its claims as `SourceryKitAgentResponse` (never computed by hand), and
runs the full intercept → `build_handoff_payload` → `evaluate_handoff` loop. Run
`python agent_run.py` for a `PASS`; add `--tamper` to fake a value and watch it get `CAUGHT`.

| Cookbook | Framework | What you'll find |
|---|---|---|
| [openai_agents](cookbooks/openai_agents) | OpenAI Agents SDK | Structured output via `output_type=SourceryKitAgentResponse` |
| [claude_agent](cookbooks/claude_agent) | Claude Agent SDK | Structured output via `output_format` json_schema |
| [langchain_agent](cookbooks/langchain_agent) | LangChain `create_agent` | Structured output via `response_format=`, claims read from `result["structured_response"]` |

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

## All docs

- [onboarding.md](docs/onboarding.md) — first-time credential setup
- [example.md](docs/example.md) — end-to-end walkthrough
- [src/api.md](docs/src/api.md) — functions, types, errors
- [cli.md](docs/cli.md) — CLI (`init`, `doctor`, `endpoints`, `trace`)
- [intercept.md](docs/intercept.md) — recording HTTP calls (`async_intercept_context`)
- [handoff.md](docs/handoff.md) — handoff payload, claims, and verdicts
- [trusted-endpoints.md](docs/trusted-endpoints.md) — allow-listing outbound endpoints
- [architecture.md](docs/architecture.md) — how the pieces fit
- [migrations/v1_0/v1_0.md](docs/migrations/v1_0/v1_0.md) — migrate from the old `provably` SDK
