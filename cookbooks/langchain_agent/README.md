# LangChain Agent
This example demonstrates how to integrate SourceryKit with [LangChain](https://github.com/langchain-ai/langchain) using agent compilation workflows (create_agent). It showcases automated tool intercept capture, target endpoint allow-list constraints, native structured JSON responses via Pydantic, and backend evaluation loops.

## How It Works
1. **HTTP Interception**: The `bootstrap_system()` hook dynamically monitors outbound `httpx` calls, ensuring that network operations generated within the LangChain agent tool loop (`get_current_temperature_london`) are securely logged to your database intercepts table.
2. **All-Method Trust Gate**: SourceryKit enforces structural target validation checks against your external network endpoints. The external weather lookup endpoint (`api.open-meteo.com`) is explicitly registered via policy seeds (`insert_trusted_endpoint`) before execution.
3. **Automated Handoff & Evaluation**: Captured network states are bundled alongside the agent's structured `SourceryKitAgentResponse` output. The agent is configured with `response_format=SourceryKitAgentResponse`, which enforces a typed contract—the LLM returns a `reasoning` string and a `claimed_values` list of `ClaimedValue` objects (each with a JSONPath `path` and extracted string `value`). These `claimed_values` are extracted directly from `result["structured_response"]` and passed to `evaluate_handoff` to verify data integrity and catch hallucinations.

---

## Environment Configuration
Before running the agent, run the interactive setup wizard to configure your SourceryKit project variables automatically:

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
   pip install sourcerykit langchain python-dotenv httpx pydantic
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
