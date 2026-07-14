# Claude Agent SDK — Multi-Tool-Call Demo

This example demonstrates SourceryKit's multi-tool-call verification with the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). The agent calls the **same tool** (`get_weather`) twice with different cities (London and Paris). Each call produces a unique `sourcerykit_ref` (the database row UUID). The agent's claims reference the correct ref for each city, and the SDK maps each claim to the right intercept.

## How It Works

1. **HTTP Interception**: Each `async_intercept_context` invocation generates a unique `sourcerykit_ref` UUID. The tool returns it alongside the response data, so the agent knows which claim maps to which intercept.
2. **All-Method Trust Gate**: SourceryKit enforces structural target validation checks against your external network endpoints. The external weather lookup endpoint (`api.open-meteo.com`) is explicitly registered via policy seeds (`insert_trusted_endpoint`) before execution.
3. **Automated Handoff & Evaluation**: The agent groups `claimed_values` by `sourcerykit_ref` and builds one claim per intercept. Each claim's `call_ref` is set to the corresponding `sourcerykit_ref`, so `build_handoff_payload` resolves each claim to the correct intercept row — even when the same `action_name` appears multiple times.

```bash
Tool: get_weather(London)            Tool: get_weather(Paris)
  intercept_context → ref_1            intercept_context → ref_2
  return {..., sourcerykit_ref: ref_1}  return {..., sourcerykit_ref: ref_2}

Agent output:
  claimed_values: [
    {path: "$.current.temperature_2m", value: "15", sourcerykit_ref: ref_1},  ← London
    {path: "$.current.temperature_2m", value: "22", sourcerykit_ref: ref_2},  ← Paris
  ]

Claims:
  claim 1: call_ref=ref_1 → SELECT * FROM intercepts WHERE call_ref = ref_1 → London data ✓
  claim 2: call_ref=ref_2 → SELECT * FROM intercepts WHERE call_ref = ref_2 → Paris data ✓
```


## Environment Configuration

Before running the agent, run the interactive setup wizard to configure your SourceryKit project variables automatically:

```bash
sourcerykit init
```

> [!IMPORTANT]
> The wizard only configures **SOURCERYKIT_*** variables. It does **not** configure your LLM provider infrastructure keys (like `MODEL_NAME` or `ANTHROPIC_API_KEY`). Those must still be set up separately in your environment.

You will also need to set these LLM-provider variables manually:

| Variable | Required | Description |
|---|---|---|
| `MODEL_NAME` | **yes** | Targeted model architecture identifier string passed to create_agent (e.g., `claude-haiku-4-5`). |
| `ANTHROPIC_API_KEY` | **yes** | API authentication token. |

---

## Execution

1. Install the SDK package:
   ```bash
   pip install sourcerykit claude-agent-sdk python-dotenv httpx pydantic
   ```
2. Export your LLM-provider keys into your current shell or place them in a local `.env` file:
   ```bash
   export MODEL_NAME="claude-haiku-4-5"
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
3. Run the example:
      ```bash
      # Standard Validation — both claims PASS
      python agent_run.py

      # or

      # Hallucination Simulation — swap refs → CAUGHT
      python agent_run.py --tamper
   ```
