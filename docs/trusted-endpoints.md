# Trusted Endpoints
Trusted Endpoints define exactly which URLs an agent is allowed to contact. With this registry in place, any attempt to reach an unapproved destination is blocked before the request leaves the Python process.

## Core Functions
The registry acts as a database-backed, real-time allow-list for outbound network traffic:

- **Strict Policy Enforcement**: The Interceptor queries this registry before dispatching any HTTP call. Unregistered endpoints are blocked immediately, raising an exception.
- **Instant Propagation**: Additions, or revocations to the database registry take effect across the running process instantly without requiring an application restart.


## Example
All database operations in the SDK are asynchronous. Register a trusted destination during your application's setup or bootstrap phase:

```python
from sourcerykit import insert_trusted_endpoint

# Register an allowed endpoint in the database
await insert_trusted_endpoint(url="https://api.example.com/v1/data")

```

## How the Registry Works
- **URL Normalization**: URLs are standardized before storage and evaluation to prevent evasion via minor string variations.
- **Enforcement Scope**: Enforcement is strictly active with no "warning-only" or dry-run mode.


## Async API Reference
The SDK exposes the following asynchronous functions to manage and query policies:

### Check if an endpoint is trusted
```python
await sourcerykit.trusted_endpoints.is_endpoint_trusted(url: str) -> bool
```
Evaluates whether a given URL is active within the registry. This is called internally by the HTTP Interceptor before every outbound request.

### Register a new trusted endpoint
```python
await sourcerykit.trusted_endpoints.insert_trusted_endpoint(url: str, display_label: str | None = None) -> None
```
Inserts a new endpoint into the database. If the URL is already registered, this operation acts as a no-op.

### List all trusted endpoints
```python
await sourcerykit.trusted_endpoints.list_all_trusted_endpoints() -> list[str]
```
Returns a list of all active, registered endpoint URLs.

### Verify all endpoints in a handoff payload
```python
await sourcerykit.trusted_endpoints.verify_claim_endpoints(payload: HandoffPayload) -> None
```
Scans a handoff payload and verifies that every external URL referenced within it is present in the trusted registry. Raises an exception if an untrusted URL is detected.



For details on how the Interceptor blocks these calls, see [intercept](intercept.md). To see how database tables fit into the wider architecture, see [architecture](architecture.md).
