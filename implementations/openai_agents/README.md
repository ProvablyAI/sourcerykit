# OpenAI Agents SDK + Provably — Runnable Demo

This demo shows an end-to-end run of the Provably SDK integrated with the
[OpenAI Agents SDK](https://github.com/openai/openai-agents-python) (>=0.0.3).
It exercises every pillar of the SDK in a single script:

1. **Intercept** — `configure_indexing(True)` installs monkey-patches on
   `httpx.AsyncClient.send` and `requests.Session.send` so every outbound HTTP
   request from the agent loop is captured and stored in `provably_intercepts`.
2. **Trust gate** — before storing a request the SDK checks that its URL is
   registered in `trusted_endpoints`.  The demo seeds both the OpenRouter
   chat-completions URL and the Open-Meteo weather URL before running the agent.
3. **Tool call** — the agent uses a `@function_tool` that calls the free
   [Open-Meteo API](https://open-meteo.com/) (no API key required) to fetch the
   current temperature in London.
4. **Handoff** — the captured intercept row id is wrapped in a `HandoffPayload`
   with one `HandoffClaim` asserting the tool output.
5. **Evaluate** — `evaluate_handoff()` fetches the stored query record from the
   Provably backend, compares it to the claimed value, and prints the verdict.

Expected output (abbreviated):

```json
{
  "outcome": "PASS",
  "per_claim": [
    {
      "action_name": "get_weather",
      "result": "PASS",
      "proof_time_ms": 42,
      "verify_time_ms": 137
    }
  ],
  "errors": []
}
```

## Required environment variables

| Variable | Required | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | yes | API key for [OpenRouter](https://openrouter.ai/). Used for the model call (`openai/gpt-4o-mini`). |
| `PROVABLY_API_KEY` | yes | Provably integration API key. |
| `PROVABLY_ORG_ID` | yes | Provably organisation id. Scopes trusted-endpoint and query-record lookups. |
| `PROVABLY_RUST_BE_URL` | yes | Base URL of the Provably Rust backend (e.g. `https://api.provably.ai`). |
| `POSTGRES_URL` | yes | PostgreSQL DSN (e.g. `postgresql://user:pass@host/db`). Used for intercept storage and trusted-endpoint registry. |

## How to run

```bash
# 1. Install the SDK in editable mode with dev extras (includes openai-agents)
pip install -e .[dev]

# 2. Export the required env vars
export OPENROUTER_API_KEY="sk-or-..."
export PROVABLY_API_KEY="prov_..."
export PROVABLY_ORG_ID="org_..."
export PROVABLY_RUST_BE_URL="https://api.provably.ai"
export POSTGRES_URL="postgresql://user:pass@localhost/provably"

# 3. Run the demo
python implementations/openai_agents/agent_run.py
```

## Model and cost

The demo uses **`openai/gpt-4o-mini`** on OpenRouter — a cheap, capable model
that reliably follows tool-calling instructions.  Estimated cost is approximately
**$0.001 per run** (one tool call + one summary turn).

## How the trust gate works — and what happens when you forget to seed it

The Provably SDK now enforces trust on **all HTTP methods** (GET, POST, etc.),
not only GET.  This means the LLM provider call (a POST to OpenRouter) *and* the
weather API call (a GET to Open-Meteo) both need to be registered in
`trusted_endpoints` before the agent runs.

If you forget to seed an endpoint, the SDK raises:

```
RuntimeError: BLOCKED: endpoint https://openrouter.ai/api/v1/chat/completions not in trusted index for org <org_id>
```

When this error occurs inside `httpx.AsyncClient.send` (the async LLM call), the
OpenAI SDK wraps it in an `APIConnectionError`.  You can inspect the full
exception chain to find the original `BLOCKED: ...` message.

**Migration note for existing users:** if you were previously relying on the SDK
only trust-checking GET requests, you must now register *all* outbound URLs
including your LLM provider URL.  Use the `seed_trusted_endpoints` helper pattern
shown in this demo (raw psycopg2 `INSERT ... ON CONFLICT DO NOTHING`), or add
rows via the Provably dashboard.

## How `provably_self_egress()` relates to this demo

The Provably SDK's own HTTP calls (fetching query records, posting verify
requests, bootstrap handshakes) are **never** blocked by the trust gate.  They
run inside `with provably_self_egress():` context managers that mark them as
SDK-internal egress, so the trust gate is bypassed automatically.  You do not
need to add Provably's own backend URL to `trusted_endpoints`.
