"""End-to-end test suite for OpenAI Agents SDK integration.

Six scenarios (A–F) drive a fake LLM server + fake data server through the
full intercept → handoff → evaluate flow:

  A – happy path: all URLs trusted, evaluate_handoff → PASS
  B – tampered claim: claimed_value wrong → CAUGHT
  C – untrusted GET: data URL not in allowlist → tool call raises BLOCKED
  D – untrusted POST: LLM URL not in allowlist → LLM POST raises BLOCKED
  E – self-egress exemption: Provably backend NOT in allowlist; evaluate_handoff still completes
  F – async LLM coverage: at least one recorded row has method == "POST" from the LLM server

Design note on trust-gate testing (scenarios C and D):
  ``patched_interceptor`` replaces ``_insert_row`` in ``interceptor.py``, which bypasses the
  entire ``_storage.insert_intercept_row`` path (and therefore never reaches
  ``_require_trusted_endpoint``).  For C and D we need the trust check to fire but avoid a real
  DB write, so those two scenarios use ``patched_interceptor_with_trust`` instead, which:
    1. Calls ``init_interceptor()`` (installs patches),
    2. Monkeypatches POSTGRES_URL to a non-empty sentinel so the early-return guard in
       ``insert_intercept_row`` is skipped,
    3. Monkeypatches ``_require_trusted_endpoint`` with the in-memory allowlist check, and
    4. Monkeypatches ``_write_row`` to a no-op so no actual DB call happens.
"""

from __future__ import annotations

from typing import Any

import pytest
import requests as requests_lib
from agents import Agent, Runner, function_tool, set_default_openai_api, set_default_openai_client
from openai import AsyncOpenAI

import provably.intercept._storage as _storage_module
import provably.intercept.interceptor as _interceptor_module
from provably.handoff.evaluator import evaluate_handoff
from provably.handoff.types import HandoffClaim, HandoffPayload
from provably.trusted_endpoints import normalize_url_for_trust
from tests.e2e.conftest import FakeHttpServer

# ---------------------------------------------------------------------------
# Helper: build canonical ChatCompletion JSON responses for the fake LLM server
# ---------------------------------------------------------------------------

def _tool_call_response(tool_name: str, call_id: str = "call_001", arguments: str = "{}") -> dict:
    """First LLM turn: respond with a tool_call."""
    return {
        "id": "chatcmpl-test-turn1",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": arguments,
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
                "logprobs": None,
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }


def _final_response(content: str = "The temperature is 21 degrees Celsius.") -> dict:
    """Second LLM turn: final assistant message."""
    return {
        "id": "chatcmpl-test-turn2",
        "object": "chat.completion",
        "created": 1700000001,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": None,
                },
                "finish_reason": "stop",
                "logprobs": None,
            }
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
        },
    }


# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_llm_server(fake_server_factory) -> FakeHttpServer:
    """A FakeHttpServer that responds to POST /v1/chat/completions.

    First call → tool_call response; subsequent calls → final assistant message.
    """
    server = fake_server_factory()
    call_count = [0]

    def _handle_chat(_req):
        from tests.e2e.conftest import FakeResponse
        call_count[0] += 1
        body = _tool_call_response("get_temperature") if call_count[0] == 1 else _final_response()
        return FakeResponse(status=200, body=body)

    server.route("POST", "/v1/chat/completions", _handle_chat)
    return server


@pytest.fixture
def fake_data_server(fake_server_factory) -> FakeHttpServer:
    """A FakeHttpServer that responds to GET /v1/temperature with celsius: 21."""
    server = fake_server_factory()
    server.respond("GET", "/v1/temperature", status=200, body={"celsius": 21})
    return server


def _trusted_check(allowlist: set[str], url: str) -> None:
    """Prefix-aware trust check: a URL is trusted if its normalized form starts with any
    trusted entry (or exactly matches one).  This mirrors real-world usage where users
    register the service base URL (e.g. ``http://127.0.0.1:9000``) and calls to any
    path under that base (e.g. ``http://127.0.0.1:9000/v1/chat/completions``) are trusted.
    """
    norm = normalize_url_for_trust(url)
    for trusted in allowlist:
        if norm == trusted or norm.startswith(trusted + "/") or norm.startswith(trusted + "?"):
            return
    raise RuntimeError(f"BLOCKED: {url} not in trusted_endpoints")


