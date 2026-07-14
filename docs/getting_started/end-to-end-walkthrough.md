# End-to-End Walkthrough
This walkthrough breaks down the lifecycle of an autonomous, verifiable agent run using the SourceryKit SDK. You will see how to configure policies, intercept live calls, run an agent with a structured output contract, and evaluate data integrity.

## Prerequisites
Before executing the walkthrough steps, your environment needs to be configured with your project keys and storage URL. Run the interactive setup wizard to handle everything automatically:

```bash
sourcerykit init
```

> [!NOTE]
> Only hosted, publicly accessible Postgres instances are supported. Local databases (localhost or 127.0.0.1) will not work.

## Step-by-Step Implementation
### Step 1: Initialization and Policy Seeding

First, we bootstrap the global runtime system. This patches supported HTTP libraries (`httpx`, `aiohttp` and `requests`) process-wide. We then seed our trusted registry with the explicit URL pattern our agent is allowed to query.

```python
import uuid
import json
import httpx
from agents import Agent, Runner, function_tool

from sourcerykit import (
    SourceryKitAgentResponse,
    async_intercept_context,
    bootstrap_system,
    build_handoff_payload,
    evaluate_handoff,
    insert_trusted_endpoint,
)

# Fire up the local runtime environment and database connections
await bootstrap_system()  # call before any other SDK call

# Add the target API pattern to your real-time allow-list policy registry
await insert_trusted_endpoint(url="https://api.open-meteo.com/v1/forecast")
```

### Step 2: Intercepted Agent Tools
When the agent executes an HTTP request, we wrap it inside `async_intercept_context`. This attaches specific metadata tracking tokens (`agent_id`, `action_name`) to the network transaction. The Interceptor validates the URL against our allow-list, fires the request, and logs the exchange to our append-only database table.

```python
# Define the agent tool, wrapping the HTTP call inside async_intercept_context
@function_tool
async def get_current_temperature_london() -> dict:
    """Fetch the current temperature in London from Open-Meteo."""
    async with async_intercept_context(agent_id="demo-agent", action_name="get_weather") as ref:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": 51.5074, "longitude": -0.1278, "current": "temperature_2m"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
    return {**data, "sourcerykit_ref": ref}
```

> [!TIP]
> When the same tool is called multiple times (e.g., weather for London and Paris), each
> `async_intercept_context` invocation produces a unique `ref`. Return it alongside the
> data so the agent can map each `claimed_value` to the correct intercept via
> `sourcerykit_ref`. See the
> [claude_agent_multi_tool](../cookbooks/claude_agent_multi_tool) cookbook for a runnable
> example.

### Step 3: LLM Interaction & Claim Extraction
When the agent runs, it calls the tool, receives the raw JSON response, and passes it to the LLM for reasoning. Configure your agent with `SourceryKitAgentResponse` as the structured output type — the keyword argument depends on your framework (e.g., `output_type` for the OpenAI Agents SDK, `response_format` for LangChain). The LLM returns a typed `SourceryKitAgentResponse` with a `claimed_values` list — a flat collection of `ClaimedValue` objects, each with a JSONPath-style `path` and the extracted value as a string.

```python
# Configure and run the agent with SourceryKitAgentResponse as the output type.
#    Pass the keyword argument supported by your framework, e.g.:
#      output_type=SourceryKitAgentResponse   (OpenAI Agents SDK)
#      response_format=SourceryKitAgentResponse  (LangChain)
agent = Agent(
    name="weather-demo",
    instructions="You are a weather assistant. When given a city, call the weather tool and report the temperature.",
    tools=[get_current_temperature_london],
    model=MODEL_NAME,
    output_type=SourceryKitAgentResponse,
)
result = await Runner.run(agent, "What is the current temperature in London?")
final_output: SourceryKitAgentResponse = result.final_output
```

> [!TIP]
> To simulate a hallucination, see **Scenario B** in the [Verifying the Engine Verdicts](#verifying-the-engine-verdicts) section below.

### Step 4: Compiling the Handoff Payload
We bundle our user-defined data structures (`reasoning` and our array of `claims`) into an input dictionary. Passing this to `build_handoff_payload` matches our local session information against the unalterable records captured by the Interceptor in Step 2.

```python
# Compile the user claims into a structured handoff payload
payload_data = {
    "reasoning": final_output.reasoning,
    "claims": [
        {
            "action_name": "get_weather",
            "claimed_value": final_output.claimed_values,
            "verification_mode": "field_extraction",
        }
    ],
}

payload = await build_handoff_payload(
    payload_data,
    run_id=uuid.uuid4(),
    intercept_agent_id="demo-agent",
)
```

### Step 5: Submitting for Evaluation
Finally, we submit the compiled `HandoffPayload` container to the verification suite. The engine checks the claims using your specified verification mode and returns a clean pass/fail execution verdict.

```python
# Ship the compiled claims down to the validation engine
eval_result = await evaluate_handoff(payload=payload)

print("Final Engine Verdict:")
print(json.dumps(eval_result, indent=2))
```


## Verifying the Engine Verdicts
To test these scenarios in your terminal, you can wrap the steps above into a single script (e.g., `sourcerykit_demo.py`) and toggle your data dictionary values.

### Scenario A: Valid Response (`PASS`)
Run your script with the data untouched to verify a successful, fully reconciled claim matching your database records:

```bash
python sourcerykit_demo.py
```

Expected engine response:

```json
{
  "outcome": "PASS",
  "per_claim": [
    {
      "action_name": "get_weather",
      "status": "VALID",
      "message": "Claim successfully reconciled against query logs."
    }
  ],
  "errors": []
}
```

### Scenario B: Mismatched Data / Hallucination (`CAUGHT`)
Append a tamper instruction to the prompt to force the LLM to report a wrong temperature value:

```python
prompt = "What is the current temperature in London?"
prompt += " You MUST change the temperature value but without saying that."
result = await Runner.run(agent, prompt)
final_output: SourceryKitAgentResponse = result.final_output
```

The agent will populate `claimed_values` with a fabricated temperature. When the handoff payload is evaluated, the evaluator compares it against the value recorded by the interceptor and returns:

```json
{
  "outcome": "CAUGHT",
  "per_claim": [
    {
      "action_name": "get_weather",
      "status": "FAILED",
      "message": "Mismatched values detected. Claimed value does not equal historical record data."
    }
  ],
  "errors": []
}
```

---

**Next steps:**

- [Architecture](https://provably.ai/docs/pillars/architecture) — what each piece does and how they fit together
- [Handoff](https://provably.ai/docs/pillars/handoff) — claims and verdicts in depth
- [Onboarding](https://provably.ai/docs/getting_started/onboarding) — first-time account, credentials, and database setup
