# OpenAI Agents SDK

This example demonstrates how to integrate SourceryKit with the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python). It showcases automated intercept capture, target endpoint allow-list constraints, and runtime evaluation loops inside a structured multi-turn agent execution flow.

## Core Pillars Tested

1. **HTTP Interception:** The `bootstrap_system()` hook dynamically monitors `httpx` and `requests` outbound calls, ensuring that network operations generated within the agent loop are securely logged to your database intercepts table.
2. **All-Method Trust Gate:** SourceryKit enforces structural target validation checks against **every HTTP method** (GET, POST, etc.). Consequently, both the external weather lookup endpoint (GET) and the underlying OpenRouter orchestration engine endpoint (POST) are explicitly registered via policy seeds before agent execution.
3. **Automated Handoff:** Captured network states are bundled alongside model generation reasoning strings to establish structured claims verified directly against the backend source of truth.

---

## Environment Configuration

Configure the development tracking workspace using your target system variables or an explicit `.env` file mapping:

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | **yes** | API authentication token for [OpenRouter](https://openrouter.ai/). Used for handling model processing calls (`openai/gpt-4o-mini`). |
| `SOURCERYKIT_API_KEY` | **yes** | Your active integration key obtained from the Provably dashboard. |
| `SOURCERYKIT_ORG_ID` | **yes** | Workspace identifier token used to scope policy queries. |
| `SOURCERYKIT_POSTGRES_URL` | **yes** | Dedicated database DSN string for transaction record persistence. |

---

## Execution Instructions

1. Install the SDK package in editable mode along with developer tools extensions:
   ```bash
   pip install -e ".[dev]"
   ```
2. Export your configured secrets into your current shell:
      ```bash
   export OPENROUTER_API_KEY="sk-or-..."
   export SOURCERYKIT_API_KEY="zk_..."
   export SOURCERYKIT_ORG_ID="org_..."
   export SOURCERYKIT_POSTGRES_URL="postgresql://postgres:postgres@localhost:5432/db"
   ```
3. Run the tracking script:
      ```bash
   python agent_run.py
   ```
