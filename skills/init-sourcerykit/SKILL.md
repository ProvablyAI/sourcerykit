---
name: init-sourcerykit
description: >
  Use when integrating SourceryKit into an AI agent project. Covers installation,
  environment setup, bootstrapping, HTTP interception, trusted endpoints, handoff
  payloads, and evaluation. Invoke for tasks like "add SourceryKit", "wrap my tool
  with interception", "verify agent output", or "set up verifiable guardrails".
argument-hint: >
    Framework, tool URLs, and target verification flow (field extraction or range threshold)
---


# SourceryKit Integration Guide

SourceryKit is the Python SDK for [Provably](https://provably.ai). It adds verifiable
guardrails to AI agents by intercepting outbound HTTP calls, enforcing endpoint
allow-lists, and evaluating whether an agent's claimed output matches the raw data
that was actually fetched.

## When to Use

- Adding verifiable guardrails to a new or existing AI agent.
- Converting a plain API tool into an intercepted, auditable tool flow.
- Enforcing structured output so claims can be verified against raw responses.
- Investigating why evaluation returns `CAUGHT` (fabricated/altered values detected) or `ERROR` (configuration or connectivity failure).

## Workflow (with decision points)

1. Validate prerequisites.
2. Bootstrap once at startup.
3. Register trusted endpoints.
4. Wrap every outbound HTTP request in an intercept context.
5. Enforce `SourceryKitAgentResponse` (or subclass) as structured output.
6. Build a handoff payload with action names matching intercept labels.
7. Evaluate payload and inspect outcome.
8. If outcome is not `PASS`, notify the user, branch into troubleshooting, and re-run.

### Branching logic

- If you are inside a web framework: run `await bootstrap_system()` in startup/lifespan, never per request.
- If your tool calls multiple external URLs: insert all URLs with `insert_trusted_endpoint(...)` before execution.
- If claimed values must fall within an acceptable numeric range of the intercepted value: use `verification_mode="range_threshold"`; otherwise default to `field_extraction`.
- If evaluation returns `CAUGHT`: verify JSONPath depth and claimed values first.
- If evaluation returns `ERROR`: verify env vars, hosted Postgres connectivity, and bootstrap timing.

## Quick AI Context
> "We are using SourceryKit for verifiable data integrity. All agent execution frameworks must enforce `SourceryKitAgentResponse` (or an explicit subclass) as their structured output signature, all outbound API tool requests must be wrapped within an `async_intercept_context` boundary, and every terminal task must pass a serialized payload to `evaluate_handoff` for verification checking."

## Installation

```bash
pip install sourcerykit python-dotenv
```

Requires **Python 3.12+** and a **hosted PostgreSQL** database (local DBs are not supported).

## Required Environment Variables
Copy this block into a `.env` file at the project root and fill in real values:

```bash
# Provably API key — created under "User settings → API Key → Active key" at https://app.provably.ai
PROVABLY_API_KEY=zk-XXX

# Your organisation UUID — visible in the Provably dashboard settings
SOURCERYKIT_ORG_ID=00000000-0000-0000-0000-000000000000

# Hosted PostgreSQL connection string. Local databases are NOT supported.
SOURCERYKIT_POSTGRES_URL=postgresql://user:password@db-host.example.com:5432/provably
```

Load the file at runtime with `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()  # call before bootstrap_system()
```

Or export the variables directly in your shell / deployment environment.

## Public API

All public symbols are importable directly from `sourcerykit`:

```python
from sourcerykit import (
    bootstrap_system,           # Initialize the SDK (call once at startup)
    insert_trusted_endpoint,    # Register an allowed outbound URL
    async_intercept_context,    # Context manager wrapping an HTTP call
    build_handoff_payload,      # Package agent claims into a verifiable payload
    evaluate_handoff,           # Send the payload to the evaluator and get a verdict
    SourceryKitAgentResponse,   # Pydantic model for structured agent output
    VerificationMode,           # Enum: "field_extraction" | "range_threshold"
)
```


## Integration Pattern (step by step)

### 1 — Bootstrap (once at startup)

```python
await bootstrap_system()
```

This call:
- Validates your environment variables.
- Creates the required database tables automatically (no manual Alembic migration needed).
- Runs the Provably handshake to authenticate your credentials.
- Patches HTTP libraries so the interceptor is active.

**Call it exactly once**, before any other SDK call or agent run.

#### In a standalone script

```python
import asyncio
from dotenv import load_dotenv
from sourcerykit import bootstrap_system

load_dotenv()
asyncio.run(bootstrap_system())  # then run your agent
```

#### In a FastAPI app (or any async framework)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sourcerykit import bootstrap_system

@asynccontextmanager
async def lifespan(app: FastAPI):
    await bootstrap_system()
    yield

app = FastAPI(lifespan=lifespan)
```

For other frameworks: place the `await bootstrap_system()` call inside whatever startup hook runs before requests are served (e.g. Starlette `on_startup`, aiohttp `on_startup`, Django ASGI lifespan). Never call it from inside a request handler.


### 2 — Register trusted endpoints

```python
await insert_trusted_endpoint(url="https://api.example.com/data")
```

Any outbound call to a URL **not** on this list is blocked by the interceptor.
Call this for every external URL the agent is allowed to reach.

### 3 — Wrap outbound HTTP calls in an intercept context

```python
import httpx
from sourcerykit import async_intercept_context

async with async_intercept_context(agent_id="my-agent", action_name="fetch_data"):
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data", ...)
        response.raise_for_status()
```

- `agent_id` — a stable identifier for this agent instance.
- `action_name` — a label that ties this HTTP call to a claim in the handoff payload.

The interceptor logs request + response to the Intercepts table automatically.


### 4 — Use `SourceryKitAgentResponse` as the agent's output type

The agent **must** return a structured response so claimed values can be extracted.

```python
from sourcerykit import SourceryKitAgentResponse
```

Pass it as the structured output type when configuring your agent framework:

| Framework | Keyword argument |
|-----------|-----------------|
| OpenAI Agents SDK | `output_type=SourceryKitAgentResponse` |
| LangChain | `response_format=SourceryKitAgentResponse` |

`SourceryKitAgentResponse` is a Pydantic model with two fields:

```python
class ClaimedValue(BaseModel):
    path: str    # JSONPath-style key, e.g. "$.current.temperature_2m"
    value: str   # The extracted value as a string, e.g. "18.5"

class SourceryKitAgentResponse(BaseModel):
    reasoning: str                    # Human-readable explanation of the result
    claimed_values: list[ClaimedValue]  # Values the LLM says it extracted
```

The LLM populates this automatically when it is set as the structured output type — **no extra prompting is required**. The field descriptions embedded in the schema are enough to guide the model.


### 5 — Customizing Your Agent's Output Schema

If your application requires additional custom fields alongside SourceryKit tracking metrics, simply extend the base structure via standard Pydantic inheritance:

```python
from sourcerykit import SourceryKitAgentResponse
from pydantic import Field

class MyCustomWeatherAgentResponse(SourceryKitAgentResponse):
    """Extend SourceryKit to add custom application fields seamlessly."""
    is_freezing: bool = Field(description="True if temperature is below 0°C.")
    recommended_clothing: str = Field(description="What the user should wear.")
```

Pass `MyCustomWeatherAgentResponse` directly to your agent runner framework. The underlying tracking parameters (`reasoning`, `claimed_values`) are inherited automatically, keeping your telemetry loop completely functional!


### 6 — JSONPath Mapping Standard
To pass evaluation verification flawlessly, ensure your agent maps tool output data shapes to valid JSONPath parameters according to this depth specifier syntax guideline:


| Raw Tool Output Structure | Target `ClaimedValue.path` Specification |
|-----------|-----------------|
| `{"temperature": 18.5}` | `$.temperature` |
| `{"current": {"temp": 18.5}}` | `$.current.temp` |
| `{"hourly": [12.0, 15.5]}` | `$.hourly` (for explicit array indexing parsing) |


The path string **must** exactly match the structural depth of the raw dict returned by the tool function. Do not guess or truncate parent namespaces.


### 7 — Build the handoff payload

```python
import uuid
from sourcerykit import build_handoff_payload

payload = await build_handoff_payload(
    {
        "reasoning": final_output.reasoning,
        "claims": [
            {
                "action_name": "fetch_data",          # must match the intercept context
                "claimed_value": final_output.claimed_values,
                # field_extraction: checks that each ClaimedValue.path/value pair
                #   is present in the raw intercepted response body.
                # range_threshold: checks that a numeric value falls within an
                #   acceptable range of the intercepted value (advanced use case).
                "verification_mode": "field_extraction",
            }
        ],
    },
    run_id=uuid.uuid4(),
    intercept_agent_id="my-agent",                    # must match agent_id above
)
```

### 8 — Evaluate and get a verdict

```python
from sourcerykit import evaluate_handoff

result = await evaluate_handoff(payload=payload)
outcome = result.get("outcome")  # "PASS", "CAUGHT", or "ERROR"
```

- **PASS** — the agent's claimed values match the intercepted data.
- **CAUGHT** — the agent fabricated or altered values.
- **ERROR** — something went wrong during verification.


## End-to-end example (OpenAI Agents SDK)

This is a complete, runnable script. Replace `API_URL`, `MODEL_NAME`, and tool logic
with your own.

```python
import asyncio, uuid, httpx
from dotenv import load_dotenv
from agents import Agent, Runner, function_tool
from sourcerykit import (
    bootstrap_system,
    insert_trusted_endpoint,
    async_intercept_context,
    build_handoff_payload,
    evaluate_handoff,
    SourceryKitAgentResponse,
)

load_dotenv()

API_URL = "https://api.example.com/data"
MODEL_NAME = "gpt-4o"


@function_tool
async def fetch_data() -> dict:
    """Fetch data from the external API."""
    async with async_intercept_context(agent_id="demo", action_name="fetch_data"):
        async with httpx.AsyncClient() as client:
            resp = await client.get(API_URL)
            resp.raise_for_status()
            return resp.json()


async def main() -> None:
    # 1. Bootstrap once
    await bootstrap_system()

    # 2. Register every external URL the agent may call
    await insert_trusted_endpoint(url=API_URL)

    # 3. Configure and run the agent
    agent = Agent(
        name="demo",
        instructions="Use the fetch_data tool, then report the result.",
        tools=[fetch_data],
        model=MODEL_NAME,
        output_type=SourceryKitAgentResponse,   # <-- required
    )
    result = await Runner.run(agent, "Fetch the data and tell me what you got.")
    final_output: SourceryKitAgentResponse = result.final_output

    # 4. Build and evaluate the handoff payload
    payload = await build_handoff_payload(
        {
            "reasoning": final_output.reasoning,
            "claims": [
                {
                    "action_name": "fetch_data",
                    "claimed_value": final_output.claimed_values,
                    "verification_mode": "field_extraction",
                }
            ],
        },
        run_id=uuid.uuid4(),
        intercept_agent_id="demo",
    )

    verdict = await evaluate_handoff(payload=payload)
    print("Outcome:", verdict.get("outcome"))  # PASS, CAUGHT, or ERROR


if __name__ == "__main__":
    asyncio.run(main())
```

## Common mistakes to avoid

| Mistake | Fix |
|---------|-----|
| Calling `bootstrap_system()` more than once | Call it exactly once at process startup |
| `action_name` in the claim doesn't match the intercept context label | They must be identical strings |
| `intercept_agent_id` in `build_handoff_payload` differs from `agent_id` in `async_intercept_context` | They must be the same value |
| Hitting an unregistered URL | Add it with `insert_trusted_endpoint` before the request |
| Using a local Postgres instance | Only hosted, publicly accessible Postgres is supported |
| Forgetting `output_type` / `response_format` on the agent | Without it `claimed_values` will always be empty |
| Calling `bootstrap_system()` inside a request handler | Move it to the app startup / lifespan hook |
| "Cannot run nested event loop" error | You're calling `asyncio.run()` inside an already-running loop — use `await` instead, or use `asyncio.get_event_loop().run_until_complete()` only if no loop is running |


## Completion Checks

Treat integration as done only when all checks pass:

- `bootstrap_system()` is called exactly once during process startup.
- Every outbound network call in agent tools is inside `async_intercept_context(...)`.
- Every outbound URL is registered via `insert_trusted_endpoint(...)`.
- Agent output type is `SourceryKitAgentResponse` (or subclass) and includes non-empty `claimed_values`.
- Each claim `action_name` exactly matches the intercept context `action_name`.
- `intercept_agent_id` exactly matches the context `agent_id`.
- `evaluate_handoff(...)` runs for the terminal payload and returns a handled outcome (`PASS`, `CAUGHT`, or `ERROR`).


## Code Generation Checklist
When generating or refactoring code to support SourceryKit, ensure compliance with these rules:

1. **Tool Wrapping**: Ensure every single external network request inside an agent tool is explicitly wrapped within an `async with async_intercept_context(...)` block.
2. **Schema Binding**: Verify that the agent execution block uses the tracking response schema (`SourceryKitAgentResponse` or a valid subclass) as its strict structured output type mapping constraint.
3. **Identifier Matching**: The action_name string used in the tool context must match the action_name string declared in the claims payload array identically.
4. **Handoff Sequence**: Always follow agent generation steps by forwarding final fields to `build_handoff_payload` and awaiting the results from `evaluate_handoff` before the agent's response is consumed or forwarded downstream.
