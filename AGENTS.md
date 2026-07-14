# AGENTS.md

SourceryKit is the Python SDK for [Provably](https://provably.ai): verifiable guardrails
for AI agents — it records outbound HTTP calls, enforces endpoint policies, and checks an
agent's claims against what those calls actually returned, so a hallucinated value is
**caught** instead of shipped.

> [!IMPORTANT]
> **Setup is scriptable — prefer the non-interactive `sourcerykit init` CLI over
> hand-writing config.** Exactly one step needs a human: clicking the email-verification
> link. Full steps: [docs/onboarding.md](docs/onboarding.md).

## Where to go next

| Your situation | Do this |
|---|---|
| First time — no Provably credentials yet | Run the `sourcerykit init` setup (see the note above) → [docs/onboarding.md](docs/onboarding.md). |
| Integrating SourceryKit into an agent | Open the closest cookbook ([below](#cookbooks-runnable-examples)), mirror it, then swap in your own tool and claims. |
| Want to see one full run first | [docs/example.md](docs/example.md) — end-to-end walkthrough. |
| Got an unexpected `CAUGHT` or `ERROR` | Read [the outcomes below](#the-flow-at-a-glance), then [docs/handoff.md](docs/handoff.md). |
| Need a signature, type, or CLI flag | [docs/src/api.md](docs/src/api.md) · [docs/cli.md](docs/cli.md) |
| Record or inspect outbound HTTP calls | [docs/intercept.md](docs/intercept.md) |
| Allow-list outbound endpoints | [docs/trusted-endpoints.md](docs/trusted-endpoints.md) |
| Understand how the pieces fit | [docs/architecture.md](docs/architecture.md) |
| Migrate from the old `provably` SDK | [docs/migrations/v1_0/v1_0.md](docs/migrations/v1_0/v1_0.md) |

**Cookbooks are the ground truth — mirror one, never hand-roll the claim.** Everything else
is supporting docs; load only what a task needs.

## Cookbooks (runnable examples)

Each is a full runnable agent: `python agent_run.py` for a `PASS`; add `--tamper` to corrupt
a claim and watch `evaluate_handoff` return `CAUGHT`. Every claimed value carries a
`sourcerykit_ref` (copied from the tool's output) that maps it to the exact recorded call —
so the same tool can be called many times, and separate agents can each own a stage.

**Framework not listed?** The flow is identical everywhere — only the structured-output
binding is framework-specific. Copy the closest cookbook and change just that binding; each
cookbook's README covers its own wiring.

**Single-agent** — one agent fetches, claims, and verifies (weather):

| Cookbook | Framework | What you'll find |
|---|---|---|
| [openai_agents](cookbooks/openai_agents) | OpenAI Agents SDK | Structured output via `output_type=SourceryKitAgentResponse` |
| [claude_agent](cookbooks/claude_agent) | Claude Agent SDK | Structured output via `output_format` json_schema |
| [langchain_agent](cookbooks/langchain_agent) | LangChain `create_agent` | Structured output via `response_format=`, claims read from `result["structured_response"]` |

**Multi-agent / multi-tool** — producer agents build claims; a separate verifier evaluates them:

| Cookbook | Framework | Pattern |
|---|---|---|
| [openai_agents_multi_agent](cookbooks/openai_agents_multi_agent) | OpenAI Agents SDK | Orchestrator → specialists → verify (customer support) |
| [crewai_multi_agent](cookbooks/crewai_multi_agent) | CrewAI | Specialist crew → build → evaluate → remediate (invoice audit) |
| [langgraph_multi_agent](cookbooks/langgraph_multi_agent) | LangGraph | Fetcher → evaluator → healer on `CAUGHT` (flights) |
| [claude_agent_multi_tool](cookbooks/claude_agent_multi_tool) | Claude Agent SDK | Same tool called twice; `sourcerykit_ref` maps each claim (weather) |

## The flow at a glance

```bash
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
`requests`. Each claim maps to its recorded call by the `sourcerykit_ref` the tool returns
(copied into the claimed value), so the same tool or `action_name` can be called repeatedly.
