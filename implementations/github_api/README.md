# Verifiable GitHub API Calls

This implementation shows an agent-style flow where the SDK verifies a GitHub API
claim before printing the answer.

Flow:

1. Seed `https://api.github.com/repos/{owner}/{repo}` into `trusted_endpoints`.
2. Enable Provably indexing.
3. Call the GitHub REST API through `requests`.
4. Build a handoff payload with a claim about `$.stargazers_count`.
5. Run `evaluate_handoff`.
6. Print the answer only when the evaluation outcome is `PASS`.

## Required environment

```sh
export PROVABLY_RUST_BE_URL="https://api.provably.ai"
export PROVABLY_API_KEY="..."
export PROVABLY_ORG_ID="..."
export POSTGRES_URL="postgresql://..."
```

Optional, but recommended for rate limits:

```sh
export GITHUB_TOKEN="..."
```

## Run

```sh
python implementations/github_api/agent_run.py \
  --repo ProvablyAI/verifiable-data-agentkit
```

To prove the guardrail catches a bad claim:

```sh
python implementations/github_api/agent_run.py \
  --repo ProvablyAI/verifiable-data-agentkit \
  --tamper
```
