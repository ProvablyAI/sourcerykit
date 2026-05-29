"""
Runnable demo: OpenAI Agents SDK + SourceryKit Interception → Handoff → Evaluation.

This example runs an agent flow backed by OpenAI's Agents framework. It routes
LLM reasoning calls to OpenRouter and weather tool lookups to Open-Meteo, with
SourceryKit validating data integrity across every step.

Run:
    python agent_run.py
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid

import requests
from agents import Agent, Runner, function_tool, set_default_openai_api, set_default_openai_client
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

from agentkit import (  # noqa: E402
    async_intercept_context,
    bootstrap_system,
    build_handoff_payload,
    evaluate_handoff,
    insert_trusted_endpoint,
    take_last_intercept_row_id,
)

_OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@function_tool
async def get_current_temperature_london() -> dict:
    """Fetch the current temperature in London from Open-Meteo.

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


async def main() -> None:
    # 1. Activate SourceryKit indexing (interceptor + storage)
    await bootstrap_system()

    # 2. Configure the Agents SDK client structure to connect via OpenRouter
    openrouter_client = AsyncOpenAI(
        base_url=_OPENROUTER_BASE_URL,
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    set_default_openai_client(openrouter_client, use_for_tracing=False)
    set_default_openai_api("chat_completions")

    # 3. Seed all outbound endpoints (both tool routing and model APIs must be allow-listed)
    print("Seeding trusted endpoints…")
    await insert_trusted_endpoint(_OPEN_METEO_BASE_URL)
    await insert_trusted_endpoint(f"{_OPENROUTER_BASE_URL}/chat/completions")

    # 4. Initialize and launch the agent framework run loop
    agent = Agent(
        name="weather-demo",
        instructions=(
            "You are a helpful assistant. When asked about the current temperature in London, "
            "use the get_current_temperature_london tool and report the result clearly."
        ),
        tools=[get_current_temperature_london],
        model="openai/gpt-4o-mini",
    )

    print("Running agent...")
    result = await Runner.run(agent, "What is the current temperature in London?")
    print(f"\nAgent response: {result.final_output}\n")

    if take_last_intercept_row_id() is None:
        print("WARNING: No intercept row captured. Check SOURCERYKIT_POSTGRES_URL configuration.")

    # 5. Extract raw tool values out of the completed agent runner context items
    tool_output_value: dict = {}
    for item in result.new_items:
        if hasattr(item, "output"):
            raw_out = item.output
            if isinstance(raw_out, str):
                try:
                    tool_output_value = json.loads(raw_out)
                except Exception:
                    pass
            elif isinstance(raw_out, dict):
                tool_output_value = raw_out
            if tool_output_value:
                break

    print(f"Tool output captured for claim: {tool_output_value}")

    # 6. Build the unified handoff payload container
    payload = await build_handoff_payload(
        {
            "reasoning": result.final_output,
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

    # 7. Submit the payload for evaluation against database logs
    print("Evaluating handoff payload...")
    eval_result = await evaluate_handoff(payload)

    print("\nEvaluation Result:")
    print(json.dumps(eval_result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
