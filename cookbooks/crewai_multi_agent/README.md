# CrewAI Multi-Agent — Invoice Auditing with Specialist Agents
This example demonstrates multi-agent orchestration using [CrewAI](https://github.com/crewAIInc/crewAI) with SourceryKit verification. Three specialist agents each query a different ERP table, with centralized evaluation by the orchestrator.

## Flow
```
Flow[AuditState]:

  @start() run_specialists()
    → Crew with 3 specialist agents, each querying a different table:
      - Amount Validator → invoices table (action_name="get_invoice_amount")
      - Vendor Checker   → vendors table  (action_name="get_vendor")
      - Currency Verifier → currencies table (action_name="get_currency")
    → Each has its own agent_id and action_name for intercept tracking
    → Returns SourceryKitAgentResponse per agent

  @listen(run_specialists) build_payloads()
    → Deterministic: builds HandoffPayload per specialist
    → Producer side: agents build verifiable artifacts

  @listen(build_payloads) evaluate_and_report()
    → Orchestrator evaluates each payload (never sees raw agent output)
    → PASS → success report
    → CAUGHT → Remediation crew produces incident report
```

## How It Works
1. **HTTP Interception**: Each specialist's tool wraps its HTTP call with `async_intercept_context(agent_id=..., action_name=...)`, logging the request/response to the database separately per agent and per table.
2. **Specialist Crew**: Three agents run in sequence, each querying a different ERP table (invoices, vendors, currencies).
3. **Payload Building**: Deterministic code builds a `HandoffPayload` per specialist. This is the producer side — agents create verifiable artifacts.
4. **Evaluation**: The orchestrator evaluates each payload via `evaluate_handoff`. This is the verifier side — the orchestrator never touches raw agent output, only the verifiable payloads.
5. **Conditional Routing**: If any payload fails verification, a remediation crew produces an incident report analyzing the discrepancy.

---

## Environment Configuration
Before running the system, run the interactive setup wizard to configure your SourceryKit project variables automatically:

```bash
sourcerykit init
```

> [!IMPORTANT]
> The wizard only configures **SOURCERYKIT_*** variables. It does **not** configure your LLM provider infrastructure keys (like `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`). Those must still be set up separately in your environment.

| Variable | Required | Description |
|---|---|---|
| `MODEL_NAME` | **yes** | Targeted model engine name (e.g., `openai/gpt-4o-mini`). |

> [!Note]
> Ensure your underlying model provider's environment variables—such as `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`—are also set as required by your CrewAI provider setup.

---

## Execution
1. Install dependencies:
   ```bash
   pip install sourcerykit crewai-tools python-dotenv httpx pydantic

   # Pick the CrewAI extra that matches your LLM provider:
   pip install "crewai[openai]"       # OpenAI
   pip install "crewai[anthropic]"    # Anthropic
   pip install "crewai[litellm]"      # OpenRouter / multi-provider via LiteLLM
   ```
2. Export your LLM-provider keys into your current shell or place them in a local `.env` file:
   ```bash
   export MODEL_NAME="openai/gpt-4o-mini"
   export OPENAI_API_KEY="sk-..."
   ```
3. Run the example:
      ```bash
      # Standard Validation
      python agent_run.py

      # or

      # Hallucination Simulation
      python agent_run.py --tamper
   ```
