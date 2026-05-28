"""
Demo: GitHub API + Provably interception -> handoff -> evaluate.

The script calls the GitHub REST API, makes a claim about the repo's star count,
and verifies that claim against the intercepted API response before printing the
answer.

Prerequisites:
    PROVABLY_API_KEY
    PROVABLY_ORG_ID
    PROVABLY_RUST_BE_URL
    POSTGRES_URL

Optional:
    GITHUB_TOKEN

Run:
    python implementations/github_api/agent_run.py --repo ProvablyAI/verifiable-data-agentkit
    python implementations/github_api/agent_run.py --repo ProvablyAI/verifiable-data-agentkit --tamper
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import psycopg2
import requests

import provably.runtime as provably_runtime
from provably.handoff.evaluator import evaluate_handoff
from provably.handoff.payload_builder import build_handoff_payload
from provably.intercept import intercept_context, take_last_intercept_row_id
from provably.trusted_endpoints import ensure_trusted_endpoints_table, normalize_url_for_trust

_GITHUB_REPO_PATTERN = "https://api.github.com/repos/{owner}/{repo}"
_AGENT_ID = "github_agent"
_ACTION_NAME = "github_get_repo"


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _seed_trusted_endpoint() -> None:
    postgres_url = _require_env("POSTGRES_URL")
    org_id = _require_env("PROVABLY_ORG_ID")
    normalized = normalize_url_for_trust(_GITHUB_REPO_PATTERN)

    conn = psycopg2.connect(postgres_url)
    try:
        ensure_trusted_endpoints_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trusted_endpoints (org_id, normalized_url, display_label, entry_type)
                VALUES (%s, %s, %s, 'endpoint')
                ON CONFLICT (org_id, normalized_url) WHERE revoked_at IS NULL DO NOTHING
                """,
                (org_id, normalized, _GITHUB_REPO_PATTERN),
            )
        conn.commit()
    finally:
        conn.close()


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_repo(repo: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}"
    with intercept_context(agent_id=_AGENT_ID, action_name=_ACTION_NAME):
        response = requests.get(url, headers=_github_headers(), timeout=30)
        response.raise_for_status()
        return response.json()


def _build_fetch_and_claim(repo_json: dict[str, Any], *, tamper: bool) -> dict[str, Any]:
    claimed_stars = int(repo_json["stargazers_count"])
    if tamper:
        claimed_stars += 1

    full_name = str(repo_json.get("full_name") or "unknown/repo")
    return {
        "reasoning": (
            f"The agent called the GitHub repository API for {full_name} and extracted "
            "the stargazers_count field."
        ),
        "claims": [
            {
                "action_name": _ACTION_NAME,
                "claimed_value": claimed_stars,
                "verification_mode": "field_extraction",
                "json_path": "$.stargazers_count",
            }
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a GitHub API claim with Provably.")
    parser.add_argument(
        "--repo",
        default="ProvablyAI/verifiable-data-agentkit",
        help="GitHub repo in owner/name form.",
    )
    parser.add_argument(
        "--tamper",
        action="store_true",
        help="Claim one extra star to demonstrate a CAUGHT verdict.",
    )
    args = parser.parse_args()

    _seed_trusted_endpoint()
    provably_runtime.configure_indexing(enable_indexing=True)

    repo_json = _fetch_repo(args.repo)
    row_id = take_last_intercept_row_id()
    if row_id is None:
        raise RuntimeError("No intercept row captured; check POSTGRES_URL and trusted_endpoints.")

    payload = build_handoff_payload(
        _build_fetch_and_claim(repo_json, tamper=args.tamper),
        run_id=f"github-api-{args.repo.replace('/', '-')}",
        intercept_agent_id=_AGENT_ID,
    )

    result = evaluate_handoff(
        payload,
        provably_base_url=_require_env("PROVABLY_RUST_BE_URL").rstrip("/"),
        postgres_url=_require_env("POSTGRES_URL"),
        org_id_fallback=_require_env("PROVABLY_ORG_ID"),
    )

    print("Evaluation result:")
    print(json.dumps(result, indent=2))

    if result.get("outcome") != "PASS":
        raise SystemExit("\nNot answering because the GitHub claim did not verify.")

    stars = repo_json["stargazers_count"]
    print(f"\nVerified answer: {args.repo} has {stars} GitHub stars.")


if __name__ == "__main__":
    main()
