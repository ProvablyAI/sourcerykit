# Claude Agent SDK
This example demonstrates how to integrate SourceryKit with the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). It showcases automated intercept capture, target endpoint allow-list constraints, and runtime evaluation loops inside a structured agent execution flow.

## How It Works
1. **HTTP Interception**: The `bootstrap_system()` hook dynamically monitors outbound `httpx` calls, ensuring that network operations generated within the agent tool loop (`get_current_temperature_london`) are securely logged to your database intercepts table.
2. **All-Method Trust Gate**: SourceryKit enforces structural target validation checks against your external network endpoints. The external weather lookup endpoint (`api.open-meteo.com`) is explicitly registered via policy seeds (`insert_trusted_endpoint`) before execution.
3. **Automated Handoff & Evaluation**: Captured network states are bundled alongside the agent's structured `SourceryKitAgentResponse` output. The agent is configured with `output_format={"type": "json_schema", "schema": SourceryKitAgentResponse.model_json_schema()}`, which enforces a typed contract—the LLM returns a `reasoning` string and a `claimed_values` list of `ClaimedValue` objects (each with a JSONPath `path` and extracted string `value`). These `claimed_values` are passed as the `claimed_value` field in the handoff payload and submitted to `evaluate_handoff` to verify data integrity and catch hallucinations.


## Environment Configuration
Before running the agent, your environment must be configured with your project keys and storage database URL.

### Option A: The Easy Way (Interactive Wizard)
The fastest way to configure your environment file automatically is to run the interactive setup wizard:

```bash
sourcerykit wizard
```

> [!IMPORTANT]
> The wizard is scoped strictly to **SOURCERYKIT_*** variables. It does **not** configure your LLM provider infrastructure keys (like MODEL_NAME or ANTHROPIC_API_KEY). Those must still be set up separately in your environment.

### Option B: Manual Configuration
Alternatively, you can manually export these environment variables in your terminal or save them inside a local `.env` file (see the [SourceryKit README](https://github.com/ProvablyAI/sourcerykit/blob/main/README.md) for more details on how to get your Organization ID from the URL and your API Key from your dashboard settings):

| Variable | Required | Description |
|---|---|---|
| `MODEL_NAME` | **yes** | Targeted model architecture identifier string passed to create_agent (e.g., `claude-haiku-4-5`). |
| `ANTHROPIC_API_KEY` | **yes** | API authentication token. |
| `PROVABLY_API_KEY` | **yes** | Your active integration key obtained from the Provably dashboard. |
| `SOURCERYKIT_ORG_ID` | **yes** | Workspace identifier token used to scope policy queries. |
| `SOURCERYKIT_POSTGRES_URL` | **yes** | Dedicated database DSN string for transaction record persistence. |

---

## Execution

1. Install the SDK package:
   ```bash
   pip install sourcerykit claude-agent-sdk python-dotenv httpx pydantic
   ```
2. Export your configured secrets into your current shell or place them in a local `.env` file:
      ```bash
   export MODEL_NAME="claude-haiku-4-5"
   export ANTHROPIC_API_KEY="sk-ant-..."
   export PROVABLY_API_KEY="zk_..."
   export SOURCERYKIT_ORG_ID="org_..."
   export SOURCERYKIT_POSTGRES_URL="postgresql://postgres:postgres@remote-host-ip:5432/db"
   ```
3. Run the example:
      ```bash
      # Standard Validation
      python agent_run.py

      # or

      # Hallucination Simulation
      python agent_run.py --tamper
   ```
