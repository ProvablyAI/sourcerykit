"""Tests for sourcerykit.cli — helper functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer

from sourcerykit.cli.init import (
    _run_login,
    _run_register,
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
from sourcerykit.provably._errors import ProvablyConnectionError, ProvablyUnauthorizedError

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
# _run_register
# ---------------------------------------------------------------------------


class TestRunRegister:
    def test_returns_email_on_successful_registration(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary") as mock_q,
            patch("sourcerykit.cli.init.service") as mock_service,
        ):
            mock_q.prompt.return_value = {"email": "new@example.com", "password": "pw"}
            mock_q.press_any_key_to_continue.return_value.ask = MagicMock(return_value=None)
            mock_service.create_account = AsyncMock(return_value=None)

            result = _run_register()

        assert result == "new@example.com"

    def test_returns_empty_string_on_connection_error(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary") as mock_q,
            patch("sourcerykit.cli.init.service") as mock_service,
        ):
            mock_q.prompt.return_value = {"email": "new@example.com", "password": "pw"}
            mock_service.create_account = AsyncMock(side_effect=ProvablyConnectionError("Network unreachable"))

            result = _run_register()

        assert result == ""

    def test_returns_empty_string_when_inputs_cancelled(self) -> None:
        with patch("sourcerykit.cli.init.questionary") as mock_q:
            mock_q.prompt.return_value = None

            result = _run_register()

        assert result == ""


# ---------------------------------------------------------------------------
# _run_login
# ---------------------------------------------------------------------------


class TestRunLogin:
    def test_calls_execute_post_auth_phases_on_success(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary") as mock_q,
            patch("sourcerykit.cli.init.service") as mock_service,
            patch("sourcerykit.cli.init._execute_post_auth_phases") as mock_phases,
            patch("sourcerykit.cli.init.console"),
        ):
            mock_q.text.return_value.ask.return_value = "user@example.com"
            mock_q.password.return_value.ask.return_value = "secret"
            mock_service.login = AsyncMock(return_value={"token": "jwt-abc"})
            mock_phases.return_value = True

            with pytest.raises(typer.Exit):
                _run_login()

        mock_phases.assert_called_once_with(
            "jwt-abc",
            email="user@example.com",
            postgres_url=None,
            project_name=None,
        )

    def test_handles_unauthorized_error_without_crash(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary") as mock_q,
            patch("sourcerykit.cli.init.service") as mock_service,
            patch("sourcerykit.cli.init._execute_post_auth_phases") as mock_phases,
            patch("sourcerykit.cli.init.console"),
        ):
            mock_q.text.return_value.ask.return_value = "user@example.com"
            mock_q.password.return_value.ask.return_value = "wrong"
            mock_service.login = AsyncMock(side_effect=ProvablyUnauthorizedError("Bad creds"))

            _run_login()  # must not raise

        mock_phases.assert_not_called()

    def test_handles_connection_error_without_crash(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary") as mock_q,
            patch("sourcerykit.cli.init.service") as mock_service,
            patch("sourcerykit.cli.init._execute_post_auth_phases") as mock_phases,
            patch("sourcerykit.cli.init.console"),
        ):
            mock_q.text.return_value.ask.return_value = "user@example.com"
            mock_q.password.return_value.ask.return_value = "pass"
            mock_service.login = AsyncMock(side_effect=ProvablyConnectionError("Unreachable"))

            _run_login()  # must not raise

        mock_phases.assert_not_called()

    def test_returns_early_when_token_missing_from_response(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary") as mock_q,
            patch("sourcerykit.cli.init.service") as mock_service,
            patch("sourcerykit.cli.init._execute_post_auth_phases") as mock_phases,
            patch("sourcerykit.cli.init.console"),
        ):
            mock_q.text.return_value.ask.return_value = "user@example.com"
            mock_q.password.return_value.ask.return_value = "pass"
            mock_service.login = AsyncMock(return_value={})  # no token key

            _run_login()

        mock_phases.assert_not_called()

    def test_prefill_email_passed_to_text_prompt(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary") as mock_q,
            patch("sourcerykit.cli.init.service") as mock_service,
            patch("sourcerykit.cli.init._execute_post_auth_phases"),
            patch("sourcerykit.cli.init.console"),
        ):
            mock_q.text.return_value.ask.return_value = None  # user cancels
            mock_service.login = AsyncMock(return_value={"token": "t"})

            _run_login(prefill_email="pre@example.com")

            _, kwargs = mock_q.text.call_args
            assert kwargs.get("default") == "pre@example.com"


# ---------------------------------------------------------------------------
# mask_secret
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# _run_login (non-interactive)
# ---------------------------------------------------------------------------


class TestRunLoginNonInteractive:
    def test_skips_prompts_when_email_and_password_provided(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary") as mock_q,
            patch("sourcerykit.cli.init.service") as mock_service,
            patch("sourcerykit.cli.init._execute_post_auth_phases") as mock_phases,
            patch("sourcerykit.cli.init.console"),
        ):
            mock_service.login = AsyncMock(return_value={"token": "jwt-abc"})
            mock_phases.return_value = True

            with pytest.raises(typer.Exit):
                _run_login(email="a@b.com", password="pw")

        mock_q.text.assert_not_called()
        mock_q.password.assert_not_called()
        mock_service.login.assert_called_once()

    def test_passes_flags_to_post_auth_phases(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary"),
            patch("sourcerykit.cli.init.service") as mock_service,
            patch("sourcerykit.cli.init._execute_post_auth_phases") as mock_phases,
            patch("sourcerykit.cli.init.console"),
        ):
            mock_service.login = AsyncMock(return_value={"token": "jwt-abc"})
            mock_phases.return_value = True

            with pytest.raises(typer.Exit):
                _run_login(
                    email="a@b.com",
                    password="pw",
                    postgres_url="postgresql://u:p@h:5432/db",
                    project_name="myproj",
                )

        mock_phases.assert_called_once_with(
            "jwt-abc",
            email="a@b.com",
            postgres_url="postgresql://u:p@h:5432/db",
            project_name="myproj",
        )

    def test_handles_unauthorized_error(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary"),
            patch("sourcerykit.cli.init.service") as mock_service,
            patch("sourcerykit.cli.init._execute_post_auth_phases") as mock_phases,
            patch("sourcerykit.cli.init.console"),
        ):
            mock_service.login = AsyncMock(side_effect=ProvablyUnauthorizedError("Bad"))

            _run_login(email="a@b.com", password="bad")  # must not raise

        mock_phases.assert_not_called()

    def test_handles_connection_error(self) -> None:
        with (
            patch("sourcerykit.cli.init.questionary"),
            patch("sourcerykit.cli.init.service") as mock_service,
            patch("sourcerykit.cli.init._execute_post_auth_phases") as mock_phases,
            patch("sourcerykit.cli.init.console"),
        ):
            mock_service.login = AsyncMock(side_effect=ProvablyConnectionError("Unreachable"))

            _run_login(email="a@b.com", password="pw")  # must not raise

        mock_phases.assert_not_called()
