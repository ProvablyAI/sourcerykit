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
import uuid

import requests
from agents import Agent, Runner, function_tool, set_default_openai_api, set_default_openai_client
from openai import AsyncOpenAI

from agentkit import (  # noqa: E402
    async_intercept_context,
    bootstrap_system,
    build_handoff_payload,
    evaluate_handoff,
    insert_trusted_endpoint,
    take_last_intercept_row_id,
)

# ---------------------------------------------------------------------------
# Trusted endpoint URLs for this demo
# ---------------------------------------------------------------------------
_OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"


# ---------------------------------------------------------------------------
# Tool definition — the @function_tool decorator registers the schema at
# import time but does NOT make HTTP calls, so the interceptor doesn't need
# to be active yet at decoration time.
# ---------------------------------------------------------------------------
@function_tool
async def get_current_temperature_london() -> dict:
    """Fetch the current temperature in London (51.5074 N, 0.1278 W) from Open-Meteo.

    Returns a dict with a ``temperature_2m`` key (Celsius, float).
    """
    async with async_intercept_context(agent_id="demo", action_name="get_weather"):
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
    await bootstrap_system()

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
    await insert_trusted_endpoint(_OPEN_METEO_BASE_URL)

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
    payload = await build_handoff_payload(
        {
            "reasoning": "",
            "claims": [
                {
                    "action_name": "get_weather",
                    "claimed_value": tool_output_value,
                    "verification_mode": "verbatim",
                }
            ],
        },
        run_id=uuid.uuid4(),
        intercept_agent_id="demo",
    )

    print("Evaluating handoff…")
    eval_result = evaluate_handoff(
        payload,
    )

    print("\nEvaluation result:")
    print(json.dumps(eval_result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