@pytest.fixture
def fake_trusted_endpoints(monkeypatch: pytest.MonkeyPatch) -> set[str]:
    """Monkeypatch _require_trusted_endpoint to consult an in-memory allowlist.

    Tests mutate the returned set to seed the allowlist for each scenario.
    This fixture is ONLY sufficient for scenarios that also use ``patched_interceptor``
    (A, B, E, F), because ``patched_interceptor`` bypasses ``_storage.insert_intercept_row``
    entirely — the trust check never fires.  For scenarios C and D, use
    ``patched_interceptor_with_trust`` instead (it also patches the trust gate).
    """
    allowlist: set[str] = set()

    def fake_require(_pg_url: str, url: str) -> None:
        _trusted_check(allowlist, url)

    monkeypatch.setattr(
        "provably.intercept._storage._require_trusted_endpoint",
        fake_require,
    )
    return allowlist


@pytest.fixture
def patched_interceptor_with_trust(monkeypatch: pytest.MonkeyPatch) -> tuple[list[dict[str, Any]], set[str]]:
    """Install the real interceptor WITH the trust gate active.

    Unlike ``patched_interceptor`` (which replaces _insert_row and bypasses _storage entirely),
    this fixture lets ``insert_intercept_row`` run so ``_require_trusted_endpoint`` fires.
    It avoids a real Postgres connection by:
      1. Setting a sentinel POSTGRES_URL so the early-return guard is skipped.
      2. Replacing ``_require_trusted_endpoint`` with an in-memory prefix-aware allowlist check.
      3. Replacing ``_write_row`` with a no-op that records to an in-memory list.

    Returns (rows_list, trusted_allowlist) — tests mutate trusted_allowlist to seed permissions.
    """
    rows: list[dict[str, Any]] = []
    allowlist: set[str] = set()

    # Give insert_intercept_row a non-empty POSTGRES_URL so it doesn't early-return
    monkeypatch.setenv("POSTGRES_URL", "postgresql://fake-host/fake-db")

    def fake_require(_pg_url: str, url: str) -> None:
        _trusted_check(allowlist, url)

    def fake_write_row(postgres_url, url, method, request_payload, raw, agent_id, action_name):
        rows.append({"url": url, "method": method, "request": request_payload, "raw": raw})
        return None

    monkeypatch.setattr(_storage_module, "_require_trusted_endpoint", fake_require)
    monkeypatch.setattr(_storage_module, "_write_row", fake_write_row)

    _interceptor_module.init_interceptor()
    monkeypatch.setattr(_interceptor_module, "_enabled", True)

    return rows, allowlist


def _configure_agent_client(fake_llm_server: FakeHttpServer) -> None:
    """Point the agents SDK at the fake LLM server and force chat completions mode."""
    client = AsyncOpenAI(
        base_url=f"{fake_llm_server.base_url}/v1",
        api_key="test-key",
    )
    set_default_openai_client(client, use_for_tracing=False)
    set_default_openai_api("chat_completions")


def _stored(record: dict) -> dict:
    return {"result": record}


# ---------------------------------------------------------------------------
# Scenario A — happy path
# ---------------------------------------------------------------------------

@pytest.mark.e2e
async def test_openai_agent_intercepts_and_handoff_passes(
    fake_llm_server: FakeHttpServer,
    fake_data_server: FakeHttpServer,
    fake_server_factory,
    patched_interceptor: list[dict[str, Any]],
    fake_trusted_endpoints: set[str],
) -> None:
    """A: both LLM and data URLs trusted; Runner.run succeeds; evaluate_handoff → PASS."""
    # Seed trusted endpoints: LLM server + data server base URLs
    fake_trusted_endpoints.add(normalize_url_for_trust(fake_llm_server.base_url))
    fake_trusted_endpoints.add(normalize_url_for_trust(fake_data_server.base_url))

    _configure_agent_client(fake_llm_server)

    data_url = f"{fake_data_server.base_url}/v1/temperature"

    @function_tool
    def get_temperature() -> dict:
        """Get the current temperature."""
        return requests_lib.get(data_url).json()

    agent = Agent(
        name="weather-agent",
        instructions="Use the get_temperature tool and report the result.",
        tools=[get_temperature],
        model="gpt-4o-mini",
    )

    result = await Runner.run(agent, "What's the temp?")
    assert result is not None

    # Assert interceptor recorded at least 2 rows: one POST (LLM), one GET (data)
    assert len(patched_interceptor) >= 2, f"Expected >=2 rows, got {len(patched_interceptor)}"
    llm_rows = [r for r in patched_interceptor if r["method"] == "POST"]
    data_rows = [r for r in patched_interceptor if r["method"] == "GET"]
    assert len(llm_rows) >= 1, "Expected at least one POST row (LLM call)"
    assert len(data_rows) >= 1, "Expected at least one GET row (data call)"

    # Spin up a fake Provably backend
    fake_provably = fake_server_factory()
    fake_provably.respond(
        "GET",
        "/api/v1/organizations/org-1/queries/q1",
        status=200,
        body=_stored({"celsius": 21}),
    )
    fake_provably.respond(
        "POST",
        "/api/v1/organizations/org-1/queries/q1/verify",
        status=200,
        body={"verified": True},
    )

    payload = HandoffPayload(
        provably_org_id="org-1",
        integration_api_key="key-abc",
        claims=[
            HandoffClaim(
                action_name="get_temperature",
                claimed_value={"celsius": 21},
                query_record_id="q1",
            )
        ],
    )

    eval_result = evaluate_handoff(payload, provably_base_url=fake_provably.base_url)
    assert eval_result["outcome"] == "PASS", f"Expected PASS, got: {eval_result}"
    assert eval_result["per_claim"][0]["result"] == "PASS"


