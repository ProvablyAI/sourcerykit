"""
Demo: Local Model (Docker Model Runner) + Provably interception → handoff → evaluate.

The agent fetches the current London temperature from Open-Meteo, passes it to
a local LLM (Docker Model Runner), then evaluates the handoff with Provably.

Prerequisites
-------------
    PROVABLY_API_KEY      – Provably integration key
    PROVABLY_ORG_ID       – Provably organisation id
    PROVABLY_RUST_BE_URL  – Provably Rust backend base URL
    POSTGRES_URL          – PostgreSQL DSN for intercept storage
    LOCAL_MODEL_URL       – (optional) Docker Model Runner endpoint URL
                            default: http://localhost:12434/engines/v1/chat/completions
    LOCAL_MODEL           – (optional) model id to use (as pulled via docker model pull)
                            default: huggingface.co/qwen/qwen3.5-0.8b-base

Run:
    pip install -e .[dev]
    python examples/local_model/agent_run.py           # expect PASS
    python examples/local_model/agent_run.py --tamper  # expect CAUGHT
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os

import psycopg2
import requests
from dotenv import load_dotenv

import provably.runtime as _prt
from provably.handoff.evaluator import evaluate_handoff
from provably.handoff.payload_builder import build_handoff_payload
from provably.intercept import take_last_intercept_row_id
from provably.intercept.interceptor import intercept_context
from provably.trusted_endpoints import (
    ensure_trusted_endpoints_table,
    normalize_url_for_trust,
)

load_dotenv()


_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_DEFAULT_MODEL_URL = "http://localhost:12434/engines/v1/chat/completions"
_DEFAULT_MODEL = "huggingface.co/qwen/qwen3.5-0.8b-base"


def _seed_trusted_endpoints() -> None:
    """Insert trusted URLs into the DB (idempotent)."""
    postgres_url = os.environ["POSTGRES_URL"]
    org_id = os.environ["PROVABLY_ORG_ID"]
    conn = psycopg2.connect(postgres_url)
    try:
        ensure_trusted_endpoints_table(conn)
        with conn.cursor() as cur:
            norm = normalize_url_for_trust(_OPEN_METEO_URL)
            cur.execute(
                """
                INSERT INTO trusted_endpoints (org_id, normalized_url, display_label, entry_type)
                VALUES (%s, %s, %s, 'endpoint')
                ON CONFLICT (org_id, normalized_url) WHERE revoked_at IS NULL DO NOTHING
                """,
                (org_id, norm, _OPEN_METEO_URL),
            )
        conn.commit()
    finally:
        conn.close()


def get_current_temperature_london() -> dict:
    """Fetch current London weather from Open-Meteo and record the intercept."""
    with intercept_context(agent_id="demo", action_name="get_weather"):
        response = requests.get(
            _OPEN_METEO_URL,
            params={"latitude": 51.5074, "longitude": -0.1278, "current": "temperature_2m"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


async def main(tamper: bool = False) -> None:
    # Seed trusted endpoints BEFORE enabling indexing (trust gate fires on first insert).
    print("Seeding trusted endpoints…")
    _seed_trusted_endpoints()

    _prt.configure_indexing(enable_indexing=True)

    print("Calling weather tool…")
    tool_output_value: dict = get_current_temperature_london()
    print(f"Tool output: {tool_output_value}")

    if take_last_intercept_row_id() is None:
        print("WARNING: No intercept row captured — check POSTGRES_URL and trusted_endpoints.")

    model_url = os.getenv("LOCAL_MODEL_URL", _DEFAULT_MODEL_URL).strip() or _DEFAULT_MODEL_URL
    model = os.getenv("LOCAL_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL

    print(f"Running LLM ({model})…")
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
    reasoning = llm_resp.json()["choices"][0]["message"]["content"]
    print(f"\nAgent response: {reasoning}\n")

    # Optionally tamper to simulate a hallucination → forces CAUGHT.
    claimed_value = copy.deepcopy(tool_output_value)
    if tamper:
        fake_temp = round(tool_output_value.get("current", {}).get("temperature_2m", 0) + 50, 1)
        claimed_value.setdefault("current", {})["temperature_2m"] = fake_temp
        print(f"[TAMPER] Injecting fake temperature_2m={fake_temp} — expect CAUGHT\n")

    payload = build_handoff_payload(
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
        run_id="run-1",
        intercept_agent_id="demo",
    )

    print("Evaluating handoff…")
    eval_result = evaluate_handoff(
        payload,
        provably_base_url=os.environ.get("PROVABLY_RUST_BE_URL", "").rstrip("/"),
        postgres_url=os.environ["POSTGRES_URL"],
        org_id_fallback=os.environ["PROVABLY_ORG_ID"],
    )

    print("\nEvaluation result:")
    print(json.dumps(eval_result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provably agent demo")
    parser.add_argument(
        "--tamper",
        action="store_true",
        help="Inject a hallucinated temperature into claimed_value to force CAUGHT.",
    )
    args = parser.parse_args()
    asyncio.run(main(tamper=args.tamper))
