# LangGraph Multi-Agent — Travel Agency Flight Status
This example demonstrates a multi-agent pipeline using [LangGraph](https://github.com/langchain-ai/langgraph) with SourceryKit verification and conditional routing.

## Flow
```
START → Fetcher Agent → Build Handoff → Evaluator
                                            │
                         ┌──────────────────┤
                         ▼                  ▼
                      CAUGHT → Healer Agent  PASS → Success
```

1. **Fetcher Agent** — calls a mock flight API for flight BA2490 (London Heathrow → Paris CDG), returns `SourceryKitAgentResponse` with claims.
2. **Build Handoff** — deterministic node compiles claims into a `HandoffPayload` (no LLM involved).
3. **Evaluator** — runs `evaluate_handoff` to verify claims against recorded HTTP intercepts.
4. **Conditional routing**:
   - **PASS** → Success node prints the verified flight status.
   - **CAUGHT** → Healer Agent analyzes the failure and produces a corrected response.

## How It Works
1. **HTTP Interception**: The fetcher's tool wraps its HTTP call with `async_intercept_context`, logging the request/response to the database.
2. **Handoff Payload**: `build_handoff_payload` compiles the fetcher's claims into a verifiable payload.
3. **Evaluation**: `evaluate_handoff` checks cryptographic proofs and compares claims against recorded intercepts.
4. **Healing**: On CAUGHT, the healer agent receives the original claims and failure details, then produces corrected claims.

## Mock Data

| Flight | Route | Status | Departure | Gate |
|---|---|---|---|---|
| BA2490 | LHR→CDG | ON_TIME | 2026-07-09T14:30:00Z | B42 |

---

## Environment Configuration
Before running the system, run the interactive setup wizard to configure your SourceryKit project variables automatically:

```bash
sourcerykit init
```

> [!IMPORTANT]
> The wizard only configures **SOURCERYKIT_*** variables. It does **not** configure your LLM provider infrastructure keys. You must set your model provider's environment variables (e.g. `OPENROUTER_API_KEY`) separately.

| Variable | Required | Description |
|---|---|---|
| `MODEL_NAME` | **yes** | Targeted model architecture identifier string passed to create_agent (e.g., `openrouter:openai/gpt-4o-mini`). |

---

## Execution
1. Install dependencies:
   ```bash
   pip install sourcerykit langchain langgraph python-dotenv httpx pydantic
   ```
2. Export your LLM-provider keys into your current shell or place them in a local `.env` file:
   ```bash
   export MODEL_NAME="openrouter:openai/gpt-4o-mini"
   ```
3. Run the example:
      ```bash
      # Standard Validation
      python agent_run.py

      # or

      # Hallucination Simulation
      python agent_run.py --tamper
   ```
