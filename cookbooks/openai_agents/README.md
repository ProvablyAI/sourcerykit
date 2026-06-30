# OpenAI Agents SDK

This example demonstrates how to integrate SourceryKit with the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python). It showcases automated intercept capture, target endpoint allow-list constraints, and runtime evaluation loops inside a structured agent execution flow.

## How It Works
1. **HTTP Interception**: The `bootstrap_system()` hook dynamically monitors outbound `httpx` calls, ensuring that network operations generated within the agent tool loop (`get_current_temperature_london`) are securely logged to your database intercepts table.
2. **All-Method Trust Gate**: SourceryKit enforces structural target validation checks against your external network endpoints. The external weather lookup endpoint (`api.open-meteo.com`) is explicitly registered via policy seeds (`insert_trusted_endpoint`) before execution.
3. **Automated Handoff & Evaluation**: Captured network states are bundled alongside the agent's structured `SourceryKitAgentResponse` output. The agent is configured with `output_type=SourceryKitAgentResponse`, which enforces a typed contract—the LLM returns a `reasoning` string and a `claimed_values` list of `ClaimedValue` objects (each with a JSONPath `path` and extracted string `value`). These `claimed_values` are passed as the `claimed_value` field in the handoff payload and submitted to `evaluate_handoff` to verify data integrity and catch hallucinations.

---

## Environment Configuration
Before running the agent, run the interactive setup wizard to configure your SourceryKit project variables automatically:

```bash
sourcerykit init
```

> [!IMPORTANT]
> The wizard only configures **SOURCERYKIT_*** variables. It does **not** configure your LLM provider infrastructure keys (like `MODEL_URL` or `MODEL_API_KEY`). Those must still be set up separately in your environment.

You will also need to set these LLM-provider variables manually:

| Variable | Required | Description |
|---|---|---|
| `MODEL_URL` | **yes** | Base URL routing endpoint for the LLM processing interface (e.g., `https://openrouter.ai/api/v1`). |
| `MODEL_API_KEY` | **yes** | API authentication token for the targeting model processing engine. |
| `MODEL_NAME` | **yes** | Targeted model engine name (e.g., `openai/gpt-4o-mini`). |

---

## Execution

1. Install the SDK package:
   ```bash
   pip install sourcerykit openai-agents python-dotenv httpx pydantic
   ```
2. Export your LLM-provider keys into your current shell or place them in a local `.env` file:
   ```bash
   export MODEL_URL="https://openrouter.ai/api/v1"
   export MODEL_API_KEY="sk-or-..."
   export MODEL_NAME="openai/gpt-4o-mini"
   ```
3. Run the example:
      ```bash
      # Standard Validation
      python agent_run.py

      # or

      # Hallucination Simulation
      python agent_run.py --tamper
   ```
