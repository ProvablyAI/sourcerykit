"""Tests for sourcerykit.cli.config."""

import uuid
from unittest.mock import MagicMock, patch

from sourcerykit.cli.config import list as config_list


def _make_settings(**overrides: object) -> MagicMock:
    """Build a mock Settings with sensible defaults."""
    s = MagicMock()
    s.org_id = overrides.get("org_id", uuid.uuid4())
    s.postgres_url = overrides.get("postgres_url", "postgresql://user:secret@host:5432/db")
    s.project_name = overrides.get("project_name", "my-project")
    return s


class TestConfigList:
    def test_shows_org_id(self) -> None:
        s = _make_settings()
        with (
            patch("sourcerykit.cli.config.require_settings", return_value=s),
            patch("sourcerykit.cli.config.console") as mock_console,
        ):
            config_list(show_key=False)

        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any(str(s.org_id) in c for c in calls)

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
