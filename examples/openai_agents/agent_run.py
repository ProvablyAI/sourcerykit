"""
Runnable demo: OpenAI Agents SDK + Provably interception → handoff → evaluate.

Prerequisites
-------------
Set the following environment variables before running:

    OPENROUTER_API_KEY    – OpenRouter API key (model call)
    PROVABLY_API_KEY      – Provably integration key
    PROVABLY_ORG_ID       – Provably organisation id
    PROVABLY_RUST_BE_URL  – Provably Rust backend base URL
    POSTGRES_URL          – PostgreSQL DSN for intercept storage

Run:
    pip install -e .[dev]
    python examples/openai_agents/agent_run.py

Cost: ~$0.001 per run using openai/gpt-4o-mini on OpenRouter.
"""

from __future__ import annotations

import asyncio
import json
import os

import psycopg2
import requests
from agents import Agent, Runner, function_tool, set_default_openai_api, set_default_openai_client
from openai import AsyncOpenAI

import agentkit.runtime as _prt
from agentkit.handoff.client import cached_integration_api_key
from agentkit.handoff.evaluator import evaluate_handoff
from agentkit.handoff.types import HandoffClaim, HandoffPayload
from agentkit.intercept import set_interceptor_context, take_last_intercept_row_id
from agentkit.trusted_endpoints import (
    ensure_trusted_endpoints_table,
    load_trusted_endpoint_urls,
    normalize_url_for_trust,
)

# ---------------------------------------------------------------------------
# Trusted endpoint URLs for this demo
# ---------------------------------------------------------------------------
_OPENROUTER_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
_OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

_TRUSTED_URLS = [
    _OPENROUTER_COMPLETIONS_URL,
    _OPEN_METEO_BASE_URL,
]


def _seed_trusted_endpoints() -> None:
    """Insert the demo URLs into trusted_endpoints (idempotent ON CONFLICT DO NOTHING)."""
    postgres_url = os.environ["POSTGRES_URL"]
    org_id = os.environ["PROVABLY_ORG_ID"]

    conn = psycopg2.connect(postgres_url)
    try:
        ensure_trusted_endpoints_table(conn)
        with conn.cursor() as cur:
            for url in _TRUSTED_URLS:
                norm = normalize_url_for_trust(url)
                cur.execute(
                    """
                    INSERT INTO trusted_endpoints (org_id, normalized_url, display_label, entry_type)
                    VALUES (%s, %s, %s, 'endpoint')
                    ON CONFLICT (org_id, normalized_url) WHERE revoked_at IS NULL DO NOTHING
                    """,
                    (org_id, norm, url),
                )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool definition — the @function_tool decorator registers the schema at
# import time but does NOT make HTTP calls, so the interceptor doesn't need
# to be active yet at decoration time.
# ---------------------------------------------------------------------------
@function_tool
def get_current_temperature_london() -> dict:
    """Fetch the current temperature in London (51.5074 N, 0.1278 W) from Open-Meteo.

    Returns a dict with a ``temperature_2m`` key (Celsius, float).
    """
    set_interceptor_context(agent_id="demo", action_name="get_weather")

    response = requests.get(
        _OPEN_METEO_BASE_URL,
        params={
            "latitude": 51.5074,
            "longitude": -0.1278,
            "current": "temperature_2m",
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    current = data.get("current", {})
    return {"temperature_2m": current.get("temperature_2m")}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    # Step 1 — activate Provably indexing (interceptor + storage)
    # Must happen before Runner.run() so all HTTP calls are recorded.
    _prt.configure_indexing(enable_indexing=True)

    # Step 2 — configure the Agents SDK to use OpenRouter (Chat Completions API)
    openrouter_client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    set_default_openai_client(openrouter_client, use_for_tracing=False)
    # OpenRouter speaks Chat Completions, not the Responses API the SDK defaults to.
    set_default_openai_api("chat_completions")

    # Step 3 — seed trusted endpoints so the trust gate allows these URLs
    print("Seeding trusted endpoints…")
    _seed_trusted_endpoints()

    # Step 4 — run the agent
    agent = Agent(
        name="weather-demo",
        instructions=(
            "You are a helpful assistant. When asked about the current temperature in London, "
            "use the get_current_temperature_london tool and report the result clearly."
        ),
        tools=[get_current_temperature_london],
        model="openai/gpt-4o-mini",
    )

    print("Running agent…")
    result = await Runner.run(agent, "What is the current temperature in London?")
    print(f"\nAgent response: {result.final_output}\n")

    # Step 5 — capture the intercept row id for the weather tool call
    intercept_row_id = take_last_intercept_row_id()
    if intercept_row_id is None:
        print("WARNING: No intercept row captured. Check POSTGRES_URL and that trusted_endpoints are seeded correctly.")

    # Step 6 — extract tool output for the claim
    tool_output_value: dict = {}
    for item in result.new_items:
        if hasattr(item, "output"):
            raw_out = item.output
            if isinstance(raw_out, str):
                try:
                    tool_output_value = json.loads(raw_out)
                except Exception:  # noqa: BLE001
                    pass
            elif isinstance(raw_out, dict):
                tool_output_value = raw_out
            if tool_output_value:
                break

    print(f"Tool output captured for claim: {tool_output_value}")

    # Step 7 — build the HandoffPayload and evaluate
    org_id = os.environ["PROVABLY_ORG_ID"]
    provably_base_url = os.environ.get("PROVABLY_RUST_BE_URL", "").rstrip("/")
    postgres_url = os.environ["POSTGRES_URL"]

    # NOTE: in production use build_handoff_payload() to obtain a real Provably
    # query record UUID. This demo passes the raw intercepts PK as a stand-in.
    query_record_id = str(intercept_row_id) if intercept_row_id else ""
    trusted_urls = load_trusted_endpoint_urls(postgres_url, org_id)

    payload = HandoffPayload(
        provably_org_id=org_id,
        integration_api_key=cached_integration_api_key(),
        trusted_endpoint_registry=trusted_urls,
        claims=[
            HandoffClaim(
                action_name="get_weather",
                claimed_value=tool_output_value,
                query_record_id=query_record_id,
                verification_mode="verbatim",
            )
        ],
    )

    print("Evaluating handoff…")
    eval_result = evaluate_handoff(
        payload,
        provably_base_url=provably_base_url,
        postgres_url=postgres_url,
        org_id_fallback=org_id,
    )

    print("\nEvaluation result:")
    print(json.dumps(eval_result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
