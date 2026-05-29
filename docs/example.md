# End-to-End Walkthrough
This walkthrough breaks down the lifecycle of an autonomous, verifiable agent run using the SourceryKit SDK. You will see how to configure policies, intercept live calls, simulate an LLM reasoning step, and evaluate data integrity.

## Prerequisites
Ensure your environment variables are configured in your shell or a local `.env` file before executing the steps:

```bash
export SOURCERYKIT_API_KEY="your_provably_api_key"
export SOURCERYKIT_ORG_ID="your_provably_org_id"
export SOURCERYKIT_POSTGRES_URL="postgresql://user:password@localhost:5432/your_db"
```

## Step-by-Step Implementation
### Step 1: Initialization and Policy Seeding

First, we bootstrap the global runtime system. This patches supported HTTP libraries (`httpx` and `aiohttp`) process-wide. We then seed our trusted registry with the explicit URL pattern our agent is allowed to query.

```python
import uuid
import json
import copy
import httpx
from sourcerykit import (
    bootstrap_system,
    insert_trusted_endpoint,
    async_intercept_context,
    build_handoff_payload,
    evaluate_handoff,
)

_WEATHER_API_URL = "[https://api.open-meteo.com/v1/forecast](https://api.open-meteo.com/v1/forecast)"

# 1. Fire up the local runtime environment and database connections
await bootstrap_system()

# 2. Add the target API pattern to your real-time allow-list policy registry
await insert_trusted_endpoint(_WEATHER_API_URL)
```

### Step 2: Executing Intercepted Agent Tools
When the agent executes an HTTP request, we wrap it inside `async_intercept_context`. This attaches specific metadata tracking tokens (`agent_id`, `action_name`) to the network transaction. The Interceptor validates the URL against our allow-list, fires the request, and logs the exchange to our append-only database table.

```python
# 3. Execute network requests safely inside an entry intercept context
async with async_intercept_context(agent_id="demo-agent", action_name="get_weather"):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            _WEATHER_API_URL,
            params={"latitude": 51.5074, "longitude": -0.1278, "current": "temperature_2m"},
            timeout=30,
        )
        response.raise_for_status()
        tool_output = response.json()

current_temp = tool_output.get("current", {}).get("temperature_2m")
print(f"Observed temperature from source: {current_temp}°C")
```

### Step 3: LLM Interaction & Claim Extraction
Next, the agent passes the raw tool output data up to its LLM engine to compute decisions or generate user responses. For this walkthrough, we simulate a standard text completion response. We also prepare a dictionary of the information the agent claims it saw.

```python
# 4. Simulate or parse the LLM's generated reasoning text
simulated_reasoning = f"The agent checked the API and confirmed London is at {current_temp}°C."

# Deep-copy the payload to build out our user validation dictionary
claimed_value = copy.deepcopy(tool_output)
```

> [!TIP]
> To simulate a data hallucination or a malicious payload injection, alter your data dictionary here (e.g., `claimed_value["current"]["temperature_2m"] = 99.9`). This discrepancy will be immediately caught by the evaluator in Step 5.

### Step 4: Compiling the Handoff Payload

We bundle our user-defined data structures (`reasoning` and our array of `claims`) into an input dictionary. Passing this to `build_handoff_payload` matches our local session information against the unalterable records captured by the Interceptor in Step 2.

```python
# 5. Compile the user claims into a structured handoff payload
payload_data = {
    "reasoning": simulated_reasoning,
    "claims": [
        {
            "action_name": "get_weather",
            "claimed_value": claimed_value,
            "verification_mode": "verbatim",
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
# 6. Ship the compiled claims down to the validation engine
eval_result = await evaluate_handoff(payload)

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
Modify a field inside your `claimed_value` dictionary right before Step 4 (e.g., `claimed_value["current"]["temperature_2m"] = 99.9`) and execute the script again:

```bash
python sourcerykit_demo.py --tamper
```

Expected engine response:

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