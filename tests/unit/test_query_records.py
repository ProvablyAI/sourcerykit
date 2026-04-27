from __future__ import annotations

from typing import Any

import pytest

from provably.handoff._query_records import create_query_record_for_intercept


@pytest.fixture
def fake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVABLY_RUST_BE_URL", "https://api.test")
    monkeypatch.setenv("PROVABLY_API_KEY", "k")
    monkeypatch.setenv("PROVABLY_ORG_ID", "org-1")


def test_creates_query_record_and_returns_id_url(
    fake_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cluster A path: SQL POST + generate_proof POST + wait. No /verify (that's cluster B)."""
    monkeypatch.setenv("PROVABLY_APP_UI_URL", "https://app.test")
    posted: list[tuple[str, dict[str, Any]]] = []

    def fake_post(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        posted.append((path, payload or {}))
        if path.endswith("/query"):
            return {"id": "q-uuid"}
        return {}

    def fake_wait(_org: str, _qid: str, timeout_s: float = 180.0) -> None:
        return None

    monkeypatch.setattr("provably.handoff._query_records.post_json", fake_post)
    monkeypatch.setattr("provably.handoff._query_records.wait_for_proof_completed", fake_wait)

    qid, qurl = create_query_record_for_intercept(
        "endpoint_0",
        agent_id="fetch_and_claim",
        middleware_id="mw-1",
        collection_id="coll-1",
    )
    assert qid == "q-uuid"
    assert qurl == "https://app.test/org/org-1/query-record/q-uuid"

    paths = [p for p, _ in posted]
    assert paths == [
        "/api/v1/organizations/org-1/middlewares/mw-1/query",
        "/api/v1/organizations/org-1/queries/q-uuid/generate_proof",
    ]
    assert not any(p.endswith("/verify") for p in paths), (
        "create_query_record_for_intercept must not call /verify; that runs in evaluator (cluster B)"
    )

    sql_body = posted[0][1]
    assert sql_body["require_proof"] is True
    assert sql_body["collection_id"] == "coll-1"
    # No row_id supplied → fallback filter on action_name (single = predicate).
    assert sql_body["query"] == "SELECT * FROM provably_intercepts WHERE action_name = 'endpoint_0'"


def test_creates_query_record_with_row_id_uses_id_filter(
    fake_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When row_id is provided the SQL must use WHERE id = N (integer PK, single predicate)."""
    monkeypatch.setenv("PROVABLY_APP_UI_URL", "https://app.test")
    captured: dict[str, Any] = {}

    def fake_post(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if path.endswith("/query"):
            captured["body"] = payload or {}
            return {"id": "q-uuid"}
        return {}

    monkeypatch.setattr("provably.handoff._query_records.post_json", fake_post)
    monkeypatch.setattr("provably.handoff._query_records.wait_for_proof_completed", lambda *_a, **_kw: None)

    create_query_record_for_intercept(
        "endpoint_0",
        agent_id="fetch_and_claim",
        middleware_id="mw-1",
        collection_id="coll-1",
        row_id=42,
    )
    assert captured["body"]["query"] == "SELECT * FROM provably_intercepts WHERE id = 42"


def test_creates_query_record_falls_back_to_api_url_without_app_ui(
    fake_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PROVABLY_APP_UI_URL", raising=False)

    def fake_post(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if path.endswith("/query"):
            return {"id": "q-uuid"}
        return {}

    monkeypatch.setattr("provably.handoff._query_records.post_json", fake_post)
    monkeypatch.setattr("provably.handoff._query_records.wait_for_proof_completed", lambda *_a, **_kw: None)

    _qid, qurl = create_query_record_for_intercept(
        "endpoint_0",
        agent_id="fetch_and_claim",
        middleware_id="mw-1",
        collection_id="coll-1",
    )
    assert qurl == "https://api.test/api/v1/organizations/org-1/queries/q-uuid"


def test_infers_app_deep_link_when_only_rust_be_is_provably_saas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If ``PROVABLY_APP_UI_URL`` is unset but ``PROVABLY_RUST_BE_URL`` is *.provably.ai, infer ``app-*``."""
    monkeypatch.setenv("PROVABLY_RUST_BE_URL", "https://api-dev.provably.ai")
    monkeypatch.setenv("PROVABLY_API_KEY", "k")
    monkeypatch.setenv("PROVABLY_ORG_ID", "org-1")
    monkeypatch.delenv("PROVABLY_APP_UI_URL", raising=False)

    def fake_post(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if path.endswith("/query"):
            return {"id": "q-uuid"}
        return {}

    monkeypatch.setattr("provably.handoff._query_records.post_json", fake_post)
    monkeypatch.setattr("provably.handoff._query_records.wait_for_proof_completed", lambda *_a, **_kw: None)

    _qid, qurl = create_query_record_for_intercept(
        "endpoint_0",
        agent_id="fetch_and_claim",
        middleware_id="mw-1",
        collection_id="coll-1",
    )
    assert qurl == "https://app-dev.provably.ai/org/org-1/query-record/q-uuid"


def test_escapes_single_quotes_in_sql(
    fake_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_post(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if path.endswith("/query"):
            captured["body"] = payload or {}
            return {"id": "q-uuid"}
        return {}

    monkeypatch.setattr("provably.handoff._query_records.post_json", fake_post)
    monkeypatch.setattr("provably.handoff._query_records.wait_for_proof_completed", lambda *_a, **_kw: None)

    create_query_record_for_intercept(
        "O'Reilly",
        agent_id="fetch_and_claim",
        middleware_id="mw-1",
        collection_id="coll-1",
    )
    # No row_id → fallback filter on action_name; apostrophe must be SQL-escaped.
    assert "WHERE action_name = 'O''Reilly'" in captured["body"]["query"]


@pytest.mark.parametrize(
    ("agent_id", "action_name"),
    [("", "act"), ("ag", "")],
)
def test_rejects_empty_args(
    fake_env: None,
    agent_id: str,
    action_name: str,
) -> None:
    with pytest.raises(ValueError):
        create_query_record_for_intercept(
            action_name,
            agent_id=agent_id,
            middleware_id="mw-1",
            collection_id="coll-1",
        )
