import argparse
import asyncio
import copy
import json
import logging
import uuid

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent  # The modern standard

# Up-to-date LangChain 1.x Imports
from langchain_core.tools import tool

from agentkit import (
    async_intercept_context,
    bootstrap_system,
    build_handoff_payload,
    evaluate_handoff,
    insert_trusted_endpoint,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(name)s [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Global state to capture the tool's raw execution data during the agent's run
_LATEST_TOOL_OUTPUT = {}


# 1. Define the Agent's Tool
@tool
async def get_current_temperature_london() -> str:
    """Fetch current London weather data. Use this whenever asked about London weather or temperature."""
    global _LATEST_TOOL_OUTPUT
    async with async_intercept_context(agent_id="demo", action_name="get_weather"):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                _OPEN_METEO_URL,
                params={"latitude": 51.5074, "longitude": -0.1278, "current": "temperature_2m"},
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            _LATEST_TOOL_OUTPUT = copy.deepcopy(data)
            return json.dumps(data)


async def main(tamper: bool = False) -> None:
    # Initialize runtime interceptor hooks
    await bootstrap_system()
    await insert_trusted_endpoint(_OPEN_METEO_URL)

    # 2. Setup Agent and Tools
    agent = create_agent(model="openai:gpt-5.4", tools=[get_current_temperature_london])

    print("Sending request to latest LangChain Agent...")
    user_prompt = "Hey there! Can you check what the current temperature in London is right now?"

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_prompt}]},
    )

    # Extract the final message content from the updated state graph history
    reasoning = result["messages"][-1].content
    print(f"\nAgent Response: {reasoning}\n")

    # 3. Tampering logic for AgentKit verification
    claimed_value = copy.deepcopy(_LATEST_TOOL_OUTPUT)
    if tamper:
        actual_temp = _LATEST_TOOL_OUTPUT.get("current", {}).get("temperature_2m", 0)
        claimed_value["current"]["temperature_2m"] = round(actual_temp + 50.0, 1)
        print("[TAMPER] Injecting hallucination data into claim structure — expect CAUGHT\n")

    # 4. Assemble and evaluate payload
    payload = await build_handoff_payload(
        {
            "reasoning": reasoning,
            "claims": [
                {
                    "action_name": "get_weather",
                    "claimed_value": claimed_value,
                    "verification_mode": "verbatim",
                }
            ],
        },
        run_id=uuid.uuid4(),
        intercept_agent_id="demo",
    )

    print("Evaluating handoff payload...")
    eval_result = await evaluate_handoff(payload)

    print("\nEvaluation Verdict:")
    print(json.dumps(eval_result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modern SourceryKit LangChain Agent Demo")
    parser.add_argument("--tamper", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(tamper=args.tamper))
