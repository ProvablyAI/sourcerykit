# Architecture

The SDK is intentionally small. This document is the map: every module, what
it depends on, and what crosses an I/O boundary.

## Module map

```
src/provably/
  __init__.py             public surface
  log.py                  structlog wrapper used SDK-internally
  common/
    env.py                env-var helpers (get_env_str etc.)
  trusted_endpoints.py    registry DDL + normalization + policy check
  intercept/
    __init__.py           public re-exports of the patch + lifecycle
    interceptor.py        global requests/httpx monkey-patch + simulation hook
    _storage.py           insert into provably_intercepts
    _responses.py         response-body adapters used by the patch
  handoff/
    __init__.py
    client.py             initialize_runtime
    types.py              HandoffPayload v2, HandoffClaim, etc.
    transport.py          post_handoff
    evaluator.py          evaluate_handoff, extract_indexed_from_query_record
    eval_modes.py         the four verification modes
    json_utils.py         canonical_json
    _bootstrap.py         integration cache
    _discovery.py         lookup helpers
    _http.py              shared httpx client config
    _preprocess.py        one-time intercept-table padding
    _resources.py         loader for embedded JSON resources
```

## Dependency rules

Allowed at runtime:

- stdlib
- `httpx`, `requests`
- `pydantic`, `jsonschema`
- `psycopg2-binary` (v0.1 only — see issue
  [#1](https://github.com/ProvablyAI/provably-python-sdk/issues/1))
- `structlog`

Forbidden in `src/provably/`:

- Any web framework (`fastapi`, `flask`, `starlette`, `uvicorn`, `gunicorn`).
- Any agent framework (`langgraph`, `langchain`, `crewai`, `autogen`).
- Any LLM-vendor SDK (`openai`, `anthropic`, etc.).
- Anything that ties the SDK to a specific deployment (`python-dotenv`, app
  config helpers).

The whole point of the split from the demo monorepo was to keep this SDK
vendor-neutral and host-neutral. Any PR that adds a forbidden dependency must
be rejected.

## I/O boundaries

The SDK touches the outside world in exactly four places. Adding a fifth is a
design decision, not an implementation detail.

| Boundary | Modules | Notes |
|---|---|---|
| Postgres write — `provably_intercepts` | `intercept._storage` | Connects via `psycopg2.connect(POSTGRES_URL)`. v0.2 will inject a connection. |
| Postgres read/write — `trusted_endpoints` | `trusted_endpoints` | Caller-provided `conn` everywhere except `check_claim_endpoints_are_trusted`, which still opens its own connection. |
| Postgres write — intercept-table padding | `handoff._preprocess` | Connects via `psycopg2.connect(POSTGRES_URL)` once during `initialize_runtime`. |
| HTTP egress | `handoff.evaluator`, `handoff.transport`, `handoff._bootstrap` | Always uses `httpx` directly so the monkey-patch does not double-count SDK-internal calls. |

The interceptor monkey-patches `requests.get/post` and `httpx.get/post` for
*everyone else* in the process. SDK-internal HTTP calls go through `httpx`
directly to avoid recursion.

## Public-vs-internal contract

- Public: anything in `src/provably/__init__.py`'s `__all__`. Signatures are
  stable; changes are a minor-version bump with a deprecation shim.
- Internal: anything else. Modules with an underscore prefix
  (`handoff._bootstrap`, `intercept._storage`, etc.) may be renamed,
  refactored, or deleted between patch versions.

When in doubt, treat it as internal.

## Lifecycle

```
import provably
provably.initialize_runtime()          # one-time bootstrap; reads env vars
provably.init_interceptor()            # install monkey-patch, set _enabled=True
# ... agent runs, recording rows into provably_intercepts ...
provably.disable()                     # optional: stop recording
provably.enable()                      # resume
provably.post_handoff(url, payload)    # at handoff time
provably.evaluate_handoff(payload, ..) # on the eval-service side
```

`init_interceptor` is idempotent. The v0.2 plan
([#3](https://github.com/ProvablyAI/provably-python-sdk/issues/3)) is to fold
it into `initialize_runtime` so the lifecycle is a single call.

## Why this shape

The goal is that an agent-framework-shaped consumer can adopt the SDK with
roughly four lines of code:

```python
import provably
provably.initialize_runtime()
provably.init_interceptor()
# ... existing agent code, unchanged ...
provably.post_handoff(url, payload)
```

Anything that would require the consumer to refactor their orchestration,
adopt a specific web framework, or change their LLM client belongs outside the
SDK.
