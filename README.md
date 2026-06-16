<div align="center">
  <img src="https://github.com/ProvablyAI/sourcerykit/blob/main/docs/logo.svg" alt="SourceryKit" width="280" />
</div>

<div align="center">

[![status: v1.0](https://img.shields.io/badge/status-v1.0-blue)](https://github.com/ProvablyAI/sourcerykit/blob/main/CHANGELOG.md)
[![python: 3.12+](https://img.shields.io/badge/python-3.12+-blue)](https://github.com/ProvablyAI/sourcerykit/blob/main/pyproject.toml)
[![license: Proprietary](https://img.shields.io/badge/license-Proprietary-red)](https://github.com/ProvablyAI/sourcerykit/blob/main/LICENSE.md)

</div>

SourceryKit is the Python SDK for [Provably](https://provably.ai). It provides verifiable guardrails for AI agents by automatically recording outbound HTTP calls, enforcing endpoint policies, and checking your agent's claims against a source of truth—all before any request leaves your process.

---

> [!IMPORTANT]
> Upgrading the SDK from v0.2 to v1.0? See the [v1.0 migration guide](https://github.com/ProvablyAI/sourcerykit/blob/main/docs/migrations/v1_0/v1_0.md).


## How Does It Work?

SourceryKit handles policy enforcement and logging right inside your agent's normal workflow:


```mermaid
flowchart TD
  Agent([Agent]) -->|Initializes| Bootstrap[Bootstrap System]
  Bootstrap -->|Configures| Interceptor[HTTP Interceptor]
  Bootstrap -->|Registers| TrustedEndpoints[(Trusted Endpoints)]

  Agent -->|Outbound HTTP| Interceptor
  Interceptor -->|Validates against| TrustedEndpoints
  Interceptor -->|Logs to| Intercepts[(Intercepts Table)]

  Agent -->|Submits| Handoff[Handoff Payload]
  Handoff -->|Verified by| Evaluator[Evaluator]
  Evaluator -->|Queries records| Provably[Provably Backend]
  Provably -->|Generates proofs from| Intercepts
  Evaluator -->|Returns Verdict| Agent
```

### The Pieces

- **HTTP Interceptor**: Patches your HTTP libraries to watch and log outbound calls, blocking untrusted requests on the spot.
- **Trusted Endpoints**: A database allow-list of approved destinations for your agent.
- **Intercepts Table**: An append-only DB table that logs every request and response for auditing.
- **SourceryKitAgentResponse**: A Pydantic model used as the structured response_format for your agent. Enforces a typed response contract with a `claimed_values` list of extracted values.
- **Handoff Payload**: A clean data bundle containing the claims your agent is making about its external actions.
- **Evaluator**: Compares the handoff payload against records in the Provably backend to give you a clear verdict.
- **Provably Backend**: The source of truth that turns your local intercepts into anchored verification proofs.


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
    await sourcerykit.insert_trusted_endpoint("https://api.example.com/data")

    # 3. Make a network call inside an intercept context
    async with sourcerykit.async_intercept_context(agent_id="demo-agent", action_name="get_data"):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.example.com/data",
                params={"query": "example_parameter"}
            )
            response.raise_for_status()

    # 4. Configure your agent with SourceryKitAgentResponse as the structured output type
    #    and run it. Each framework exposes the typed result differently, but the output
    #    is always a SourceryKitAgentResponse with `claimed_values`.
    #    Pass the keyword argument supported by your framework, e.g.:
    #      output_type=SourceryKitAgentResponse   (OpenAI Agents SDK)
    #      response_format=SourceryKitAgentResponse  (LangChain)
    agent = Agent(
        name="demo-agent",
        instructions="You are a helpful assistant.",
        tools=[...],
        model=MODEL_NAME,
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
        intercept_agent_id="demo-agent",
    )

    # 6. Ask the evaluator for a verdict
    result = await sourcerykit.evaluate_handoff(payload)
    print(f"Evaluation Outcome: {result.get('outcome')}") # PASS, CAUGHT, or ERROR
```

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


## Quick Setup Wizard
The fastest way to get everything configured is to use the interactive onboarding wizard. The CLI handles your account provisioning, organization workspace initialization, and real-time validation of your remote Postgres database.

Run the wizard using your package manager or command line entry point:

```bash
sourcerykit wizard
```

The wizard will guide you through:
- **Account Setup & Authorization**: Create a new account or log into an existing one, and select your organization workspace.
- **API Key Generation**: Automatically fetch your SDK API-KEY from your account profile.
- **Database Handshake**: Enter your database details, test the connection, and ensure it's accessible.
- **Save Config**: Automatically write your credentials and tokens straight to a local .env file.


## Configuration
Set up these three environment variables to get things running:
- `SOURCERYKIT_API_KEY` — Your Provably API key (grab this from your dashboard).
- `SOURCERYKIT_ORG_ID` — Your organization ID (grab this from your dashboard).
- `SOURCERYKIT_POSTGRES_URL` — The connection string for your Postgres database, used for storing intercepts and trusted endpoints. Only PostgreSQL is supported. Format: `postgresql://user:password@ipaddress:port/database_name`

> [!NOTE]
> Only hosted, publicly accessible Postgres instances are supported. Local databases will not work.

You can set these in your shell, a .env file, or your deployment environment. For a full list of options, see [.env.example](https://github.com/ProvablyAI/sourcerykit/blob/main/.env.example).


## More Docs
Want to dig into the details? Check out the specific guides:

- [Architecture Overview](https://github.com/ProvablyAI/sourcerykit/blob/main/docs/architecture.md)
- [HTTP Interception](https://github.com/ProvablyAI/sourcerykit/blob/main/docs/intercept.md)
- [Managing Trusted Endpoints](https://github.com/ProvablyAI/sourcerykit/blob/main/docs/trusted-endpoints.md)
- [Handoff Contracts & Evaluation](https://github.com/ProvablyAI/sourcerykit/blob/main/docs/handoff.md)


## Contributing
We welcome fixes, features, and doc updates! Check out [CONTRIBUTING.md](https://github.com/ProvablyAI/sourcerykit/blob/main/CONTRIBUTING.md) to see how to run tests and open up a pull request.

## License

This project is licensed under the [Business Source License 1.1](https://github.com/ProvablyAI/sourcerykit/blob/main/LICENSE.md).

- Copyright © 2026 Provably Technologies LTD
- You may not offer the Software as a commercial hosted service without purchasing a commercial license from [Provably Technologies Ltd](https://provably.ai).
- On 2029-05-07, the license will automatically convert to GPL-3.0-or-later.

See the [LICENSE](https://github.com/ProvablyAI/sourcerykit/blob/main/LICENSE.md) file for full terms and details.
