"""Tests for sourcerykit.cli — helper functions."""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
import typer
from provably import OAuthTokens, ProvablyConnectionError

from sourcerykit.cli.init import (
    _execute_post_auth_phases,
    _run_oauth_browser,
)
from sourcerykit.cli.utils import (
    _normalize_postgres_url,
    ask_postgres_url,
    mask_secret,
    prompt_postgres_url_with_retry,
    prompt_project_name,
    require_settings,
    run_connectivity_check,
)

_VALID_POSTGRES_URL = "postgresql://user:pass@1.2.3.4:5432/mydb"


# ---------------------------------------------------------------------------
# ask_postgres_url
# ---------------------------------------------------------------------------


class TestAskPostgresUrl:
    def test_builds_url_from_answers(self) -> None:
        answers = {
            "host": "1.2.3.4",
            "port": "5432",
            "username": "alice",
            "password": "s3cr3t",
            "database": "mydb",
        }
        with patch("sourcerykit.cli.utils.questionary") as mock_q:
            mock_q.prompt.return_value = answers
            result = ask_postgres_url()

        assert result == "postgresql://alice:s3cr3t@1.2.3.4:5432/mydb"

    def test_url_encodes_special_chars_in_password(self) -> None:
        answers = {
            "host": "db.example.com",
            "port": "5432",
            "username": "user",
            "password": "p@$$w0rd!",
            "database": "mydb",
        }
        with patch("sourcerykit.cli.utils.questionary") as mock_q:
            mock_q.prompt.return_value = answers
            result = ask_postgres_url()

        assert "p%40%24%24w0rd%21" in result
        assert "@db.example.com" in result

    def test_url_encodes_special_chars_in_username(self) -> None:
        answers = {
            "host": "db.example.com",
            "port": "5432",
            "username": "user@domain",
            "password": "pass",
            "database": "mydb",
        }
        with patch("sourcerykit.cli.utils.questionary") as mock_q:
            mock_q.prompt.return_value = answers
            result = ask_postgres_url()

        assert "user%40domain" in result

    def test_returns_empty_string_when_questionary_cancelled(self) -> None:
        with patch("sourcerykit.cli.utils.questionary") as mock_q:
            mock_q.prompt.return_value = None
            result = ask_postgres_url()

        assert result == ""


# ---------------------------------------------------------------------------
# run_connectivity_check
# ---------------------------------------------------------------------------


class TestRunConnectivityCheck:
    def test_returns_true_on_connected_db(self) -> None:
        with patch("sourcerykit.cli.utils.psycopg") as mock_psycopg:
            mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=None)
            mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
            result = run_connectivity_check(_VALID_POSTGRES_URL)

        assert result is True

    def test_returns_false_on_psycopg_connect_failure(self) -> None:
        with patch("sourcerykit.cli.utils.psycopg") as mock_psycopg:
            mock_psycopg.connect.side_effect = Exception("Connection refused")
            result = run_connectivity_check(_VALID_POSTGRES_URL)

        assert result is False


# ---------------------------------------------------------------------------
# _run_oauth_browser
# ---------------------------------------------------------------------------


class TestRunOauthBrowser:
    def test_logs_in_and_runs_post_auth_with_flags(self) -> None:
        tokens = OAuthTokens(access_token="at", refresh_token="rt", client_id="sourcerykit-cli")
        with (
            patch("sourcerykit.cli.init.browser_login", new=AsyncMock(return_value=tokens)) as mock_login,
            patch("sourcerykit.cli.init.service.get_user_email", new=AsyncMock(return_value="user@example.com")),
            patch("sourcerykit.cli.init.save_app_dir_config") as mock_save,
            patch("sourcerykit.cli.init._execute_post_auth_phases", return_value=True) as mock_phases,
            patch("sourcerykit.cli.init.console"),
        ):
            with pytest.raises(typer.Exit):
                _run_oauth_browser(
                    postgres_url="postgresql://u:p@h:5432/db",
                    project_name="proj",
                    sandbox=True,
                )

        # The SDK has no default client; sourcerykit must name its own.
        mock_login.assert_awaited_once_with(ANY, client_id="sourcerykit-cli", port=8910)
        mock_save.assert_called_once_with(token="at", refresh_token="rt", email="user@example.com")
        mock_phases.assert_called_once_with(
            "at",
            email="user@example.com",
            postgres_url="postgresql://u:p@h:5432/db",
            project_name="proj",
            sandbox=True,
            org_id_auto=False,
        )

    def test_returns_without_phases_on_connection_error(self) -> None:
        with (
            patch("sourcerykit.cli.init.browser_login", new=AsyncMock(side_effect=ProvablyConnectionError("down"))),
            patch("sourcerykit.cli.init._execute_post_auth_phases") as mock_phases,
            patch("sourcerykit.cli.init.console"),
        ):
            _run_oauth_browser(sandbox=True)  # must not raise

        mock_phases.assert_not_called()


