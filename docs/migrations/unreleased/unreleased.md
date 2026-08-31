# Migrating to the unreleased version

<!-- When cutting the release, rename this directory to the version (e.g. `v1_2/v1_2.md`) and update the link in `docs/migrations/README.md` and `CHANGELOG.md`. -->

## Breaking change: user API key replaced by OAuth tokens

The user API key is gone. The SDK authenticates with the OAuth access token (auto-refreshed via the refresh token), and the handoff verify path uses the per-collection **integration key** instead of the user key.

| Previous | New | Notes |
|---|---|---|
| `PROVABLY_API_KEY` | `PROVABLY_ACCESS_TOKEN` | Issued by `sourcerykit init` (browser OAuth) |
| — | `PROVABLY_REFRESH_TOKEN` | Optional in env; rotated automatically by the SDK |

If you construct `Settings` manually, `api_key` is now `access_token` (plus optional `refresh_token`):

```python
# Previous
Settings(api_key="zk-...", org_id=...)

# New
Settings(access_token="...", org_id=...)
```

Other changes:
- `sourcerykit init` no longer mints a user API key.
- `sourcerykit config set --api-key` and the `PROVABLY_API_KEY` display in `config list` are removed.
- New optional `SOURCERYKIT_TOKEN_STORE` — an embedded app can point token rotation at its own `.env` instead of the global config.

### Action required

Re-run the wizard — the old global config holds `api_key` but no `token`:

```bash
sourcerykit init
```

## Breaking change: OAuth browser-only login

`sourcerykit init` no longer accepts `--register`, `--email`, or `--password`. Login is browser-based OAuth (PKCE) only; new accounts are created on the Provably web app during the browser login. `--postgres-url`, `--project-name`, and `--sandbox` still work non-interactively after the one-time browser login.

## Also in this release

- **Idempotent integration bootstrap** — re-running `init`/`doctor --fix` reuses the existing integration (exact collection match) via the new `POST /organizations/{org_id}/integrations/ensure` endpoint, instead of minting a duplicate key and shadow user.

## Schema

No database schema changes.

## Upgrade

```bash
pip install --upgrade sourcerykit
sourcerykit init   # re-authenticate (browser OAuth)
```
