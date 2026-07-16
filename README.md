<div align="center">
  <img src="https://raw.githubusercontent.com/ProvablyAI/sourcerykit/refs/heads/main/docs/images/logo.svg" alt="SourceryKit" width="280" />

  <br />

  [![CI](https://github.com/ProvablyAI/sourcerykit/actions/workflows/ci.yml/badge.svg)](https://github.com/ProvablyAI/sourcerykit/actions/workflows/ci.yml)
  [![PyPI version](https://img.shields.io/pypi/v/sourcerykit)](https://pypi.org/project/sourcerykit/)
  [![Python versions](https://img.shields.io/pypi/pyversions/sourcerykit)](https://pypi.org/project/sourcerykit/)
  [![License](https://img.shields.io/pypi/l/sourcerykit)](https://github.com/ProvablyAI/sourcerykit/blob/main/LICENSE.md)
  [![Types: Mypy](https://img.shields.io/badge/types-mypy-blue)](https://mypy-lang.org/)
</div>


SourceryKit is the Python SDK for [Provably](https://provably.ai). It provides verifiable guardrails for AI agents by automatically recording outbound HTTP calls, enforcing endpoint policies, and checking your agent's claims against a source of truth—all before any request leaves your process.

> ⚠️ **IMPORTANT:** Upgrading the SDK from v0.2 to v1.0? See the [v1.0 migration guide](https://github.com/ProvablyAI/sourcerykit/blob/main/docs/migrations/v1_0/v1_0.md).


## How Does It Work?

SourceryKit handles policy enforcement and logging right inside your agent's normal workflow:

<div align="center">
  <img src="https://raw.githubusercontent.com/ProvablyAI/sourcerykit/refs/heads/main/docs/images/architecture.svg" alt="architecture" width="550" />
</div>

### The Pieces

- **HTTP Interceptor**: Patches your HTTP libraries to watch and log outbound calls, blocking untrusted requests on the spot.
- **Trusted Endpoints**: A database allow-list of approved destinations for your agent.
- **Intercepts Table**: An append-only DB table that logs every request and response for auditing.
- **SourceryKitAgentResponse**: A Pydantic model used as the structured response_format for your agent. Enforces a typed response contract with a `claimed_values` list of extracted values.
- **Handoff Payload**: A clean data bundle containing the claims your agent is making about its external actions.
- **Evaluator**: Compares the handoff payload against records in the Provably backend to give you a clear verdict.
- **Provably Backend**: The source of truth that turns your local intercepts into anchored verification proofs.


## Installation

SourceryKit requires **Python 3.12+**. You can grab it directly from source:

```bash
git clone git@github.com:ProvablyAI/sourcerykit.git
pip install -e ./sourcerykit
```

Or install it directly via pip:

```bash
pip install sourcerykit
```


## Configuration
To get things running, SourceryKit must be configured with your project variables. The interactive CLI handles account provisioning, organization workspace initialization, database validation, and persists credentials globally (OS application folder) and locally (project `.env`).

```bash
sourcerykit init
```

The wizard will guide you through:
- **Account Setup & Authorization**: Create a new account or log into an existing one, and select your organization workspace.
- **API Key Generation**: Automatically fetch your SDK API-KEY from your account profile.
- **Database Handshake**: Enter your database details, test the connection, and ensure it's accessible.
- **Save Config**: Automatically write your credentials and tokens straight to a local .env file.

> ⚠️ **IMPORTANT:** The wizard only configures **SOURCERYKIT_*** variables. It does **not** handle third-party LLM provider infrastructure keys, which must still be exported separately.

### Manual configuration (fallback)

Already have credentials, or need to bypass the wizard (CI, containers, debugging)? Environment
variables override the stored config:

```bash
export PROVABLY_API_KEY="..."
export SOURCERYKIT_ORG_ID="..."
export SOURCERYKIT_POSTGRES_URL="postgresql://user:password@host:5432/db"
```

For a full list of CLI commands, check out the [CLI Documentation](https://provably.ai/docs/getting_started/cli) file, or simply run:
```bash
sourcerykit --help
```

For a full list of environment variables, see [.env.example](https://github.com/ProvablyAI/sourcerykit/blob/main/.env.example).

## Quick Example
Here is how to bootstrap the system, run an intercepted request, build a payload, and check if everything passes validation:

```python
import uuid
import httpx
import sourcerykit
from agents import Agent, Runner
from sourcerykit import SourceryKitAgentResponse

async def run_verifiable_agent():
    # 1. Fire up the system
    await sourcerykit.bootstrap_system()

    # 2. Tell the registry which URL is allowed
    await sourcerykit.insert_trusted_endpoint(url="https://api.example.com/data")

    # 3. Make a network call inside an intercept context
    async with sourcerykit.async_intercept_context(agent_id="demo-agent", action_name="get_data"):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.example.com/data",
                params={"query": "example_parameter"}
            )
            response.raise_for_status()

    # 4. Run agent with SourceryKitAgentResponse as the output format
    #    (e.g., output_type=... for OpenAI, response_format=... for LangChain, output_format=... for Claude).
    #    The output is a structured response containing `claimed_values`.
    prompt = "You are a helpful assistant."
    agent = Agent(
        name="demo-agent",
        instructions=prompt,
        tools=[...],
        model="model-name",
        output_type=SourceryKitAgentResponse,
    )
    result = await Runner.run(agent, prompt)
    final_output: SourceryKitAgentResponse = result.final_output

    # 5. Build the handoff payload from the agent's structured output
    payload_data = {
        "reasoning": final_output.reasoning,
        "claims": [
            {
                "action_name": "get_data",
                "claimed_value": final_output.claimed_values,
                "verification_mode": "field_extraction",
            }
        ],
    }

    payload = await sourcerykit.build_handoff_payload(
        payload_data,
        run_id=uuid.uuid4(),
        prompt=prompt,
        intercept_agent_id="demo-agent",
    )

    # 6. Ask the evaluator for a verdict
    result = await sourcerykit.evaluate_handoff(payload=payload)
    print(f"Evaluation Outcome: {result.get('outcome')}") # PASS, CAUGHT, or ERROR
```


## More Docs
Want to dig into the details? Check out our documentation and specific guides:

* **Official Documentation:** Visit [provably.ai/docs](https://provably.ai/docs) for the complete reference.
* [End-to-End Walkthrough](https://provably.ai/docs/getting_started/end-to-end-walkthrough) — Get up and running from scratch.
* [Cookbooks & Examples](https://github.com/ProvablyAI/sourcerykit/tree/main/cookbooks) — Practical recipes and code samples.

### Technical Guides
- [Architecture Overview](https://provably.ai/docs/pillars/architecture)
- [HTTP Interception](https://provably.ai/docs/pillars/interceptor)
- [Managing Trusted Endpoints](https://provably.ai/docs/pillars/trusted-endpoints)
- [Handoff Contracts & Evaluation](https://provably.ai/docs/pillars/handoff)


## Contributing
We welcome fixes, features, and doc updates! Check out [CONTRIBUTING.md](https://github.com/ProvablyAI/sourcerykit/blob/main/CONTRIBUTING.md) to see how to run tests and open up a pull request.

## License

This project is licensed under the [Business Source License 1.1](https://github.com/ProvablyAI/sourcerykit/blob/main/LICENSE.md).

- Copyright © 2026 Provably Technologies LTD
- You may not offer the Software as a commercial hosted service without purchasing a commercial license from [Provably Technologies Ltd](https://provably.ai).
- On 2029-05-07, the license will automatically convert to GPL-3.0-or-later.

See the [LICENSE](https://github.com/ProvablyAI/sourcerykit/blob/main/LICENSE.md) file for full terms and details.
