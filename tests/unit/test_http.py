from __future__ import annotations

import pytest

from provably.handoff._http import (
    _infer_app_ui_base_from_rust_api_url,
    _resolved_app_ui_base,
    base_url,
    headers,
    org_id,
    query_record_page_url,
)


class TestEnvAccessors:
    def test_base_url_strips_trailing_slash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROVABLY_RUST_BE_URL", "https://api.test/")
        assert base_url() == "https://api.test"

    def test_base_url_requires_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PROVABLY_RUST_BE_URL", raising=False)
        with pytest.raises(ValueError, match="PROVABLY_RUST_BE_URL"):
            base_url()

    def test_headers_include_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROVABLY_API_KEY", "secret")
        h = headers()
        assert h["x-api-key"] == "secret"
        assert h["Content-Type"] == "application/json"

    def test_org_id_requires_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PROVABLY_ORG_ID", raising=False)
        with pytest.raises(ValueError, match="PROVABLY_ORG_ID"):
            org_id()


class TestInferAppUiBase:
    @pytest.mark.parametrize(
        ("rust_url", "expected"),
        [
            ("https://api-dev.provably.ai", "https://app-dev.provably.ai"),
            ("https://api.provably.ai", "https://app.provably.ai"),
            ("https://eu.api-dev.provably.ai", "https://eu.app-dev.provably.ai"),
            ("https://api2.provably.ai", "https://app2.provably.ai"),
        ],
    )
    def test_rewrites_api_label_to_app(self, rust_url: str, expected: str) -> None:
        assert _infer_app_ui_base_from_rust_api_url(rust_url) == expected

    def test_returns_empty_for_blank(self) -> None:
        assert _infer_app_ui_base_from_rust_api_url("") == ""

    def test_returns_empty_for_non_provably_host(self) -> None:
        assert _infer_app_ui_base_from_rust_api_url("https://api.example.com") == ""

    def test_returns_empty_when_no_api_label(self) -> None:
        assert _infer_app_ui_base_from_rust_api_url("https://gateway.provably.ai") == ""

    def test_accepts_url_without_scheme(self) -> None:
        assert _infer_app_ui_base_from_rust_api_url("api-dev.provably.ai") == "https://app-dev.provably.ai"


class TestResolvedAppUiBase:
    def test_prefers_explicit_app_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROVABLY_APP_UI_URL", "https://app-dev.provably.ai/")
        assert _resolved_app_ui_base() == "https://app-dev.provably.ai"

    def test_normalizes_explicit_api_url_to_app(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROVABLY_APP_UI_URL", "https://api-dev.provably.ai")
        assert _resolved_app_ui_base() == "https://app-dev.provably.ai"

    def test_infers_from_rust_be_url_when_app_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PROVABLY_APP_UI_URL", raising=False)
        monkeypatch.setenv("PROVABLY_RUST_BE_URL", "https://api-dev.provably.ai")
        assert _resolved_app_ui_base() == "https://app-dev.provably.ai"

    def test_empty_when_nothing_resolves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PROVABLY_APP_UI_URL", raising=False)
        monkeypatch.setenv("PROVABLY_RUST_BE_URL", "https://gateway.example.com")
        assert _resolved_app_ui_base() == ""


class TestQueryRecordPageUrl:
    def test_uses_app_deep_link_when_resolvable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PROVABLY_APP_UI_URL", "https://app-dev.provably.ai")
        url = query_record_page_url("org-1", "q-9")
        assert url == "https://app-dev.provably.ai/org/org-1/query-record/q-9"

    def test_falls_back_to_api_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PROVABLY_APP_UI_URL", raising=False)
        monkeypatch.setenv("PROVABLY_RUST_BE_URL", "https://api.test")
        url = query_record_page_url("org-1", "q-9")
        assert url == "https://api.test/api/v1/organizations/org-1/queries/q-9"
