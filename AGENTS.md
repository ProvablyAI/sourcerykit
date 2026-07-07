# AGENTS.md

SourceryKit is the Python SDK for [Provably](https://provably.ai): verifiable guardrails
for AI agents — it records outbound HTTP calls, enforces endpoint policies, and checks an
agent's claims against what those calls actually returned, so a hallucinated value is
**caught** instead of shipped.

## Where to go next

| Your situation | Do this |
|---|---|
| First time — no Provably credentials yet | [Set up below](#setup-onboarding): two non-interactive `sourcerykit init` commands + one email-verification click. Full walkthrough: [docs/onboarding.md](docs/onboarding.md). |
| Integrating SourceryKit into an agent | Open the closest cookbook ([below](#cookbooks-runnable-examples)), mirror it, then swap in your own tool and claims. |
| Want to see one full run first | [docs/example.md](docs/example.md) — end-to-end walkthrough. |
| Got an unexpected `CAUGHT` or `ERROR` | Read [the outcomes below](#the-flow-at-a-glance), then [docs/handoff.md](docs/handoff.md). |
| Need a signature, type, or CLI flag | [docs/src/api.md](docs/src/api.md) · [docs/cli.md](docs/cli.md) |

**Cookbooks are the ground truth — mirror one, never hand-roll the claim.** Everything else
is supporting docs; load only what a task needs.

## Setup (onboarding)

Onboarding is fully scriptable — prefer the CLI over setting config by hand. An agent can do
it end to end with two non-interactive commands, with one human step (the email-verification
click) in between. Full walkthrough: [docs/onboarding.md](docs/onboarding.md).

**1. Register** — creates the account, sends the verification email, then exits:

```bash
sourcerykit init --register --email you@example.com --password '<password>'
```

**2. Verify the email** — click the link sent to that address. This is the one step an agent
cannot do itself.

**3. Complete setup** — logs in, creates or selects the org, fetches the API key, validates
the database, runs the bootstrap handshake, and writes all config:

```bash
sourcerykit init --email you@example.com --password '<password>' \
  --postgres-url 'postgresql://user:pass@host:5432/dbname' \
  --project-name my-project
```

Step 3 writes the API key + org id to the global config, and the project name, Postgres URL,
and bootstrap IDs (`SOURCERYKIT_MIDDLEWARE_ID`, `…_DATABASE_ID`, `…_SCHEMA_ID`, `…_TABLE_ID`,
`…_COLLECTION_ID`, `…_INTEGRATION_KEY`) to the local `.env`. Check it any time with
`sourcerykit doctor` (add `--fix` to repair), or inspect it with `sourcerykit config list`.

> A brand-new account has no organization, so step 3 auto-creates one and stays fully
> non-interactive. If the account already belongs to **multiple** orgs, `init` prompts to
> choose — use a single-org account to keep it scriptable.

**Manual / CI fallback.** Already have credentials, or scripting without the CLI? Set the
config via environment variables instead — these override the stored config:

```bash
export PROVABLY_API_KEY='...'
export SOURCERYKIT_ORG_ID='...'
export SOURCERYKIT_POSTGRES_URL='postgresql://user:pass@host:5432/dbname'
```

## Cookbooks (runnable examples)

Same weather-verify flow in three frameworks. Each fetches the London temperature from
open-meteo, returns its claims as `SourceryKitAgentResponse`, and runs the full
intercept → `build_handoff_payload` → `evaluate_handoff` loop. Run `python agent_run.py`
for a `PASS`; add `--tamper` to fake a value and watch it get `CAUGHT`.

**Framework not listed?** The SDK calls (`bootstrap_system`, `insert_trusted_endpoint`,
`async_intercept_context`, `build_handoff_payload`, `evaluate_handoff`) are identical for
every framework — only how you bind `SourceryKitAgentResponse` as the agent's structured
output changes. Copy any cookbook and replace just that binding with your framework's
equivalent. No structured-output support? Prompt the model with
`SourceryKitAgentResponse.model_json_schema()` and validate the reply into the model by hand.

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

## More docs

Not linked above: [intercept.md](docs/intercept.md) (recording HTTP calls) ·
[trusted-endpoints.md](docs/trusted-endpoints.md) (allow-listing) ·
[architecture.md](docs/architecture.md) (how it fits) ·
[migrations/v1_0/v1_0.md](docs/migrations/v1_0/v1_0.md) (from the old `provably` SDK)
