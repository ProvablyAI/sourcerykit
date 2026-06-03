from __future__ import annotations

from typing import Any

import pytest

from provably.handoff import client
from provably.handoff.client import initialize_runtime


@pytest.fixture
def spies(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    calls: dict[str, list[Any]] = {"bootstrap": [], "padding": [], "preprocess": []}

    monkeypatch.setattr(client, "ensure_bootstrap_cached", lambda: calls["bootstrap"].append(True))
    monkeypatch.setattr(
        client,
        "ensure_preprocess_intercept_padding",
        lambda url: calls["padding"].append(url),
    )
    monkeypatch.setattr(
        client,
        "run_preprocess",
        lambda org, mw, tbl: calls["preprocess"].append((org, mw, tbl)),
    )
    monkeypatch.setattr(
        client,
        "cache",
        lambda: {"org_id": "org-1", "middleware_id": "mw-1", "table_id": "tbl-1"},
    )
    return calls


def test_preprocess_false_short_circuits_after_bootstrap(
    spies: dict[str, list[Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POSTGRES_URL", "postgres://x")

    initialize_runtime(preprocess=False)

    assert spies["bootstrap"] == [True]
    assert spies["padding"] == []
    assert spies["preprocess"] == []


def test_runs_padding_and_preprocess_when_postgres_url_set(
    spies: dict[str, list[Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POSTGRES_URL", "postgres://host/app")

    initialize_runtime()

    assert spies["bootstrap"] == [True]
    assert spies["padding"] == ["postgres://host/app"]
    assert spies["preprocess"] == [("org-1", "mw-1", "tbl-1")]


def test_skips_padding_when_postgres_url_missing(
    spies: dict[str, list[Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("POSTGRES_URL", raising=False)

    initialize_runtime()

    assert spies["padding"] == []
    # run_preprocess still fires using cached ids
    assert spies["preprocess"] == [("org-1", "mw-1", "tbl-1")]


def test_blank_postgres_url_treated_as_missing(
    spies: dict[str, list[Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POSTGRES_URL", "   ")

    initialize_runtime()

    assert spies["padding"] == []
    assert spies["preprocess"] == [("org-1", "mw-1", "tbl-1")]