# ---------------------------------------------------------------------------
# Scenario B — tampered claim
# ---------------------------------------------------------------------------

@pytest.mark.e2e
async def test_evaluate_catches_wrong_claim(
    fake_llm_server: FakeHttpServer,
    fake_data_server: FakeHttpServer,
    fake_server_factory,
    patched_interceptor: list[dict[str, Any]],
    fake_trusted_endpoints: set[str],
) -> None:
    """B: same as A but claimed_value is wrong → CAUGHT."""
    fake_trusted_endpoints.add(normalize_url_for_trust(fake_llm_server.base_url))
    fake_trusted_endpoints.add(normalize_url_for_trust(fake_data_server.base_url))

    _configure_agent_client(fake_llm_server)

    data_url = f"{fake_data_server.base_url}/v1/temperature"

    @function_tool
    def get_temperature() -> dict:
        """Get the current temperature."""
        return requests_lib.get(data_url).json()

    agent = Agent(
        name="weather-agent",
        instructions="Use the get_temperature tool and report the result.",
        tools=[get_temperature],
        model="gpt-4o-mini",
    )

    await Runner.run(agent, "What's the temp?")

    fake_provably = fake_server_factory()
    fake_provably.respond(
        "GET",
        "/api/v1/organizations/org-1/queries/q1",
        status=200,
        body=_stored({"celsius": 21}),
    )

    # Claim a wrong (tampered) value
    payload = HandoffPayload(
        provably_org_id="org-1",
        integration_api_key="key-abc",
        claims=[
            HandoffClaim(
                action_name="get_temperature",
                claimed_value={"celsius": 99},  # tampered
                query_record_id="q1",
            )
        ],
    )

    eval_result = evaluate_handoff(payload, provably_base_url=fake_provably.base_url)
    assert eval_result["outcome"] == "CAUGHT", f"Expected CAUGHT, got: {eval_result}"
    assert eval_result["per_claim"][0]["result"] == "CAUGHT"


# ---------------------------------------------------------------------------
# Scenario C — untrusted GET blocks the tool call
# ---------------------------------------------------------------------------

@pytest.mark.e2e
async def test_untrusted_get_blocks_request(
    fake_llm_server: FakeHttpServer,
    fake_data_server: FakeHttpServer,
    patched_interceptor_with_trust,
) -> None:
    """C: data server URL NOT in trusted_endpoints → tool GET raises BLOCKED.

    Uses patched_interceptor_with_trust so the real trust gate fires inside
    insert_intercept_row (patched_interceptor bypasses it entirely).
    """
    rows, allowlist = patched_interceptor_with_trust

    # Only trust the LLM server; omit the data server
    allowlist.add(normalize_url_for_trust(fake_llm_server.base_url))
    # data server deliberately omitted

    _configure_agent_client(fake_llm_server)

    data_url = f"{fake_data_server.base_url}/v1/temperature"

    @function_tool(failure_error_function=None)
    def get_temperature() -> dict:
        """Get the current temperature."""
        return requests_lib.get(data_url).json()

    agent = Agent(
        name="weather-agent",
        instructions="Use the get_temperature tool and report the result.",
        tools=[get_temperature],
        model="gpt-4o-mini",
    )

    with pytest.raises((RuntimeError, Exception), match="BLOCKED"):
        await Runner.run(agent, "What's the temp?")


# ---------------------------------------------------------------------------
# Scenario D — untrusted POST blocks the LLM call
# ---------------------------------------------------------------------------

def _exception_chain_contains(exc: BaseException, pattern: str) -> bool:
    """Walk the full exception chain (__cause__, __context__) looking for ``pattern``."""
    seen: set[int] = set()
    curr: BaseException | None = exc
    while curr is not None and id(curr) not in seen:
        seen.add(id(curr))
        if pattern in str(curr):
            return True
        # Check cause before context
        next_exc = curr.__cause__ if curr.__cause__ is not None else curr.__context__
        curr = next_exc
    return False


