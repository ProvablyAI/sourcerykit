# Intercept

The intercept pillar gives any Python process a deterministic record of every
outbound HTTP call without changing the call sites.

## Lifecycle

```python
import provably

provably.initialize_runtime()   # one-time bootstrap; safe to call once per process
provably.init_interceptor()     # install the patch; sets enabled=True
# ... HTTP traffic flows; rows land in provably_intercepts ...
provably.disable()              # stop recording, patch still installed
provably.enable()               # resume
provably.is_enabled()           # bool
```

`init_interceptor` is idempotent. After the first call:

- `requests.get`, `requests.post`, `httpx.get`, `httpx.post` are wrapped.
- The originals are stashed at `provably.intercept.interceptor._orig` for the
  test suite.
- `_enabled` is `True`. Calling `disable()` flips this without unpatching.

## What gets stored

For every successful call, the storage layer writes one row into
`provably_intercepts` containing:

- `url`, `method`
- `request_payload` — caller-supplied query / body / headers (canonicalized)
- `response_payload` — raw response body, **before** any simulation hook runs
- `agent_id`, `action_name`, `intercept_index` — values set via
  `set_interceptor_context`
- timestamp

The original wire response is captured first; mutation (if any) happens after
the row is written. This is the invariant that makes the dashboard's "edit
intercept body and replay" feature safe — ground truth in Postgres is never
overwritten.

## Tagging the next intercept

```python
provably.set_interceptor_context(
    agent_id="cluster_a",
    action_name="lookup_patient",
    intercept_index=0,
)
response = requests.get("https://api.example.com/patients/42")
```

The context is held in a `ContextVar`, so it is per-coroutine / per-thread.
Setting it once before a logical step tags every intercept that step makes.

To get the row id of the most recent insert (e.g. to attach it to a downstream
log line):

```python
row_id = provably.take_last_intercept_row_id()
```

`take_*` clears the slot, so each call returns the id once.

## Optional response-body hook

After a row is stored, an optional callback can change what the **caller** sees (tests, UIs, etc.):

```python
def hook(intercept_index: int, raw_body: Any) -> Any:
    return {"user_edited": True} if some_condition else raw_body

provably.set_intercept_body_hook(hook)
```

It receives the raw body after insert; the DB row is unchanged. Host code (e.g. a
simulation dashboard) can read any env it wants inside the hook.

If the hook returns the same object it received (`raw is mutated`), the
original `requests.Response` / `httpx.Response` is returned unmodified. If
it returns a different object, the response is wrapped so `.json()` and
`.text` reflect the override while status code, headers, and `raise_for_status`
remain intact.

## Trusted-endpoint enforcement

`GET`s are checked against `trusted_endpoints` before any insert. If the
normalized URL is not present for the agent's org, the wrapped call raises:

```
RuntimeError: BLOCKED: https://api.example.com/x not in trusted_endpoints for org=...
```

`POST`s are not policed in v0.1.

## Caveats

- The patch is **global**. Every consumer of `requests` and `httpx` in the
  process gets observed. This is intentional for the demo flow but means hosts
  that need a request-scoped opt-out should wrap calls in
  `provably.disable()` / `provably.enable()`.
- Subprocesses, threads spawned before `init_interceptor`, and other languages
  in the process are **not** observed.
- The patch wraps the module-level functions, not `requests.Session.get` or
  `httpx.Client.get`. Calls that go through a long-lived session or client
  bypass the patch. This is a known gap; see the SDK roadmap.
- `_insert_row` swallows DB errors and never re-raises into the caller. The
  caller's HTTP call always succeeds or fails on its own merits, regardless of
  whether storage worked.