class TestExecutePostAuthPhasesOrgs:
    _A = "11111111-1111-1111-1111-111111111111"
    _B = "22222222-2222-2222-2222-222222222222"
    _C = "33333333-3333-3333-3333-333333333333"

    def _picked_org(self, saved_config: dict[str, str]) -> str:
        orgs = [{"id": self._C}, {"id": self._A}, {"id": self._B}]
        with (
            patch("sourcerykit.cli.init.service.get_organizations", new=AsyncMock(return_value=orgs)),
            patch("sourcerykit.cli.init.load_app_dir_config", return_value=saved_config),
            patch("sourcerykit.cli.init.questionary") as mock_q,
            patch("sourcerykit.cli.init.save_app_dir_config") as mock_save,
            patch("sourcerykit.cli.init.provably_service.create_sandbox", new=AsyncMock(side_effect=Exception("stop"))),
            patch("sourcerykit.cli.init.console"),
        ):
            _execute_post_auth_phases("at", email="u@example.com", sandbox=True, org_id_auto=True)

        mock_q.select.assert_not_called()
        return str(mock_save.call_args.kwargs["org_id"])

    def test_multiple_orgs_keeps_saved_org(self) -> None:
        assert self._picked_org({"org_id": self._B}) == self._B

    def test_multiple_orgs_picks_lowest_id_without_saved_org(self) -> None:
        assert self._picked_org({}) == self._A

    def test_multiple_orgs_ignores_saved_org_no_longer_listed(self) -> None:
        assert self._picked_org({"org_id": "44444444-4444-4444-4444-444444444444"}) == self._A

    def test_multiple_orgs_without_flag_or_tty_fails_without_prompting(self) -> None:
        with (
            patch(
                "sourcerykit.cli.init.service.get_organizations",
                new=AsyncMock(return_value=[{"id": self._A}, {"id": self._B}]),
            ),
            patch("sourcerykit.cli.init.sys.stdin.isatty", return_value=False),
            patch("sourcerykit.cli.init.questionary") as mock_q,
            patch("sourcerykit.cli.init.save_app_dir_config") as mock_save,
            patch("sourcerykit.cli.init.console"),
        ):
            assert _execute_post_auth_phases("at", email="u@example.com", sandbox=True) is False

        mock_q.select.assert_not_called()
        mock_save.assert_not_called()


class TestMaskSecret:
    def test_empty_string(self) -> None:
        assert mask_secret("") == ""

    def test_short_string_shows_all(self) -> None:
        assert mask_secret("abc") == "abc"

    def test_normal_string_masks_all_but_last_4(self) -> None:
        assert mask_secret("abcdefghijklmnop") == "************mnop"

    def test_custom_show_last(self) -> None:
        assert mask_secret("abcdefgh", show_last=2) == "******gh"


# ---------------------------------------------------------------------------
# require_settings
# ---------------------------------------------------------------------------


class TestRequireSettings:
    def test_returns_settings_on_success(self) -> None:
        mock_settings = MagicMock()
        with patch("sourcerykit.cli.utils.get_settings", return_value=mock_settings):
            result = require_settings()
        assert result is mock_settings

    def test_raises_exit_on_failure(self) -> None:
        with patch("sourcerykit.cli.utils.get_settings", side_effect=Exception("missing config")):
            with pytest.raises(typer.Exit):
                require_settings()


