# Migrating to Unreleased

Changes currently on `main` that have not been tagged as a release yet.

## Breaking change

`SourceryKitAgentResponse.reasoning` has been renamed to `.answer`. The database column, `HandoffPayload`, all query builders, and the UI/dashboard now use `answer`.

Your agent's structured output schema will pick up the new field name automatically. If you call `build_handoff_payload` manually, the `fetch_and_claim` dict now expects `answer` instead of `reasoning`:

```python
# Previous
payload = await build_handoff_payload(
    fetch_and_claim={"reasoning": "...", "claimed_values": [...]},
    prompt="...",
)

# New
payload = await build_handoff_payload(
    fetch_and_claim={"answer": "...", "claimed_values": [...]},
    prompt="...",
)
```

## Schema change

Migration `005` adds an `answer TEXT` column to the `traces` table.

## Upgrade

```bash
pip install --upgrade sourcerykit
sourcerykit upgrade
```
