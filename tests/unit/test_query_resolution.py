from __future__ import annotations

from typing import Any

import pytest

from provably.handoff._query_resolution import resolve_query_record_ids_for_truths


@pytest.fixture
def fake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVABLY_RUST_BE_URL", "https://api.test")
    monkeypatch.setenv("PROVABLY_QUERY_RESOLVE_MAX_WAIT_S", "1")


def test_resolves_matching_query_by_indexed_result(
    fake_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROVABLY_APP_UI_URL", "https://app.test")
    api_row = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "result": {"x": 1, "y": 2},
    }

    def fake_get(_path: str, _params: dict[str, Any], **_kw: Any) -> list[dict[str, Any]]:
        return [api_row]

    monkeypatch.setattr("provably.handoff._query_resolution.get_json_params", fake_get)

    out = resolve_query_record_ids_for_truths(
        [{"y": 2, "x": 1}],
        "org-1",
        "coll-uuid",
        max_wait_s=2.0,
        poll_s=0.0,
    )
    assert len(out) == 1
    assert out[0][0] == "550e8400-e29b-41d4-a716-446655440000"
    assert out[0][1] == (
        "https://app.test/org/org-1/query-record/550e8400-e29b-41d4-a716-446655440000"
    )


def test_two_claims_two_rows_same_shape(
    fake_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [
        {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "result": {"v": 1},
        },
        {
            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "result": {"v": 1},
        },
    ]

    monkeypatch.setattr(
        "provably.handoff._query_resolution.get_json_params",
        lambda _p, _params, **_k: rows,
    )

    out = resolve_query_record_ids_for_truths(
        [{"v": 1}, {"v": 1}],
        "org-1",
        "coll-uuid",
        max_wait_s=2.0,
        poll_s=0.0,
    )
    assert [o[0] for o in out] == [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    ]
