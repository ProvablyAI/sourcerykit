# LangChain Agent

This directory demonstrates how to seamlessly integrate SourceryKit with autonomous agent systems built using the modern [LangChain](https://github.com/langchain-ai/langchain).

## How It Works
1. **Clean Interception:** Your custom LangChain `@tool` block is wrapped in an `async_intercept_context` manager. When the orchestration layer (`create_agent`) triggers the function call, SourceryKit captures and indexes the execution metadata inside your Postgres database.
2. **Data Caching:** The tool securely caches a copy of the raw response dictionary making it accessible once the graph completes its processing turns.
3. **Claim Evaluation:** After `agent.ainvoke()` natively resolves the final conversational output string, the captured execution structure is passed directly to `build_handoff_payload` and evaluated against the tamper-proof baseline records.

---

## Environment Configuration

Configure your environment setup using your shell profile or a local `.env` file mapping:

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | **yes** | Your OpenAI secret key. |
| `SOURCERYKIT_API_KEY` | **yes** | Your active integration token from the Provably dashboard. |
| `SOURCERYKIT_ORG_ID` | **yes** | Your workspace organization UUID. |
| `SOURCERYKIT_POSTGRES_URL` | **yes** | DSN connection string for your hosted Postgres intercept database. |

---

## Execution
1. Install the SDK package:
   ```bash
   pip install sourcerykit
   ```
2. Export your configured secrets into your current shell:
      ```bash
   export OPENAI_API_KEY="sk-or-..."
   export SOURCERYKIT_API_KEY="zk_..."
   export SOURCERYKIT_ORG_ID="org_..."
   export SOURCERYKIT_POSTGRES_URL="postgresql://postgres:postgres@localhost:5432/db"
   ```
3. Run the example:
      ```bash
   python agent_run.py
   ```
