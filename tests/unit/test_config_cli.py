"""Tests for sourcerykit.cli.config."""

import uuid
from unittest.mock import MagicMock, patch

from sourcerykit.cli.config import list as config_list


def _make_settings(**overrides: object) -> MagicMock:
    """Build a mock Settings with sensible defaults."""
    s = MagicMock()
    s.api_key = overrides.get("api_key", "zk-12345678-1234-1234-1234-123456789abc")
    s.org_id = overrides.get("org_id", uuid.uuid4())
    s.postgres_url = overrides.get("postgres_url", "postgresql://user:secret@host:5432/db")
    s.project_name = overrides.get("project_name", "my-project")
    return s


class TestConfigList:
    def test_shows_masked_key_by_default(self) -> None:
        s = _make_settings()
        with (
            patch("sourcerykit.cli.config.require_settings", return_value=s),
            patch("sourcerykit.cli.config.console") as mock_console,
        ):
            config_list(show_key=False)

        # Verify console.print was called with masked key
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("****" in c or "***" in c for c in calls)

    def test_shows_full_key_with_show_key(self) -> None:
        api_key = "zk-12345678-1234-1234-1234-123456789abc"
        s = _make_settings(api_key=api_key)
        with (
            patch("sourcerykit.cli.config.require_settings", return_value=s),
            patch("sourcerykit.cli.config.console") as mock_console,
        ):
            config_list(show_key=True)

        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any(api_key in c for c in calls)

    def test_masks_postgres_password(self) -> None:
        s = _make_settings(postgres_url="postgresql://user:secret@host:5432/db")
        with (
            patch("sourcerykit.cli.config.require_settings", return_value=s),
            patch("sourcerykit.cli.config.console") as mock_console,
        ):
            config_list(show_key=False)

        calls = [str(c) for c in mock_console.print.call_args_list]
        # Password should be masked in the postgres URL display
        assert any("***" in c for c in calls)
