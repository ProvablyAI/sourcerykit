"""End-to-end tests for OpenAI Agents SDK integration.

Six scenarios drive a fake LLM server + fake data server through the full
intercept → handoff → evaluate flow:

  A – happy path: all URLs trusted, evaluate_handoff → PASS
  B – tampered claim: claimed_value wrong → CAUGHT
  C – untrusted GET: data URL not in allowlist → tool call raises BLOCKED
  D – untrusted POST: LLM URL not in allowlist → LLM POST raises BLOCKED
  E – self-egress exemption: Provably backend NOT in allowlist; evaluate_handoff still completes
  F – async LLM coverage: at least one recorded POST row from the LLM server

Trust-gate testing notes (scenarios C and D):
    ``patched_interceptor`` replaces ``_insert_row`` entirely, bypassing the
    ``_storage.insert_intercept_row`` path (and therefore the trust check). For C and D the
    trust check must fire while still avoiding a real DB write, so those scenarios use
    ``patched_interceptor_with_trust`` which patches ``_require_trusted_endpoint`` +
    ``_write_row`` instead and sets a sentinel ``POSTGRES_URL``.
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
from tests.e2e.conftest import FakeHttpServer, FakeResponse

# ---------------------------------------------------------------------------
# Fake LLM ChatCompletion JSON responses
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
                            "function": {"name": tool_name, "arguments": arguments},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
                "logprobs": None,
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
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
                "message": {"role": "assistant", "content": content, "tool_calls": None},
                "finish_reason": "stop",
                "logprobs": None,
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_llm_server(fake_server_factory) -> FakeHttpServer:
    """Fake LLM: tool_call response on the first POST, final assistant message after that."""
    server = fake_server_factory()
    call_count = [0]

    def _handle_chat(_req):
        call_count[0] += 1
        body = _tool_call_response("get_temperature") if call_count[0] == 1 else _final_response()
        return FakeResponse(status=200, body=body)

    server.route("POST", "/v1/chat/completions", _handle_chat)
    return server


@pytest.fixture
def fake_data_server(fake_server_factory) -> FakeHttpServer:
    """Fake data API: GET /v1/temperature → {'celsius': 21}."""
    server = fake_server_factory()
    server.respond("GET", "/v1/temperature", status=200, body={"celsius": 21})
    return server


def _trusted_check(allowlist: set[str], url: str) -> None:
    """Prefix-aware trust check.

    Mirrors real-world usage where users register a service base URL (e.g.
    ``http://127.0.0.1:9000``) and any path under that base is allowed.
    """
    norm = normalize_url_for_trust(url)
    for trusted in allowlist:
        if norm == trusted or norm.startswith(trusted + "/") or norm.startswith(trusted + "?"):
            return
    raise RuntimeError(f"BLOCKED: {url} not in trusted_endpoints")


@pytest.fixture
def fake_trusted_endpoints(monkeypatch: pytest.MonkeyPatch) -> set[str]:
    """In-memory allowlist for ``_require_trusted_endpoint``.

    Only sufficient when paired with ``patched_interceptor`` (which bypasses
    ``insert_intercept_row``). For scenarios needing the real trust gate to fire (C, D),
    use ``patched_interceptor_with_trust``.
    """
    allowlist: set[str] = set()
    monkeypatch.setattr(
        "provably.intercept._storage._require_trusted_endpoint",
        lambda _pg, url: _trusted_check(allowlist, url),
    )
    return allowlist


@pytest.fixture
def patched_interceptor_with_trust(monkeypatch: pytest.MonkeyPatch) -> tuple[list[dict[str, Any]], set[str]]:
    """Like ``patched_interceptor`` but with the trust gate active.

    Lets ``insert_intercept_row`` actually run so ``_require_trusted_endpoint`` fires; avoids
    a real Postgres connection by:
      1. Setting a sentinel ``POSTGRES_URL`` so the early-return guard is skipped.
      2. Replacing ``_require_trusted_endpoint`` with the in-memory prefix check.
      3. Replacing ``_write_row`` with a no-op that records to an in-memory list.
    """
    rows: list[dict[str, Any]] = []
    allowlist: set[str] = set()

    monkeypatch.setenv("POSTGRES_URL", "postgresql://fake-host/fake-db")
    monkeypatch.setattr(
        _storage_module, "_require_trusted_endpoint", lambda _pg, url: _trusted_check(allowlist, url)
    )
    monkeypatch.setattr(
        _storage_module,
        "_write_row",
        lambda *_a, **_kw: rows.append({"url": _a[1], "method": _a[2], "request": _a[3], "raw": _a[4]}),
    )

    _interceptor_module.init_interceptor()
    monkeypatch.setattr(_interceptor_module, "_enabled", True)
    return rows, allowlist


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _seed_allowlist(allowlist: set[str], *servers: FakeHttpServer) -> None:
    """Seed an allowlist with the normalized base URLs of the given fake servers."""
    for s in servers:
        allowlist.add(normalize_url_for_trust(s.base_url))


def _configure_agent_client(fake_llm_server: FakeHttpServer) -> None:
    """Point the agents SDK at the fake LLM server and force chat completions mode."""
    client = AsyncOpenAI(base_url=f"{fake_llm_server.base_url}/v1", api_key="test-key")
    set_default_openai_client(client, use_for_tracing=False)
    set_default_openai_api("chat_completions")


def _make_weather_agent(
    fake_data_server: FakeHttpServer, *, fail_loudly: bool = False
) -> Agent:
    """Build the standard weather agent that GETs ``/v1/temperature`` from the fake data server.

    ``fail_loudly=True`` sets ``failure_error_function=None`` on the tool so that exceptions
    raised inside the tool propagate up through ``Runner.run`` instead of being converted
    into LLM-visible error strings (used by scenario C).
    """
    data_url = f"{fake_data_server.base_url}/v1/temperature"
    decorator = function_tool(failure_error_function=None) if fail_loudly else function_tool

    @decorator
    def get_temperature() -> dict:
        """Get the current temperature."""
        return requests_lib.get(data_url).json()

    return Agent(
        name="weather-agent",
        instructions="Use the get_temperature tool and report the result.",
        tools=[get_temperature],
        model="gpt-4o-mini",
    )


def _make_provably_backend(
    fake_server_factory, query_record_id: str, indexed_value: dict
) -> FakeHttpServer:
    """Spin up a fake Provably backend that resolves one query record + one verify call."""
    server = fake_server_factory()
    base = f"/api/v1/organizations/org-1/queries/{query_record_id}"
    server.respond("GET", base, status=200, body={"result": indexed_value})
    server.respond("POST", f"{base}/verify", status=200, body={"verified": True})
    return server


def _make_payload(query_record_id: str, claimed_value: dict) -> HandoffPayload:
    return HandoffPayload(
        provably_org_id="org-1",
        integration_api_key="key-abc",
        claims=[
            HandoffClaim(
                action_name="get_temperature",
                claimed_value=claimed_value,
                query_record_id=query_record_id,
            )
        ],
    )


def _exception_chain_contains(exc: BaseException, pattern: str) -> bool:
    """Walk ``__cause__``/``__context__`` looking for ``pattern`` (the agents SDK wraps
    ``RuntimeError`` from ``AsyncClient.send`` as ``APIConnectionError``)."""
    seen: set[int] = set()
    curr: BaseException | None = exc
    while curr is not None and id(curr) not in seen:
        seen.add(id(curr))
        if pattern in str(curr):
            return True
        curr = curr.__cause__ if curr.__cause__ is not None else curr.__context__
    return False


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@pytest.mark.e2e
async def test_openai_agent_intercepts_and_handoff_passes(
    fake_llm_server: FakeHttpServer,
    fake_data_server: FakeHttpServer,
    fake_server_factory,
    patched_interceptor: list[dict[str, Any]],
    fake_trusted_endpoints: set[str],
) -> None:
    """A — both URLs trusted; agent runs; evaluate_handoff → PASS."""
    _seed_allowlist(fake_trusted_endpoints, fake_llm_server, fake_data_server)
    _configure_agent_client(fake_llm_server)

    result = await Runner.run(_make_weather_agent(fake_data_server), "What's the temp?")
    assert result is not None

    methods = [r["method"] for r in patched_interceptor]
    assert methods.count("POST") >= 1, f"Expected ≥1 LLM POST, got {methods}"
    assert methods.count("GET") >= 1, f"Expected ≥1 data GET, got {methods}"

    fake_provably = _make_provably_backend(fake_server_factory, "q1", {"celsius": 21})
    eval_result = evaluate_handoff(
        _make_payload("q1", {"celsius": 21}), provably_base_url=fake_provably.base_url
    )
    assert eval_result["outcome"] == "PASS", f"Expected PASS, got: {eval_result}"
    assert eval_result["per_claim"][0]["result"] == "PASS"


@pytest.mark.e2e
async def test_evaluate_catches_wrong_claim(
    fake_llm_server: FakeHttpServer,
    fake_data_server: FakeHttpServer,
    fake_server_factory,
    patched_interceptor: list[dict[str, Any]],
    fake_trusted_endpoints: set[str],
) -> None:
    """B — happy run, but the claim's value disagrees with the indexed record → CAUGHT."""
    _seed_allowlist(fake_trusted_endpoints, fake_llm_server, fake_data_server)
    _configure_agent_client(fake_llm_server)

    await Runner.run(_make_weather_agent(fake_data_server), "What's the temp?")

    fake_provably = _make_provably_backend(fake_server_factory, "q1", {"celsius": 21})
    eval_result = evaluate_handoff(
        _make_payload("q1", {"celsius": 99}),  # tampered claim
        provably_base_url=fake_provably.base_url,
    )
    assert eval_result["outcome"] == "CAUGHT", f"Expected CAUGHT, got: {eval_result}"
    assert eval_result["per_claim"][0]["result"] == "CAUGHT"


@pytest.mark.e2e
async def test_untrusted_get_blocks_request(
    fake_llm_server: FakeHttpServer,
    fake_data_server: FakeHttpServer,
    patched_interceptor_with_trust: tuple[list[dict[str, Any]], set[str]],
) -> None:
    """C — data URL not in allowlist → tool GET raises BLOCKED."""
    _, allowlist = patched_interceptor_with_trust
    _seed_allowlist(allowlist, fake_llm_server)  # data server omitted on purpose
    _configure_agent_client(fake_llm_server)

    with pytest.raises((RuntimeError, Exception), match="BLOCKED"):
        await Runner.run(_make_weather_agent(fake_data_server, fail_loudly=True), "What's the temp?")


@pytest.mark.e2e
async def test_untrusted_post_blocks_llm_call(
    fake_llm_server: FakeHttpServer,
    fake_data_server: FakeHttpServer,
    patched_interceptor_with_trust: tuple[list[dict[str, Any]], set[str]],
) -> None:
    """D — LLM URL not in allowlist → LLM POST raises BLOCKED (validates POST trust gate).

    The BLOCKED RuntimeError is raised inside ``_attach()`` during ``AsyncClient.send``,
    which the agents SDK wraps as ``APIConnectionError`` — we walk the exception chain.
    """
    _, allowlist = patched_interceptor_with_trust
    _seed_allowlist(allowlist, fake_data_server)  # LLM server omitted on purpose
    _configure_agent_client(fake_llm_server)

    with pytest.raises(Exception) as exc_info:
        await Runner.run(_make_weather_agent(fake_data_server), "What's the temp?")

    assert _exception_chain_contains(exc_info.value, "BLOCKED"), (
        f"Expected 'BLOCKED' in exception chain. Got: {exc_info.value!r}"
    )


@pytest.mark.e2e
def test_self_egress_completes_without_trust(
    fake_server_factory,
    patched_interceptor: list[dict[str, Any]],
    fake_trusted_endpoints: set[str],
) -> None:
    """E — Provably backend NOT in trusted_endpoints; evaluate_handoff still completes.

    The SDK wraps its own egress in ``provably_self_egress()`` so the trust gate never fires
    on internal calls.
    """
    assert len(fake_trusted_endpoints) == 0  # nothing trusted
    fake_provably = _make_provably_backend(fake_server_factory, "q1", {"x": 1})

    eval_result = evaluate_handoff(
        _make_payload("q1", {"x": 1}), provably_base_url=fake_provably.base_url
    )
    assert eval_result["outcome"] == "PASS", f"Expected PASS, got: {eval_result}"


@pytest.mark.e2e
async def test_async_llm_call_intercepted(
    fake_llm_server: FakeHttpServer,
    fake_data_server: FakeHttpServer,
    patched_interceptor: list[dict[str, Any]],
    fake_trusted_endpoints: set[str],
) -> None:
    """F — at least one recorded POST row points at the fake LLM server (proves
    ``AsyncClient.send`` patch fires)."""
    _seed_allowlist(fake_trusted_endpoints, fake_llm_server, fake_data_server)
    _configure_agent_client(fake_llm_server)

    await Runner.run(_make_weather_agent(fake_data_server), "What's the temp?")

    llm_base = normalize_url_for_trust(fake_llm_server.base_url)
    post_llm_rows = [
        r for r in patched_interceptor
        if r["method"] == "POST" and llm_base in normalize_url_for_trust(r["url"])
    ]
    assert post_llm_rows, (
        f"Expected ≥1 POST row to LLM server {llm_base}. "
        f"Recorded: {[(r['method'], r['url']) for r in patched_interceptor]}"
    )
