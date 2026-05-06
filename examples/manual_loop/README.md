# Manual loop demo

End-to-end walk-through of the SDK without an agent framework: tool → LLM →
handoff → evaluate, all orchestrated by hand.

This is the simplest shape of an SDK integration and the recommended starting
point. There is no async tool/LLM interleaving, so the [`intercept_context`](../../src/provably/intercept/interceptor.py)
ContextVar lifecycle is trivial and you do not need to think about which
agent framework's `Task` semantics apply.

For a Runner-based equivalent (OpenAI Agents SDK), see [`../openai_agents/`](../openai_agents/).

## What it shows

1. Seed `trusted_endpoints` with the URLs the demo will hit.
2. `configure_indexing(True)` — installs the interceptor.
3. Call the weather tool directly. Inside the tool body, `with intercept_context(agent_id="demo", action_name="get_weather"):` scopes the tag to just the weather GET.
4. Snapshot `take_last_intercept_row_id()` immediately after — that's the weather row.
5. POST to an LLM for a natural-language summary. The text goes into `reasoning` only; the evaluator never compares it.
6. `build_handoff_payload(..., intercept_agent_id="demo")` — the `intercept_agent_id` matches the tool's `agent_id`, so the lookup hits the right row.
7. `evaluate_handoff(...)` returns `{"outcome": "PASS", ...}` on the happy path.

## Run

```bash
# Required for both paths
export PROVABLY_API_KEY=...
export PROVABLY_ORG_ID=...
export PROVABLY_RUST_BE_URL=...
export POSTGRES_URL=...

# OpenRouter (default; ~$0.001/run with openai/gpt-4o-mini)
export OPENROUTER_API_KEY=...
python examples/manual_loop/agent_run.py

# Or any OpenAI-compatible local endpoint (Docker Model Runner, vLLM, llama.cpp server, …)
export HF_TGI_URL="http://localhost:12434/engines/v1/chat/completions"
export HF_TGI_MODEL="huggingface.co/qwen/qwen3.5-0.8b-base"   # optional
python examples/manual_loop/agent_run.py

# Tamper path — flips the claimed temperature so the evaluator catches it
python examples/manual_loop/agent_run.py --tamper
```

Expected happy-path output (abbreviated):

```json
{
  "outcome": "PASS",
  "per_claim": [
    { "action_name": "get_weather", "result": "PASS", "proof_time_ms": 42, "verify_time_ms": 137 }
  ],
  "errors": []
}
```

`--tamper` adds 50 °C to the claimed temperature before building the payload, so the evaluator returns:

```json
{
  "outcome": "CAUGHT",
  "per_claim": [
    { "action_name": "get_weather", "result": "CAUGHT", ... }
  ],
  "errors": []
}
```
