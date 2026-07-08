# OpenAI Agents SDK — Multi-Agent Customer Support

This example demonstrates multi-agent orchestration using the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) with SourceryKit verification. Three specialist agents each query a different customer support table, with centralized evaluation by the orchestrator.

## Flow

```
User: "Customer CUST-001 is asking about order ORD-123..."
  → Orchestrator Agent
    → analyzes query, routes to relevant specialists
    → calls run_order_status_check()
      → fetches order data, builds HandoffPayload, stores in global dict
    → calls run_return_policy_check()
      → fetches policy data, builds HandoffPayload, stores in global dict
    → calls run_account_balance_check()
      → fetches balance data, builds HandoffPayload, stores in global dict
    → calls verify_claims(specialist='order_status')
    → calls verify_claims(specialist='return_policy')
    → calls verify_claims(specialist='account_balance')
    → reports combined verdict
```

## How It Works
1. **HTTP Interception**: Each specialist's tool wraps its HTTP call with `async_intercept_context(agent_id=..., action_name=...)`, logging the request/response to the database separately per agent and per table.
2. **Specialist Agents**: Three agents, each querying a different support table (orders, policies, accounts). Specialists perform basic validation and return confidence scores in their reasoning.
3. **Payload Building**: Deterministic code builds a `HandoffPayload` per specialist and stores it in a global `_payloads` dict. This is the producer side — agents create verifiable artifacts.
4. **Verification**: The orchestrator calls `verify_claims(specialist='<name>')` to evaluate each payload via `evaluate_handoff`. This is the verifier side — the orchestrator decides WHEN to verify but doesn't pass JSON.

## Mock Data Tables

| Specialist | Table | Action Name | Agent ID |
|---|---|---|---|
| Order Status | orders | `get_order_status` | `order_status` |
| Return Policy | policies | `get_return_policy` | `return_policy` |
| Account Balance | accounts | `get_account_balance` | `account_balance` |

---

## Environment Configuration

```bash
sourcerykit init
```

> [!IMPORTANT]
> The wizard only configures **SOURCERYKIT_*** variables. LLM provider keys must be set separately.

| Variable | Required | Description |
|---|---|---|
| `MODEL_URL` | **yes** | Base URL for the LLM provider (e.g., `https://openrouter.ai/api/v1`). |
| `MODEL_API_KEY` | **yes** | API authentication token for the LLM provider. |
| `MODEL_NAME` | **yes** | Model name (e.g., `openai/gpt-4o-mini`). |

---

## Execution

1. Install dependencies:
   ```bash
   pip install sourcerykit openai-agents python-dotenv httpx pydantic
   ```
2. Export your LLM-provider keys:
   ```bash
   export MODEL_URL="https://openrouter.ai/api/v1"
   export MODEL_API_KEY="sk-or-..."
   export MODEL_NAME="openai/gpt-4o-mini"
   ```
3. Run:
   ```bash
   # Standard validation (PASS)
   python agent_run.py

   # Hallucination simulation (CAUGHT)
   python agent_run.py --tamper
   ```
