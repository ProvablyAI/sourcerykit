# Claude Agent SDK
This example demonstrates how to integrate SourceryKit with the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). It showcases automated intercept capture, target endpoint allow-list constraints, and runtime evaluation loops inside a structured agent execution flow.

## How It Works
1. **HTTP Interception**: The `bootstrap_system()` hook dynamically monitors outbound `httpx` calls, ensuring that network operations generated within the agent tool loop (`get_current_temperature_london`) are securely logged to your database intercepts table.
2. **All-Method Trust Gate**: SourceryKit enforces structural target validation checks against your external network endpoints. The external weather lookup endpoint (`api.open-meteo.com`) is explicitly registered via policy seeds (`insert_trusted_endpoint`) before execution.
3. **Automated Handoff & Evaluation**: Captured network states are bundled alongside the agent's structured `SourceryKitAgentResponse` output. The agent is configured with `output_format={"type": "json_schema", "schema": SourceryKitAgentResponse.model_json_schema()}`, which enforces a typed contract—the LLM returns a `answer` string and a `claimed_values` list of `ClaimedValue` objects (each with a JSONPath `path` and extracted string `value`). These `claimed_values` are passed as the `claimed_value` field in the handoff payload and submitted to `evaluate_handoff` to verify data integrity and catch hallucinations.


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
      # Standard Validation
      python agent_run.py

      # or

      # Hallucination Simulation
      python agent_run.py --tamper
   ```
