"""
Demo: Local LLM Engine + SourceryKit Interception → Handoff → Evaluation.

This agent fetches London weather data, passes it to an OpenAI-compatible
local inference server (Ollama, oMLX, vLLM, Docker Model Runner, etc.), and
submits claims to the evaluator to verify execution integrity.

Run:
    python agent_run.py           # Returns PASS
    python agent_run.py --tamper  # Returns CAUGHT
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import logging
import os
import uuid

import httpx
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(name)s [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

from agentkit import (  # noqa: E402
    async_intercept_context,
    bootstrap_system,
    build_handoff_payload,
    evaluate_handoff,
    insert_trusted_endpoint,
    take_last_intercept_row_id,
)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_DEFAULT_MODEL_URL = "http://localhost:12434/engines/v1/chat/completions"
_DEFAULT_MODEL = "huggingface.co/qwen/qwen3.5-0.8b-base"


async def get_current_temperature_london() -> dict:
    """Fetch current London weather data and log the transaction via the interceptor."""
    async with async_intercept_context(agent_id="demo", action_name="get_weather"):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                _OPEN_METEO_URL,
                params={"latitude": 51.5074, "longitude": -0.1278, "current": "temperature_2m"},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()


async def main(tamper: bool = False) -> None:
    # 1. Initialize the runtime interceptor hooks
    await bootstrap_system()

    print("Seeding trusted endpoints…")
    await insert_trusted_endpoint(_OPEN_METEO_URL)

    print("Invoking weather tool...")
    tool_output_value: dict = await get_current_temperature_london()

    if take_last_intercept_row_id() is None:
        print("WARNING: No intercept row captured. Check SOURCERYKIT_POSTGRES_URL configuration.")

    # 2. Resolve local inference settings
    model_url = os.getenv("LOCAL_MODEL_URL", _DEFAULT_MODEL_URL).strip() or _DEFAULT_MODEL_URL
    model = os.getenv("LOCAL_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL

    print(f"Routing context to local LLM ({model})...")
    prompt = f"What is the current temperature in London?\nTool result: {json.dumps(tool_output_value)}"

    llm_resp = requests.post(
        model_url,
        headers={"Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 120,
        },
    )
    llm_resp.raise_for_status()
    reasoning = llm_resp.json()["choices"]["message"]["content"]
    print(f"\nAgent Response: {reasoning}\n")

    # 3. Handle optional tampering logic to demonstrate verification guardrails
    claimed_value = copy.deepcopy(tool_output_value)
    if tamper:
        actual_temp = tool_output_value.get("current", {}).get("temperature_2m", 0)
        claimed_value["current"]["temperature_2m"] = round(actual_temp + 50.0, 1)
        print("[TAMPER] Injecting hallucination data into claim structure — expect CAUGHT\n")

    # 4. Assemble the verified handoff bundle
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

    # 5. Evaluate execution statements against unalterable records
    print("Evaluating handoff payload...")
    eval_result = await evaluate_handoff(payload)

    print("\nEvaluation Verdict:")
    print(json.dumps(eval_result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SourceryKit Local Model Demo")
    parser.add_argument(
        "--tamper",
        action="store_true",
        help="Inject a hallucinated temperature into the claim to trigger a CAUGHT verification verdict.",
    )
    args = parser.parse_args()
    asyncio.run(main(tamper=args.tamper))
