"""Tests for sourcerykit.config.Settings and get_settings."""

import uuid
from collections.abc import Generator

import pytest

from sourcerykit.config import Settings, get_settings
from sourcerykit.errors import SourceryKitConfigError

_VALID_ORG = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None, None, None]:
    """Clear lru_cache between tests so env var changes are picked up."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------


class TestSettings:
    def test_construction_with_all_required_fields(self) -> None:
        s = Settings(
            api_key="my-key",
            org_id=uuid.UUID(_VALID_ORG),
            postgres_url="postgresql://user:pass@localhost/db",
        )
        assert s.api_key == "my-key"
        assert s.postgres_url == "postgresql://user:pass@localhost/db"

    def test_defaults_for_optional_url_fields(self) -> None:
        s = Settings(
            api_key="k",
            org_id=uuid.UUID(_VALID_ORG),
            postgres_url="postgresql://x",
        )
        assert s.provably_app == "https://app.provably.ai"
        assert s.provably_api == "https://api.provably.ai"
        assert s.provably_mcp == "https://mcp.provably.ai"

    def test_raises_config_error_when_api_key_missing(self) -> None:
        with pytest.raises(SourceryKitConfigError, match="SOURCERYKIT_API_KEY"):
            Settings(api_key="", org_id=uuid.UUID(_VALID_ORG), postgres_url="postgresql://x")

    def test_raises_config_error_when_org_id_is_nil(self) -> None:
        nil_uuid = uuid.UUID(int=0)
        with pytest.raises(SourceryKitConfigError, match="SOURCERYKIT_ORG_ID"):
            Settings(api_key="k", org_id=nil_uuid, postgres_url="postgresql://x")

    def test_raises_config_error_when_postgres_url_missing(self) -> None:
        with pytest.raises(SourceryKitConfigError, match="SOURCERYKIT_POSTGRES_URL"):
            Settings(api_key="k", org_id=uuid.UUID(_VALID_ORG), postgres_url="")

    def test_raises_config_error_lists_all_missing_fields(self) -> None:
        nil = uuid.UUID(int=0)
        with pytest.raises(SourceryKitConfigError) as exc_info:
            Settings(api_key="", org_id=nil, postgres_url="")
        msg = str(exc_info.value)
        assert "SOURCERYKIT_API_KEY" in msg
        assert "SOURCERYKIT_ORG_ID" in msg
        assert "SOURCERYKIT_POSTGRES_URL" in msg

    def test_is_frozen(self) -> None:
        s = Settings(api_key="k", org_id=uuid.UUID(_VALID_ORG), postgres_url="postgresql://x")
        with pytest.raises((AttributeError, TypeError)):
            s.api_key = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# get_settings
# ---------------------------------------------------------------------------


class TestGetSettings:
    def test_reads_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOURCERYKIT_API_KEY", "env-key")
        monkeypatch.setenv("SOURCERYKIT_ORG_ID", _VALID_ORG)
        monkeypatch.setenv("SOURCERYKIT_POSTGRES_URL", "postgresql://env/db")
        s = get_settings()
        assert s.api_key == "env-key"
        assert str(s.org_id) == _VALID_ORG
        assert s.postgres_url == "postgresql://env/db"

    def test_optional_env_vars_override_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOURCERYKIT_API_KEY", "k")
        monkeypatch.setenv("SOURCERYKIT_ORG_ID", _VALID_ORG)
        monkeypatch.setenv("SOURCERYKIT_POSTGRES_URL", "postgresql://x")
        monkeypatch.setenv("SOURCERYKIT_PROVABLY_APP_URL", "https://custom-app.example.com")
        s = get_settings()
        assert s.provably_app == "https://custom-app.example.com"

    def test_raises_config_error_when_env_vars_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for key in (
            "SOURCERYKIT_API_KEY",
            "SOURCERYKIT_ORG_ID",
            "SOURCERYKIT_POSTGRES_URL",
            "SOURCERYKIT_PROVABLY_APP_URL",
            "SOURCERYKIT_PROVABLY_API_URL",
            "SOURCERYKIT_PROVABLY_MCP_URL",
        ):
            monkeypatch.delenv(key, raising=False)
        with pytest.raises(SourceryKitConfigError):
            get_settings()

    def test_result_is_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOURCERYKIT_API_KEY", "k")
        monkeypatch.setenv("SOURCERYKIT_ORG_ID", _VALID_ORG)
        monkeypatch.setenv("SOURCERYKIT_POSTGRES_URL", "postgresql://x")
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