@pytest.mark.e2e
async def test_untrusted_post_blocks_llm_call(
    fake_llm_server: FakeHttpServer,
    fake_data_server: FakeHttpServer,
    patched_interceptor_with_trust,
) -> None:
    """D: LLM server URL NOT in trusted_endpoints → LLM POST raises BLOCKED.

    Validates that the trust gate now fires on POST (Phase 1 Prereq B).
    Uses patched_interceptor_with_trust so the real trust gate fires.

    The BLOCKED RuntimeError is raised inside _attach() during AsyncClient.send,
    which the openai SDK wraps in an APIConnectionError; we therefore inspect
    the full exception chain rather than matching the top-level message.
    """
    rows, allowlist = patched_interceptor_with_trust

    # Only trust the data server; omit the LLM server
    allowlist.add(normalize_url_for_trust(fake_data_server.base_url))
    # LLM server deliberately omitted

    _configure_agent_client(fake_llm_server)

    data_url = f"{fake_data_server.base_url}/v1/temperature"

    @function_tool
    def get_temperature() -> dict:
        """Get the current temperature."""
        return requests_lib.get(data_url).json()

    agent = Agent(
        name="weather-agent",
        instructions="Use the get_temperature tool and report the result.",
        tools=[get_temperature],
        model="gpt-4o-mini",
    )

    with pytest.raises(Exception) as exc_info:
        await Runner.run(agent, "What's the temp?")

    assert _exception_chain_contains(exc_info.value, "BLOCKED"), (
        f"Expected 'BLOCKED' somewhere in the exception chain. Got: {exc_info.value!r}"
    )


# ---------------------------------------------------------------------------
# Scenario E — self-egress exemption: evaluate_handoff completes even when
#              the Provably backend URL is not in trusted_endpoints
# ---------------------------------------------------------------------------

@pytest.mark.e2e
def test_self_egress_completes_without_trust(
    fake_server_factory,
    patched_interceptor: list[dict[str, Any]],
    fake_trusted_endpoints: set[str],
) -> None:
    """E: Provably backend NOT in trusted_endpoints; evaluate_handoff still completes.

    The SDK wraps its own egress with provably_self_egress() so the trust gate
    never fires on internal SDK calls.
    """
    # Leave trusted_endpoints completely empty — the Provably backend is not trusted
    assert len(fake_trusted_endpoints) == 0

    fake_provably = fake_server_factory()
    fake_provably.respond(
        "GET",
        "/api/v1/organizations/org-1/queries/q1",
        status=200,
        body=_stored({"x": 1}),
    )
    fake_provably.respond(
        "POST",
        "/api/v1/organizations/org-1/queries/q1/verify",
        status=200,
        body={"verified": True},
    )

    payload = HandoffPayload(
        provably_org_id="org-1",
        integration_api_key="key-abc",
        claims=[
            HandoffClaim(
                action_name="get_data",
                claimed_value={"x": 1},
                query_record_id="q1",
            )
        ],
    )

    # This must NOT raise BLOCKED — SDK egress is exempt from trust gate
    eval_result = evaluate_handoff(payload, provably_base_url=fake_provably.base_url)
    assert eval_result["outcome"] == "PASS", f"Expected PASS, got: {eval_result}"


# ---------------------------------------------------------------------------
# Scenario F — async LLM call is intercepted
# ---------------------------------------------------------------------------

@pytest.mark.e2e
async def test_async_llm_call_intercepted(
    fake_llm_server: FakeHttpServer,
    fake_data_server: FakeHttpServer,
    patched_interceptor: list[dict[str, Any]],
    fake_trusted_endpoints: set[str],
) -> None:
    """F: assert at least one recorded row has method==POST from the fake LLM server.

    Validates that httpx.AsyncClient.send is patched and recording fires.
    """
    fake_trusted_endpoints.add(normalize_url_for_trust(fake_llm_server.base_url))
    fake_trusted_endpoints.add(normalize_url_for_trust(fake_data_server.base_url))

    _configure_agent_client(fake_llm_server)

    data_url = f"{fake_data_server.base_url}/v1/temperature"

    @function_tool
    def get_temperature() -> dict:
        """Get the current temperature."""
        return requests_lib.get(data_url).json()

    agent = Agent(
        name="weather-agent",
        instructions="Use the get_temperature tool and report the result.",
        tools=[get_temperature],
        model="gpt-4o-mini",
    )

    await Runner.run(agent, "What's the temp?")

    # Assert at least one POST row exists and its URL points to the fake LLM server
    llm_base = normalize_url_for_trust(fake_llm_server.base_url)
    post_llm_rows = [
        r for r in patched_interceptor
        if r["method"] == "POST" and llm_base in normalize_url_for_trust(r["url"])
    ]
    assert len(post_llm_rows) >= 1, (
        f"Expected at least one POST row to LLM server {llm_base}. "
        f"Recorded rows: {[(r['method'], r['url']) for r in patched_interceptor]}"
    )
