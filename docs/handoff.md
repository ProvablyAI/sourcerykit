# Handoff
The handoff mechanism structures agent claims—such as the result of an API call—and submits them to an evaluation service. These claims are evaluated deterministically against authoritative records to provide verifiable runtime guardrails.

Agent frameworks (OpenAI Agents SDK, LangChain) should use `SourceryKitAgentResponse` as the structured output type. This enforces a typed contract where the LLM returns a `reasoning` string and a `claimed_values` list—a flat collection of `ClaimedValue` objects, each with a JSONPath-style `path` and an extracted string `value`. These `claimed_values` feed directly into the handoff payload.


## Core Flow
- **Collect Claims**: The agent records statements about its actions alongside supporting request/response payloads.
- **Build Payload**: The claims, trusted endpoint snapshots, and execution metadata are compiled into a structured `HandoffPayload`.
- **Evaluate**: The payload is sent to the evaluation service via the SDK, which matches claims against the backend source of truth and returns a verdict.


## Example
The following example demonstrates how to construct a claim, bundle it into a HandoffPayload, and submit it for evaluation:

```python
import uuid
from agents import Agent, Runner
from sourcerykit import build_handoff_payload, evaluate_handoff, SourceryKitAgentResponse

# Set SourceryKitAgentResponse as the structured output type on your agent.
# Pass the keyword argument supported by your framework, e.g.:
#   output_type=SourceryKitAgentResponse   (OpenAI Agents SDK)
#   response_format=SourceryKitAgentResponse  (LangChain)
agent = Agent(
    name="demo",
    instructions="You are a helpful assistant.",
    tools=[...],
    model=MODEL_NAME,
    output_type=SourceryKitAgentResponse,
)
result = await Runner.run(agent, prompt)
final_output: SourceryKitAgentResponse = result.final_output

# Build the handoff payload from the agent's structured output
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

# Assemble the handoff payload using the flat SDK builder
payload = await build_handoff_payload(
    payload_data,
    run_id=uuid.uuid4(),
    intercept_agent_id="demo",
)

# Submit the payload directly to the evaluator
result = await evaluate_handoff(payload)
print(f"Evaluation Verdict: {result.get('outcome')}") 
# Returns: {"outcome": "PASS" | "CAUGHT" | "ERROR", "per_claim": [...], "errors": [...]}
```

## Anatomy of fetch_and_claim
The `build_handoff_payload` function accepts a structured `fetch_and_claim` dictionary. Other runtime fields—such as network intercepts, organization IDs, and API keys—are resolved automatically by the SDK during compilation.

> [!NOTE]
> The fields below represent a complete and exhaustive view of the parameters you can manually configure. Any schema fields omitted from these tables are managed entirely by the SDK lifecycle.

### Payload Input Fields
| Field | Type | Description |
|---|---|---|
| `reasoning` | `str \| None` | Detailing the agent's logic or intent for the overall execution slice. |
| `claims` | `list[HandoffClaim]` | A complete list of raw claim dictionaries to be resolved into execution claims. |


### Claim Input Fields
| Field | Type | Description |
|---|---|---|
| `action_name` | `str` | Logical identifier for the agent action producing the claim. |
| `claimed_value` | `Any` | The specific data value or object subset the agent claims to be true. |
| `verification_mode` | `str` | The verification strategy applied to this specific claim (e.g., `field_extraction`). |
| `range_min` | `float | int | None` | Optional inclusive lower bound boundary used for `range_threshold` mode. |
| `range_max` | `float | int | None` | Optional inclusive upper bound boundary used for `range_threshold` mode. |


## Verification Modes
The evaluation engine processes claims using one of four specific strategies:

- **field_extraction**: Isolates a specific element in the backend record using the `json_path` string and compares it directly to the `claimed_value`.
- **range_threshold**: Verifies that the extracted numeric value matches the `claimed_value` and falls inclusively between defined `range_min` and `range_max` boundaries.


## Evaluation Logic
When evaluate_handoff is invoked:

1. Claims missing a valid `query_record_id` fail immediately with a CAUGHT status.

2. The evaluator securely fetches historical payloads from the backend using the payload credentials.

3. The specified `verification_mode` rules are executed against the fetched records.

4. The transaction yields an overall `PASS` verdict if, and only if, every single inner claim successfully satisfies its verification conditions.

For structural details on database tracking, see [architecture](architecture.md). For automated network capture details, see [intercept](intercept.md).
