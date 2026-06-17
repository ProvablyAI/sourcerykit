"""Tests for sourcerykit.cli.main — helper functions."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from sourcerykit.cli.main import (
    _ask_postgres_url,
    _run_connectivity_check,
    _run_login,
    _run_register,
    _save_to_env,
)
from sourcerykit.provably._errors import ProvablyConnectionError, ProvablyUnauthorizedError

_VALID_API_KEY = "test-api-key"
_VALID_ORG_ID = str(uuid.uuid4())
_VALID_POSTGRES_URL = "postgresql://user:pass@1.2.3.4:5432/mydb"


# ---------------------------------------------------------------------------
# _ask_postgres_url
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
        with patch("sourcerykit.cli.main.questionary") as mock_q:
            mock_q.prompt.return_value = answers
            result = _ask_postgres_url()

        assert result == "postgresql://alice:s3cr3t@1.2.3.4:5432/mydb"

    def test_url_encodes_special_chars_in_password(self) -> None:
        answers = {
            "host": "db.example.com",
            "port": "5432",
            "username": "user",
            "password": "p@$$w0rd!",
            "database": "mydb",
        }
        with patch("sourcerykit.cli.main.questionary") as mock_q:
            mock_q.prompt.return_value = answers
            result = _ask_postgres_url()

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
        with patch("sourcerykit.cli.main.questionary") as mock_q:
            mock_q.prompt.return_value = answers
            result = _ask_postgres_url()

        assert "user%40domain" in result

    def test_returns_empty_string_when_questionary_cancelled(self) -> None:
        with patch("sourcerykit.cli.main.questionary") as mock_q:
            mock_q.prompt.return_value = None
            result = _ask_postgres_url()

        assert result == ""


# ---------------------------------------------------------------------------
# _run_connectivity_check
# ---------------------------------------------------------------------------


class TestRunConnectivityCheck:
    def test_returns_true_on_valid_credentials_and_connected_db(self) -> None:
        with patch("sourcerykit.cli.main.psycopg") as mock_psycopg:
            mock_psycopg.connect.return_value.__enter__ = MagicMock(return_value=None)
            mock_psycopg.connect.return_value.__exit__ = MagicMock(return_value=False)
            result = _run_connectivity_check(_VALID_API_KEY, _VALID_ORG_ID, _VALID_POSTGRES_URL)

        assert result is True

    def test_returns_false_on_invalid_org_id_format(self) -> None:
        result = _run_connectivity_check(_VALID_API_KEY, "not-a-uuid", _VALID_POSTGRES_URL)
        assert result is False

    def test_returns_false_on_psycopg_connect_failure(self) -> None:
        with patch("sourcerykit.cli.main.psycopg") as mock_psycopg:
            mock_psycopg.connect.side_effect = Exception("Connection refused")
            result = _run_connectivity_check(_VALID_API_KEY, _VALID_ORG_ID, _VALID_POSTGRES_URL)

        assert result is False

    def test_returns_false_on_missing_api_key(self) -> None:
        result = _run_connectivity_check("", _VALID_ORG_ID, _VALID_POSTGRES_URL)
        assert result is False


# ---------------------------------------------------------------------------
# _save_to_env
# ---------------------------------------------------------------------------


class TestSaveToEnv:
    def test_calls_set_key_with_correct_args(self) -> None:
        mock_text = MagicMock()
        mock_text.ask.return_value = ".env"

        with (
            patch("sourcerykit.cli.main.questionary") as mock_q,
            patch("sourcerykit.cli.main.Path") as mock_path,
            patch("sourcerykit.cli.main.set_key") as mock_set_key,
        ):
            mock_q.text.return_value = mock_text
            mock_path.return_value.touch = MagicMock()

            _save_to_env("my-api-key", "my-org-id", "postgresql://u:p@h:5432/db")

        assert mock_set_key.call_count == 3
        mock_set_key.assert_any_call(".env", "PROVABLY_API_KEY", "my-api-key")
        mock_set_key.assert_any_call(".env", "SOURCERYKIT_ORG_ID", "my-org-id")
        mock_set_key.assert_any_call(".env", "SOURCERYKIT_POSTGRES_URL", "postgresql://u:p@h:5432/db")

    def test_skips_saving_when_path_is_empty(self) -> None:
        mock_text = MagicMock()
        mock_text.ask.return_value = None

        with (
            patch("sourcerykit.cli.main.questionary") as mock_q,
            patch("sourcerykit.cli.main.set_key") as mock_set_key,
        ):
            mock_q.text.return_value = mock_text
            _save_to_env("key", "org", "url")

        mock_set_key.assert_not_called()


# ---------------------------------------------------------------------------
# _run_register
# ---------------------------------------------------------------------------


class TestRunRegister:
    def test_returns_email_on_successful_registration(self) -> None:
        with (
            patch("sourcerykit.cli.main.questionary") as mock_q,
            patch("sourcerykit.cli.main.service") as mock_service,
        ):
            mock_q.prompt.return_value = {"email": "new@example.com", "password": "pw"}
            mock_q.press_any_key_to_continue.return_value.ask = MagicMock(return_value=None)
            mock_service.create_account = AsyncMock(return_value=None)

            result = _run_register()

        assert result == "new@example.com"

    def test_returns_empty_string_on_connection_error(self) -> None:
        with (
            patch("sourcerykit.cli.main.questionary") as mock_q,
            patch("sourcerykit.cli.main.service") as mock_service,
        ):
            mock_q.prompt.return_value = {"email": "new@example.com", "password": "pw"}
            mock_service.create_account = AsyncMock(side_effect=ProvablyConnectionError("Network unreachable"))

            result = _run_register()

        assert result == ""

    def test_returns_empty_string_when_inputs_cancelled(self) -> None:
        with patch("sourcerykit.cli.main.questionary") as mock_q:
            mock_q.prompt.return_value = None

            result = _run_register()

        assert result == ""


# ---------------------------------------------------------------------------
# _run_login
# ---------------------------------------------------------------------------


class TestRunLogin:
    def test_calls_execute_post_auth_phases_on_success(self) -> None:
        with (
            patch("sourcerykit.cli.main.questionary") as mock_q,
            patch("sourcerykit.cli.main.service") as mock_service,
            patch("sourcerykit.cli.main._execute_post_auth_phases") as mock_phases,
        ):
            mock_q.text.return_value.ask.return_value = "user@example.com"
            mock_q.password.return_value.ask.return_value = "secret"
            mock_service.login = AsyncMock(return_value={"token": "jwt-abc"})

            _run_login()

        mock_phases.assert_called_once_with("jwt-abc")

    def test_handles_unauthorized_error_without_crash(self) -> None:
        with (
            patch("sourcerykit.cli.main.questionary") as mock_q,
            patch("sourcerykit.cli.main.service") as mock_service,
            patch("sourcerykit.cli.main._execute_post_auth_phases") as mock_phases,
        ):
            mock_q.text.return_value.ask.return_value = "user@example.com"
            mock_q.password.return_value.ask.return_value = "wrong"
            mock_service.login = AsyncMock(side_effect=ProvablyUnauthorizedError("Bad creds"))

            _run_login()  # must not raise

        mock_phases.assert_not_called()

    def test_handles_connection_error_without_crash(self) -> None:
        with (
            patch("sourcerykit.cli.main.questionary") as mock_q,
            patch("sourcerykit.cli.main.service") as mock_service,
            patch("sourcerykit.cli.main._execute_post_auth_phases") as mock_phases,
        ):
            mock_q.text.return_value.ask.return_value = "user@example.com"
            mock_q.password.return_value.ask.return_value = "pass"
            mock_service.login = AsyncMock(side_effect=ProvablyConnectionError("Unreachable"))

            _run_login()  # must not raise

        mock_phases.assert_not_called()

    def test_returns_early_when_token_missing_from_response(self) -> None:
        with (
            patch("sourcerykit.cli.main.questionary") as mock_q,
            patch("sourcerykit.cli.main.service") as mock_service,
            patch("sourcerykit.cli.main._execute_post_auth_phases") as mock_phases,
        ):
            mock_q.text.return_value.ask.return_value = "user@example.com"
            mock_q.password.return_value.ask.return_value = "pass"
            mock_service.login = AsyncMock(return_value={})  # no token key

            _run_login()

        mock_phases.assert_not_called()

    def test_prefill_email_passed_to_text_prompt(self) -> None:
        with (
            patch("sourcerykit.cli.main.questionary") as mock_q,
            patch("sourcerykit.cli.main.service") as mock_service,
            patch("sourcerykit.cli.main._execute_post_auth_phases"),
        ):
            mock_q.text.return_value.ask.return_value = None  # user cancels
            mock_service.login = AsyncMock(return_value={"token": "t"})

            _run_login(prefill_email="pre@example.com")

            _, kwargs = mock_q.text.call_args
            assert kwargs.get("default") == "pre@example.com"
