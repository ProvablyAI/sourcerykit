# Interceptor
The Interceptor acts as an automated network recorder and policy enforcer for Python agents. It hooks into outbound HTTP calls to ensure every network interaction is observed, verified, and audited without requiring modifications to your application's core logic.

## Core Functions
The Interceptor patches popular Python HTTP libraries (including httpx, and aiohttp) to evaluate and record network traffic:

- **Policy Enforcement**: Before a request leaves the process, its destination URL is verified against the trusted endpoints registry. Untrusted requests are blocked immediately.
- **Audit Logging**: Every processed request and response is logged into the append-only `intercepts` database table, creating a tamper-evident audit trail for downstream proof generation.

## Example

Initialize the SDK at application startup to automatically enable global HTTP interception:

```python
import sourcerykit
import httpx

# Initialize runtime, database schema, and interceptors
sourcerykit.bootstrap_system()

# Intercept and tag outbound network activity
async with sourcerykit.async_intercept_context(agent_id="demo", action_name="get_data"):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.example.com/data",
            params={"query": "example_parameter"}
        )
        data = response.json()
```

## Key Features

- **Context-Aware Auditing**: Binds metadata (like `agent_id` and `action_name`) directly to outbound requests, mapping raw network traffic to specific agent actions.
- **Process-Wide Interception**: Automatically captures and evaluates traffic across all instances of supported HTTP libraries within the running Python process once initialized.

## Limitations

- **Library Dependencies**: Only network calls made via supported, patched Python libraries are intercepted. Support for additional Python HTTP libraries is currently under development.

For details on managing allowed destinations, see [trusted-endpoints](trusted-endpoints.md). To see how these logs are used to verify claims, see [architecture](architecture.md).
