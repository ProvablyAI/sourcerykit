# Local Model Example — Docker Model Runner + Provably

This example shows how to integrate Provably with a locally running LLM via
[Docker Model Runner](https://docs.docker.com/desktop/features/model-runner/).

The agent:
1. Calls the [Open-Meteo](https://open-meteo.com/) API to fetch the current London temperature.
2. Records the HTTP response via the Provably interceptor.
3. Passes the result to the local LLM and asks it to reason about it.
4. Builds a handoff payload and evaluates it against the indexed data — producing **PASS** or **CAUGHT**.

The `--tamper` flag injects a fake temperature into the claim before evaluation, demonstrating that hallucinated data is reliably detected.

---

## Requirements

### Docker Model Runner

Docker Model Runner is bundled with [Docker Desktop](https://docs.docker.com/desktop/) 4.40+.
Enable it under **Settings → Features in development → Enable Docker Model Runner**.

#### Finding a model on HuggingFace

Browse models at https://huggingface.co/models. On any model page:

1. Click **Use this model**.
2. Select **View all local apps**.
3. Choose **Docker Model Runner** — it will show the exact `docker model pull` command for that model.

Example (Qwen 3.5 0.8B):

```bash
docker model pull huggingface.co/qwen/qwen3.5-0.8b-base
```

Update `_DEFAULT_MODEL` in `agent_run.py` to match the model you pulled, or set it via the `LOCAL_MODEL` environment variable.

Verify the endpoint is reachable:

```bash
curl http://localhost:12434/engines/v1/models
```

> The default endpoint is `http://localhost:12434/engines/v1/chat/completions`.
> Override it with the `LOCAL_MODEL_URL` environment variable if needed.

### Python dependencies

```bash
pip install -e ".[dev]"
```

### PostgreSQL (hosted)

A hosted PostgreSQL instance is required for intercept storage. This demo expects a network-reachable, managed database (local-only Postgres on your laptop is not supported).

Set `POSTGRES_URL` to the DSN/connection string provided by your provider, for example:

```
POSTGRES_URL=postgresql://user:password@db-host.example.com:5432/provably
```

---

## Environment variables

| Variable              | Required | Description                                              |
|-----------------------|----------|----------------------------------------------------------|
| `PROVABLY_API_KEY`    | yes      | Provably integration key                                 |
| `PROVABLY_ORG_ID`     | yes      | Provably organisation ID                                 |
| `PROVABLY_RUST_BE_URL`| yes      | Provably Rust backend base URL                           |
| `POSTGRES_URL`        | yes      | PostgreSQL DSN for intercept storage                     |
| `LOCAL_MODEL_URL`     | no       | Docker Model Runner endpoint URL (default: `http://localhost:12434/engines/v1/chat/completions`) |
| `LOCAL_MODEL`         | no       | Model id to use, as pulled via `docker model pull` (default: `huggingface.co/qwen/qwen3.5-0.8b-base`) |

Copy `implementations/.env.example` to `implementations/.env` and fill in the values, or export them in your shell.

---

## Obtaining environment variables

- **PROVABLY_API_KEY**: Log in to https://app.provably.ai and open *User settings* → *Integrations*. Create a new Integration and copy the generated API key into `PROVABLY_API_KEY`.

- **PROVABLY_ORG_ID**: After signing in to the Provably web app your organisation UUID appears in the URL. For example:

	```
	https://app.provably.ai/org/${PROVABLY_ORG_ID}/data?tab=collections
	```

- **PROVABLY_RUST_BE_URL**: You can usually leave this set to the default value provided in `implementations/.env.example` (for example `https://api.provably.ai`) unless you are running a self-hosted Provably backend.

## Running

```bash
# Normal run — expect PASS
python implementations/local_model/agent_run.py

# Tampered run — expect CAUGHT (fake temperature injected into the claim)
python implementations/local_model/agent_run.py --tamper
```
