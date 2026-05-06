# Handoff

The handoff pillar is the wire contract between an agent that *makes claims*
and an **eval service** that *checks those claims deterministically against
a Provably query record*. (Naming note: this is **eval** /
"verifiable guardrails" — distinct from proof _verification_, which is a
reserved term in the wider Provably product.)

## `HandoffPayload` v2

`HandoffPayload` is a Pydantic v2 model. The currently-shipping wire version
is `"2.0"`; bumping it is a breaking change.

| Field | Type | Meaning |
|---|---|---|
| `provably_org_id` | `str` | Org that owns the query records being eval'd. |
| `integration_api_key` | `str` | API key the eval service uses to fetch query records. |
| `provably_mcp_url` | `str` | Optional MCP endpoint hint. |
| `handoff_evaluate_url` | `str` | Optional eval-service URL hint (set by Cluster A; ignored by the SDK). |
| `handoff_contract_version` | `str` | `"2.0"`. |
| `handoff_field_guide` | `dict[str, str]` | Optional human-readable field doc embedded in the payload. |
| `instructions` | `str` | Free-form instructions surfaced to the eval service. |
| `query_record_ids` | `list[str]` | Top-level list of record ids referenced by the claims. |
| `query_record_urls` | `list[str]` | Optional matching list of record URLs. |
| `trusted_endpoint_registry` | `list[str]` | Snapshot of the trusted endpoints at handoff time. |
| `claims` | `list[HandoffClaim]` | The actual claims (see below). |
| `verification_results` | `list[str]` | Filled in by the eval service; agent leaves it empty. (Field name kept for backward compatibility.) |
| `task` | `str` | Free-form task label. |
| `reasoning` | `str` | Optional summary. |
| `run_id` | `str \| None` | Simulation/run identifier. |
| `sdk_precheck` | `dict \| None` | Optional precheck metadata. |

`HandoffClaim` is one row of the claim list:

| Field | Type | Meaning |
|---|---|---|
| `action_name` | `str` | Logical name of the action that produced this claim. |
| `claimed_value` | `Any` | What the agent says is true. |
| `request_payload` | `dict[str, Any]` | What the agent sent (URL, query, headers, etc.). |
| `response_payload` | `Any` | What the agent received (optional; the indexed record is the source of truth). |
| `query_record_id` | `str` | The Provably query record this claim should be eval'd against. |
| `verification_mode` | `Literal["verbatim", "field_extraction", "schema_type", "range_threshold"]` | Eval comparison mode (field name kept for backward compatibility — semantically these are eval-comparison modes, not proof-verification modes). See below. |
| `json_path` | `str` | Dot path into the indexed payload. Empty = root. |
| `expected_json_schema` | `dict \| None` | Required for `schema_type`. |
| `range_min`, `range_max` | `float \| int \| None` | Required for `range_threshold`. |

## Transport

```python
from provably import HandoffPayload, post_handoff

post_handoff(
    "https://my-eval-service.example",
    payload,
    headers={"x-trace-id": "..."},
    timeout_s=120.0,
)
```

`post_handoff` does exactly four things:

1. Strips trailing `/` from the base URL.
2. Appends `/handoffs/receive`.
3. Serializes the payload via `payload.model_dump(mode="json")`.
4. POSTs with `Content-Type: application/json` and raises on non-2xx.

There is no retry, no batching, no fallback. Failures bubble up as
`httpx.HTTPError` / `httpx.HTTPStatusError`.

The `receiver_url` is supplied by the caller — the SDK does not read it from the
environment or assume any default. Configuration of where YOUR verifier lives
belongs in your application, not the SDK.

## Eval comparison modes

(Stored in the `verification_mode` field — name kept for backward
compatibility; these are not proof-verification modes.)

### `verbatim` (default)

Canonical-JSON equality between `claimed_value` and the indexed value (or the
`json_path` slice of it). Use this when the agent claims to have received the
exact body that the indexed record holds.

### `field_extraction`

Equality on the value at `json_path` only. Use this when the agent claims a
specific field of the response, not the whole body.

### `schema_type`

`claimed_value` is **ignored**. The value at `json_path` is validated against
`expected_json_schema` (a JSON Schema dict). Use this when the agent does not
make a value claim, only a structural one ("the response had an array of
integers at `items`").

### `range_threshold`

`claimed_value` must be numeric, must equal the numeric value at `json_path`,
**and** must lie in `[range_min, range_max]` (inclusive). Use this for
numeric claims with a tolerance band.

## `evaluate_handoff`

```python
from provably import evaluate_handoff

result = evaluate_handoff(payload, provably_base_url="https://api.provably.ai")
# {"outcome": "PASS" | "CAUGHT", "per_claim": [...], "errors": [...]}
```

For each claim:

1. If `query_record_id` is empty, the claim is `CAUGHT` with detail
   `"missing query_record_id"`.
2. The evaluator fetches
   `{base}/api/v1/organizations/{org}/queries/{query_record_id}` with
   `x-api-key: {integration_api_key}`.
3. The indexed value is extracted from the record (preferring `result`, then
   `indexed_value`, `response`, `raw_response`, `data`, `output`; recursing
   into a nested `query` dict if present).
4. The claim is dispatched to the appropriate eval comparison mode.

The handoff outcome is `PASS` only if every claim's `result` is `PASS`. Any
HTTP error during fetch is recorded both in the claim's `result` (as
`CAUGHT`) and at the top level in `errors`.

## Wire example

```json
{
  "provably_org_id": "org-1",
  "integration_api_key": "sk_...",
  "handoff_contract_version": "2.0",
  "task": "discharge_summary",
  "claims": [
    {
      "action_name": "lookup_patient",
      "claimed_value": {"name": "Jane Doe", "mrn": "X123"},
      "request_payload": {"url": "https://api.example.com/patients/42"},
      "query_record_id": "qr_abc",
      "verification_mode": "verbatim",
      "json_path": ""
    }
  ]
}
```

## Things this contract does not do

- It does not carry the agent's chain-of-thought.
- It does not carry the LLM-rendered prose response to the user.
- It does not authenticate the agent itself — the eval service trusts that
  the embedded `integration_api_key` is the right key to fetch records on
  the agent's behalf, no more.
