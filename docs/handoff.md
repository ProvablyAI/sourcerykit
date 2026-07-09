# Handoff
The handoff mechanism structures agent claims—such as the result of an API call—and submits them to an evaluation service. These claims are evaluated deterministically against authoritative records to provide verifiable runtime guardrails.

## Core Flow
- **Collect Claims**: The agent records statements about its actions alongside supporting request/response payloads.
- **Build Payload**: The claims, trusted endpoint snapshots, and execution metadata are compiled into a structured `HandoffPayload`.
- **Evaluate**: The payload is sent to the evaluation service via the SDK, which matches claims against the backend source of truth and returns a verdict.


## The agent's structured output: `SourceryKitAgentResponse`
Claims originate from the agent itself, not from your code. Agent frameworks (OpenAI Agents SDK, LangChain) bind `SourceryKitAgentResponse` as the structured output type — `output_type=` for the OpenAI Agents SDK, `response_format=` for LangChain — so the LLM is forced to return this typed contract instead of free-form text.

`SourceryKitAgentResponse` has two fields:

| Field | Type | Description |
|---|---|---|
| `reasoning` | `str` | The agent's explanation of its actions for this execution slice. |
| `claimed_values` | `list[ClaimedValue]` | A **flat list** of the values the agent claims it produced (see below). |

Each `ClaimedValue` in that list has three string fields — nothing else:

| Field | Type | Description |
|---|---|---|
| `path` | `str` | JSONPath into the tool output, e.g. `$.base_experience`. |
| `value` | `str` | The extracted value, as a string. |
| `sourcerykit_ref` | `str` | Copied verbatim from the tool call's `sourcerykit_ref` return, so the claim maps to the recorded call. Mandatory. |

`final_output.claimed_values` feeds directly into the handoff payload — you pass the list straight through, as shown in the [Example](#example) and payload tables below.

> [!IMPORTANT]
> `claimed_values` must be the agent's own structured output. Bind `SourceryKitAgentResponse`
> (see the [cookbooks](../cookbooks)) and pass `final_output.claimed_values` straight through —
> do not assemble the list yourself from the fetched data.
>
> A *wrong-shaped* hand-built claim (a dict of your own keys like `{"hint_weight": 90, ...}`)
> resolves **zero** claims — `evaluate_handoff` returns `ERROR` with an empty `per_claim`. But a
> *correctly-shaped* hand-built claim is the more dangerous case: it can return `PASS` and still
> prove nothing, because you have only compared the fetched data to itself. SourceryKit exists to
> catch a value **the agent got wrong**; if you build the claim from the data by hand there is no
> independent agent claim to check. The verification is only meaningful when the values are what
> the agent actually declared.


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
result = await evaluate_handoff(payload=payload)
print(f"Evaluation Verdict: {result.get('outcome')}")
# Returns: {"outcome": "PASS" | "CAUGHT" | "ERROR", "per_claim": [...], "errors": [...]}
```

`outcome` is the overall verdict:

- `PASS` — every claim was verified against the recorded data and matched.
- `CAUGHT` — at least one claim did not match the recorded data, or used an untrusted endpoint.
- `ERROR` — nothing could be verified (for example, no claim matched an intercept record).
  Verifying zero claims always resolves to `ERROR`, never `PASS`.

## Anatomy of the payload_data
The `build_handoff_payload` function accepts a structured `payload_data` dictionary. Other runtime fields—such as network intercepts, organization IDs, and API keys—are resolved automatically by the SDK during compilation.

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
| `claimed_value` | `list[ClaimedValue]` | The agent's `claimed_values` — pass `final_output.claimed_values` straight through. See [`SourceryKitAgentResponse`](#the-agents-structured-output-sourcerykitagentresponse) for the shape. Not an arbitrary dict of your own field names. |
| `verification_mode` | `str` | The verification strategy applied to this specific claim (e.g., `field_extraction`). |
| `range_min` | `float | int | None` | Optional inclusive lower bound boundary used for `range_threshold` mode. |
| `range_max` | `float | int | None` | Optional inclusive upper bound boundary used for `range_threshold` mode. |


## Verification Modes
The evaluation engine processes claims using one of four specific strategies:

- **field_extraction**: Isolates a specific element in the backend record using the `json_path` string and compares it directly to the `claimed_value`.
- **range_threshold**: Verifies that the extracted numeric value matches the `claimed_value` and falls inclusively between defined `range_min` and `range_max` boundaries.


## Evaluation Logic
When `evaluate_handoff` is invoked, the evaluator validates data integrity through a multi-layered trust gate:

1. **Pre-Flight Check**: Any claim missing a valid `query_record_id` fails immediately with a CAUGHT status.

2. **Retrieve Logs & Proof**: The engine uses the payload credentials to fetch the original HTTP query logs, response headers, and the cryptographic proof recorded during the interception phase.

3. **Verify Cryptographic Proof**: Before running any logical data checks, the engine validates the proof of the retrieved logs. This guarantees that:
   - The network response was actually captured by the runtime agent.
   - The logged data has not been modified or tampered with since it was written to the database.

4. **Run Verification Rules**: The engine applies your chosen `verification_mode` (such as an `field_extraction`) against the cryptographically verified records.

5. **Final Verdict**: The run receives a final PASS verdict only if the cryptographic proof is valid and every individual claim satisfies its verification rules.

For details on how database logging works, see [architecture](architecture.md). To learn how HTTP requests are captured in real-time, see [intercept](intercept.md).
