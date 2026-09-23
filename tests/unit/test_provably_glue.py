"""Tests for sourcerykit._provably — how sourcerykit plugs into the Provably SDK."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from provably import OAuthTokens
from provably._config import current

from sourcerykit import _provably
from sourcerykit._provably import SourceryKitTokenStore, sdk_config
from sourcerykit.errors import SourceryKitConfigError
from sourcerykit.intercept._self_egress import is_self_egress

_ORG = "00000000-0000-0000-0000-000000000001"


class TestSdkIsConfigured:
    def test_importing_sourcerykit_points_the_sdk_at_its_settings_store_and_egress(self) -> None:
        setup = current()
        assert setup.config is sdk_config
        assert isinstance(setup.tokens, SourceryKitTokenStore)
        # Without this, the interceptor would record and gate the SDK's own calls.
        with setup.egress():
            assert is_self_egress()

    def test_config_before_setup_has_urls_and_no_org(self) -> None:
        with (
            patch.object(_provably, "get_settings", side_effect=SourceryKitConfigError("not set up")),
            patch.object(_provably, "get_bootstrap_settings", return_value="https://api.example"),
            patch.object(_provably, "get_bootstrap_app_url", return_value="https://app.example"),
        ):
            config = sdk_config()
        assert (config.api_url, config.app_url, config.org_id) == ("https://api.example", "https://app.example", None)


class TestTokenStorePersistence:
    def test_save_writes_to_app_store_and_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = tmp_path / "app.env"
        monkeypatch.setenv("SOURCERYKIT_TOKEN_STORE", str(store))

        with (
            patch.object(_provably, "get_settings") as mock_gs,
            patch.object(_provably, "load_local_env") as mock_lle,
            patch.object(_provably, "save_app_dir_config") as mock_save,
        ):
            SourceryKitTokenStore().save(
                OAuthTokens(access_token="at2", refresh_token="rt2", client_id="sourcerykit-cli")
            )

        mock_save.assert_not_called()
        assert os.environ["PROVABLY_ACCESS_TOKEN"] == "at2"
        assert os.environ["PROVABLY_REFRESH_TOKEN"] == "rt2"
        content = store.read_text()
        assert "PROVABLY_ACCESS_TOKEN" in content and "at2" in content
        assert "PROVABLY_REFRESH_TOKEN" in content and "rt2" in content
        mock_lle.cache_clear.assert_called_once()
        mock_gs.cache_clear.assert_called_once()

    def test_save_uses_global_json_when_no_store(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SOURCERYKIT_TOKEN_STORE", raising=False)
        with patch.object(_provably, "save_app_dir_config") as mock_save:
            SourceryKitTokenStore().save(
                OAuthTokens(access_token="at", refresh_token=None, client_id="sourcerykit-cli")
            )
        mock_save.assert_called_once_with(token="at", refresh_token=None)

    def test_clear_refresh_token_from_app_store(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = tmp_path / "app.env"
        monkeypatch.setenv("SOURCERYKIT_TOKEN_STORE", str(store))
        store.write_text("PROVABLY_REFRESH_TOKEN=rt\n")
        monkeypatch.setenv("PROVABLY_REFRESH_TOKEN", "rt")

        SourceryKitTokenStore().clear_refresh_token()

        assert "PROVABLY_REFRESH_TOKEN" not in os.environ
        assert "PROVABLY_REFRESH_TOKEN=" in store.read_text()

    def test_load_reads_the_session_from_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from sourcerykit.config import get_settings

        monkeypatch.setenv("PROVABLY_ACCESS_TOKEN", "at")
        monkeypatch.setenv("PROVABLY_REFRESH_TOKEN", "rt")
        monkeypatch.setenv("SOURCERYKIT_ORG_ID", _ORG)
        get_settings.cache_clear()
        try:
            # A refresh must name the client; the SDK has no default, so the store supplies it.
            assert SourceryKitTokenStore().load() == OAuthTokens(
                access_token="at", refresh_token="rt", client_id="sourcerykit-cli"
            )
        finally:
            get_settings.cache_clear()


def test_consent_page_has_its_own_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOURCERYKIT_CONSENT_URL", raising=False)
    # The app URL is the base of query-record links, so it must not move the consent page.
    monkeypatch.setenv("SOURCERYKIT_PROVABLY_APP_URL", "https://app.example")
    assert _provably.consent_page_url() == "https://switchboard.provably.ai/consent"

    monkeypatch.setenv("SOURCERYKIT_CONSENT_URL", "http://localhost:3000/consent")
    assert _provably.consent_page_url() == "http://localhost:3000/consent"
