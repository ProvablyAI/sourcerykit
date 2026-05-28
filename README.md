# SourceryKit SDK
[![status: v0.2](https://img.shields.io/badge/status-v0.2-blue)](CHANGELOG.md)
[![python: 3.12+](https://img.shields.io/badge/python-3.12+-blue)](pyproject.toml)
[![license: Proprietary](https://img.shields.io/badge/license-Proprietary-red)](LICENSE.md)

SourceryKit is the Python SDK for [Provably](https://provably.ai). It provides verifiable guardrails for AI agents by automatically recording outbound HTTP calls, enforcing endpoint policies, and checking your agent's claims against a source of truth—all before any request leaves your process.


## How Does It Work?

SourceryKit handles policy enforcement and logging right inside your agent's normal workflow:


```{mermaid}
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
- **Handoff Payload**: A clean data bundle containing the claims your agent is making about its external actions.
- **Evaluator**: Compares the handoff payload against records in the Provably backend to give you a clear verdict.
- **Provably Backend**:The source of truth that turns your local intercepts into anchored verification proofs.


## Quick Example
Here is how to bootstrap the system, run an intercepted request, build a payload, and check if everything passes validation:

```python
import uuid
import httpx
import sourcerykit

async def run_verifiable_agent():
    # 1. Fire up the system 
    sourcerykit.bootstrap_system()

    # 2. Tell the registry which URL is allowed
    await sourcerykit.trusted_endpoints.insert_trusted_endpoint("[https://api.example.com/data](https://api.example.com/data)")

    # 3. Make a network call inside an intercept context
    async with sourcerykit.async_intercept_context(agent_id="demo-agent", action_name="get_data"):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "[https://api.example.com/data](https://api.example.com/data)",
                params={"query": "example_parameter"}
            )
            record = response.json()

    # 4. Set up the claim data
    payload_data = {
        "reasoning": "Agent completed processing and claims the returned value is valid.",
        "claims": [
            {
                "action_name": "get_data",
                "claimed_value": record,
                "verification_mode": "verbatim",
            }
        ],
    }

    # 5. Build the handoff payload
    payload = await sourcerykit.handoff.build_handoff_payload(
        payload_data,
        run_id=uuid.uuid4(),
        intercept_agent_id="demo-agent",
    )

    # 6. Ask the evaluator for a verdict
    result = await sourcerykit.evaluator.evaluate_handoff(payload)
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


## Configuration
Set up these three environment variables to get things running:
- `SOURCERYKIT_API_KEY` — Your Provably API key (grab this from your dashboard).
- `SOURCERYKIT_ORG_ID` — Your organization ID (grab this from your dashboard).
- `SOURCERYKIT_POSTGRES_URL` — The connection string for your Postgres database, used for storing intercepts and trusted endpoints. Only PostgreSQL is supported. Format: `postgresql://user:password@ipaddress:port/database_name`

Note: Only hosted, publicly accessible Postgres instances are supported. Local or embedded databases will not work.

You can set these in your shell, a .env file, or your deployment environment. For a full list of options, see [.env.example](.env.example).

## More Docs
Want to dig into the details? Check out the specific guides:

- [Architecture Overview](docs/architecture.md)
- [HTTP Interception](docs/intercept.md)
- [Managing Trusted Endpoints](docs/trusted-endpoints.md)
- [Handoff Contracts & Evaluation](docs/handoff.md)


## Contributing
We welcome fixes, features, and doc updates! Check out CONTRIBUTING.md to see how to run tests and open up a pull request.

## License

This project is licensed under the [Business Source License 1.1](LICENSE.md).

- Copyright © 2026 Provably Technologies LTD
- You may not offer the Software as a commercial hosted service without purchasing a commercial license from [Provably Technologies Ltd](https://provably.ai).
- On 2029-05-07, the license will automatically convert to GPL-3.0-or-later.

See the [LICENSE](LICENSE.md) file for full terms and details.