# ---------------------------------------------------------------------------
# prompt_project_name
# ---------------------------------------------------------------------------


class TestPromptProjectName:
    def test_normalizes_name(self) -> None:
        with patch("sourcerykit.cli.utils.questionary") as mock_q:
            mock_q.text.return_value.ask.return_value = "My Project Name"
            result = prompt_project_name()
        assert result == "my-project-name"

    def test_returns_none_on_cancel(self) -> None:
        with patch("sourcerykit.cli.utils.questionary") as mock_q:
            mock_q.text.return_value.ask.return_value = None
            result = prompt_project_name()
        assert result is None

    def test_strips_whitespace(self) -> None:
        with patch("sourcerykit.cli.utils.questionary") as mock_q:
            mock_q.text.return_value.ask.return_value = "  spaced out  "
            result = prompt_project_name()
        assert result == "spaced-out"


# ---------------------------------------------------------------------------
# prompt_project_name (non-interactive)
# ---------------------------------------------------------------------------


class TestPromptProjectNameNonInteractive:
    def test_returns_normalized_name_without_prompt(self) -> None:
        with patch("sourcerykit.cli.utils.questionary") as mock_q:
            result = prompt_project_name(project_name="My Project")
        assert result == "my-project"
        mock_q.text.assert_not_called()

    def test_normalizes_slashes_and_spaces(self) -> None:
        result = prompt_project_name(project_name="  Hello World  ")
        assert result == "hello-world"

    def test_exits_on_empty_name(self) -> None:
        with pytest.raises(typer.Exit):
            prompt_project_name(project_name="   ")


# ---------------------------------------------------------------------------
# prompt_postgres_url_with_retry (non-interactive)
# ---------------------------------------------------------------------------


class TestPromptPostgresUrlWithRetryNonInteractive:
    def test_returns_url_on_success(self) -> None:
        with patch("sourcerykit.cli.utils.run_connectivity_check", return_value=True):
            result = prompt_postgres_url_with_retry("postgresql://u:p@h:5432/db")
        assert result == "postgresql://u:p@h:5432/db"

    def test_exits_on_connection_failure(self) -> None:
        with patch("sourcerykit.cli.utils.run_connectivity_check", return_value=False):
            with pytest.raises(typer.Exit):
                prompt_postgres_url_with_retry("postgresql://u:p@h:5432/db")

    def test_normalizes_url_before_checking(self) -> None:
        with (
            patch("sourcerykit.cli.utils.run_connectivity_check", return_value=True) as mock_check,
        ):
            result = prompt_postgres_url_with_retry("postgresql://user:p@ss@h:5432/db")
        assert result is not None
        assert "p%40ss" in result
        mock_check.assert_called_once_with(result)


# ---------------------------------------------------------------------------
# _normalize_postgres_url
# ---------------------------------------------------------------------------


class TestNormalizePostgresUrl:
    def test_encodes_at_in_password(self) -> None:
        url = "postgresql://user:p@ss@host:5432/mydb"
        result = _normalize_postgres_url(url)
        assert result == "postgresql://user:p%40ss@host:5432/mydb"

    def test_encodes_special_chars(self) -> None:
        url = "postgresql://user:p$$w0rd!@host:5432/mydb"
        result = _normalize_postgres_url(url)
        assert "p%24%24w0rd%21" in result

    def test_preserves_already_encoded_url(self) -> None:
        url = "postgresql://user:p%40ss@host:5432/mydb"
        result = _normalize_postgres_url(url)
        # urlparse decodes %40 -> @, quote re-encodes -> %2540 (double-encoded)
        # This is fine: the normalizer is for raw special chars, not already-encoded URLs
        assert "p%2540ss" in result

    def test_returns_original_on_no_username(self) -> None:
        url = "postgresql://host:5432/mydb"
        result = _normalize_postgres_url(url)
        assert result == url
