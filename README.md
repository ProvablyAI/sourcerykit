# provably-sdk

Python SDK for [Provably](https://provably.ai). Imports as `provably`.

Surface (v0.1):

- **init** — one-time runtime bootstrap (`initialize_runtime`).
- **intercept** — monkey-patches `requests` and `httpx` to record each HTTP response into the `provably_intercepts` Postgres table; trusted-endpoint allow-list enforced before any insert.
- **handoff** — Pydantic `HandoffPayload` v2, JSON transport (`post_handoff`), per-claim verification modes.
- **eval** — deterministic evaluator (`evaluate_handoff`) that scores a `HandoffPayload` against Provably query records and returns `PASS` / `CAUGHT` per claim.
- **trusted endpoints** — DDL, normalization, and policy checks for the `trusted_endpoints` registry.

## Install

```bash
pip install provably-sdk
```

The PyPI distribution name is `provably-sdk`; the import name is `provably`.

## Quick start

```python
import provably

provably.initialize_runtime()
provably.init_interceptor()
provably.enable()

import requests
requests.get("https://my-trusted-endpoint.example/data")

from provably.handoff.types import HandoffPayload
from provably.handoff.transport import post_handoff

payload = HandoffPayload(...)
post_handoff("https://my-cluster-b.example", payload)
```

## Required environment variables (v0.1)

| Variable | Used by |
|---|---|
| `PROVABLY_API_KEY` | handoff client + bootstrap |
| `PROVABLY_ORG_ID` | handoff client + intercept allow-list |
| `PROVABLY_RUST_BE_URL` | handoff client + evaluator |
| `POSTGRES_URL` | intercept storage, trusted endpoints, handoff preprocess |
| `PROVABLY_APP_UI_URL` | optional, used to build Provably UI links |

A typed `Provably(api_key=..., org_id=..., ...)` client that replaces these globals is planned for v0.2.

## What the interceptor does

`init_interceptor()` monkey-patches `requests.get/post` and `httpx.get/post` globally. Every successful HTTP call is canonicalized and inserted into `provably_intercepts`. GETs to URLs not in the `trusted_endpoints` registry for the current org raise `RuntimeError("BLOCKED: ...")` before insertion.

Call `disable()` to stop recording, `enable()` to resume, `is_enabled()` to query state.

## Status

v0.1 — first extracted release. License: Proprietary. See `LICENSE.md`.
