# LangChain Agent
This example demonstrates how to integrate SourceryKit with LangChain using agent compilation workflows (create_agent). It showcases automated tool intercept capture, target endpoint allow-list constraints, native structured JSON responses via Pydantic, and backend evaluation loops.

## How It Works
1. **HTTP Interception**: The `bootstrap_system()` hook dynamically monitors outbound `httpx` calls, ensuring that network operations generated within the LangChain agent tool loop (`get_current_temperature_london`) are securely logged to your database intercepts table.
2. **All-Method Trust Gate**: SourceryKit enforces structural target validation checks against your external network endpoints. The external weather lookup endpoint (`api.open-meteo.com`) is explicitly registered via policy seeds (`insert_trusted_endpoint`) before execution.
3. **Automated Handoff & Evaluation**: Captured network states are bundled alongside the agent's structured `SourceryKitAgentResponse` output. The agent is configured with `response_format=SourceryKitAgentResponse`, which enforces a typed contract—the LLM returns a `reasoning` string and a `claimed_values` list of `ClaimedValue` objects (each with a JSONPath `path` and extracted string `value`). These `claimed_values` are extracted directly from `result["structured_response"]` and passed to `evaluate_handoff` to verify data integrity and catch hallucinations.

---

## Environment Configuration
Before running the agent, your environment must be configured with your project keys and storage database URL.

### Option A: The Easy Way (Interactive Wizard)
The fastest way to configure your environment file automatically is to run the interactive setup wizard:

```bash
sourcerykit wizard
```

> [!IMPORTANT]
> The wizard is scoped strictly to **SOURCERYKIT_*** variables. It does **not** configure your LLM provider infrastructure keys (like MODEL_NAME or OPENROUTER_API_KEY). Those must still be set up separately in your environment.

### Option B: Manual Configuration
Alternatively, you can manually export these environment variables in your terminal or save them inside a local `.env` file (see the [SourceryKit README](https://github.com/ProvablyAI/sourcerykit/blob/main/README.md) for more details on how to get your Organization ID from the URL and your API Key from your dashboard settings):

| Variable | Required | Description |
|---|---|---|
| `MODEL_NAME` | **yes** | Targeted model architecture identifier string passed to create_agent (e.g., `openrouter:openai/gpt-4o-mini`). |
| `PROVABLY_API_KEY` | **yes** | Your active integration key obtained from the Provably dashboard. |
| `SOURCERYKIT_ORG_ID` | **yes** | Workspace identifier token used to scope policy queries. |
| `SOURCERYKIT_POSTGRES_URL` | **yes** | Dedicated database DSN string for transaction record persistence. |

> [!Note]
> Ensure your underlying model provider's environment variables—such as `OPENROUTER_API_KEY`—are also set as required by your LangChain backend provider setup.

---

## Execution
1. Install dependencies:
   ```bash
   pip install sourcerykit langchain python-dotenv httpx pydantic
   ```
2. Export your configured secrets into your current shell or place them in a local `.env` file:
      ```bash
   export MODEL_NAME="openrouter:openai/gpt-4o-mini"
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
