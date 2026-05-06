"""
Runnable demo: manual tool → LLM → handoff → evaluate, no agent framework.

This example deliberately does NOT use an agent-framework Runner. The flow is:

  1. Call the weather tool directly. The interceptor records the GET row.
  2. Snapshot ``take_last_intercept_row_id()`` BEFORE any other HTTP fires.
  3. Ask an LLM to reason over the tool output (text only — never compared).
  4. Build the handoff payload via ``build_handoff_payload`` and evaluate.

This shape is the simplest way to use the SDK end-to-end and the easiest to
reason about — there is no async tool/LLM interleaving, so there is no
``ContextVar`` leak risk and no need to think about which framework's
``Task`` semantics apply.

If you ARE using an agent framework, see ``examples/openai_agents/`` instead;
the patterns here still apply but Runner-based execution introduces extra
considerations (use ``with intercept_context(...)`` inside tool bodies, look up
rows by ``get_intercept_row_id(agent_id, action_name)`` rather than the global
``take_last_intercept_row_id()``).

Prerequisites
-------------
Set the following environment variables before running:

    PROVABLY_API_KEY      – Provably integration key
    PROVABLY_ORG_ID       – Provably organisation id
    PROVABLY_RUST_BE_URL  – Provably Rust backend base URL
    POSTGRES_URL          – PostgreSQL DSN for intercept storage

For the LLM step, either:

    OPENROUTER_API_KEY    – uses OpenRouter (default; ~$0.001/run on gpt-4o-mini)
    HF_TGI_URL            – override to point at any OpenAI-compatible endpoint
                            (e.g. Docker Model Runner: http://localhost:12434/engines/v1/chat/completions)

Run:
    pip install -e .[dev]
    python examples/manual_loop/agent_run.py            # PASS
    python examples/manual_loop/agent_run.py --tamper   # CAUGHT (forced)
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os

import psycopg2
import requests

import provably.runtime as _prt
from provably.handoff.evaluator import evaluate_handoff
from provably.handoff.payload_builder import build_handoff_payload
from provably.intercept import intercept_context, take_last_intercept_row_id
from provably.trusted_endpoints import ensure_trusted_endpoints_table, normalize_url_for_trust

# Optional: load .env if python-dotenv is installed (it is not a dependency of this SDK).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


_OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
_OPENROUTER_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


def _llm_endpoint() -> tuple[str, dict[str, str], str]:
    """Pick the LLM endpoint based on env. Returns (url, headers, model)."""
    override = os.getenv("HF_TGI_URL", "").strip()
    if override:
        return override, {"Content-Type": "application/json"}, os.getenv(
            "HF_TGI_MODEL", "huggingface.co/qwen/qwen3.5-0.8b-base"
        )
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY or HF_TGI_URL before running this example.")
    return (
        _OPENROUTER_COMPLETIONS_URL,
        {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        "openai/gpt-4o-mini",
    )


def _seed_trusted_endpoints(extra: list[str]) -> None:
    """Insert the demo URLs into trusted_endpoints (idempotent)."""
    postgres_url = os.environ["POSTGRES_URL"]
    org_id = os.environ["PROVABLY_ORG_ID"]
    urls = [_OPEN_METEO_BASE_URL, *extra]

    conn = psycopg2.connect(postgres_url)
    try:
        ensure_trusted_endpoints_table(conn)
        with conn.cursor() as cur:
            for url in urls:
                cur.execute(
                    """
                    INSERT INTO trusted_endpoints (org_id, normalized_url, display_label, entry_type)
                    VALUES (%s, %s, %s, 'endpoint')
                    ON CONFLICT (org_id, normalized_url) WHERE revoked_at IS NULL DO NOTHING
                    """,
                    (org_id, normalize_url_for_trust(url), url),
                )
        conn.commit()
    finally:
        conn.close()


def get_current_temperature_london() -> dict:
    """Fetch the current temperature in London (51.5074 N, 0.1278 W) from Open-Meteo."""
    # IMPORTANT: the agent_id here MUST match the intercept_agent_id passed to
    # build_handoff_payload below ("demo"). Otherwise the (agent_id, action_name)
    # lookup will miss and the claim will end up with no recorded request payload.
    with intercept_context(agent_id="demo", action_name="get_weather"):
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
        return response.json()


async def main(tamper: bool = False) -> None:
    llm_url, llm_headers, llm_model = _llm_endpoint()

    # Step 1 — seed trusted endpoints BEFORE enabling indexing so the trust gate
    # allows these URLs when the interceptor first records them.
    print("Seeding trusted endpoints…")
    _seed_trusted_endpoints(extra=[llm_url])

    # Step 2 — activate Provably indexing (interceptor + storage).
    _prt.configure_indexing(enable_indexing=True)

    # Step 3 — call the tool directly. This records the GET row.
    print("Calling weather tool…")
    tool_output_value = get_current_temperature_london()
    print(f"Tool output (raw): {tool_output_value}")

    # Step 4 — capture the intercept row id BEFORE the LLM POST below fires.
    # take_last_intercept_row_id() returns the globally-last insert; we call it
    # immediately after the tool to make sure that's the weather GET, not the LLM.
    intercept_row_id = take_last_intercept_row_id()
    if intercept_row_id is None:
        print("WARNING: no intercept row recorded. Check POSTGRES_URL + trusted_endpoints.")

    # Step 5 — ask the LLM to reason about the tool output. The text response goes
    # into ``reasoning`` only, NOT into the claim — the evaluator never compares it.
    print("Running LLM…")
    llm_resp = requests.post(
        llm_url,
        headers=llm_headers,
        json={
            "model": llm_model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": (
                        "What is the current temperature in London?\n"
                        f"Tool result: {json.dumps(tool_output_value)}"
                    ),
                },
            ],
            "temperature": 0.0,
            "max_tokens": 120,
        },
        timeout=60,
    )
    llm_resp.raise_for_status()
    reasoning = llm_resp.json()["choices"][0]["message"]["content"]
    print(f"\nAgent response: {reasoning}\n")

    # Step 6 — claimed_value MUST be the raw response dict the interceptor stored.
    # Verbatim mode does canonical-JSON equality on this against the indexed value.
    claimed_value = copy.deepcopy(tool_output_value)
    if tamper:
        fake_temp = round(tool_output_value.get("current", {}).get("temperature_2m", 0) + 50, 1)
        claimed_value.setdefault("current", {})["temperature_2m"] = fake_temp
        print(f"[TAMPER] Replacing temperature_2m with fake value {fake_temp} — expect CAUGHT.")

    # Step 7 — build the HandoffPayload and evaluate.
    fetch_and_claim = {
        "reasoning": reasoning,
        "claims": [
            {
                # action_name MUST match the value passed to intercept_context().
                "action_name": "get_weather",
                "claimed_value": claimed_value,
                "verification_mode": "verbatim",
            }
        ],
    }

    payload = build_handoff_payload(
        fetch_and_claim,
        run_id="manual-loop-demo",
        # MUST match the agent_id passed to intercept_context() above.
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
    parser = argparse.ArgumentParser(description="Provably manual-loop demo")
    parser.add_argument(
        "--tamper",
        action="store_true",
        help="Inject a fake temperature into claimed_value to force CAUGHT.",
    )
    args = parser.parse_args()
    asyncio.run(main(tamper=args.tamper))
