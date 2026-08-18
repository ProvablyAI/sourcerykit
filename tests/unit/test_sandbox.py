"""Tests for sourcerykit.cli.sandbox — CLI sandbox commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer

from sourcerykit.cli.sandbox import create, delete, status

# ---------------------------------------------------------------------------
# sandbox create
# ---------------------------------------------------------------------------


class TestSandboxCreate:
    def test_creates_sandbox_and_saves_uri(self) -> None:
        mock_settings = MagicMock()
        mock_settings.org_id = "org-123"
        with (
            patch("sourcerykit.cli.sandbox.require_settings", return_value=mock_settings),
            patch("sourcerykit.cli.sandbox.service") as mock_svc,
            patch("sourcerykit.cli.sandbox.save_local_env") as mock_save,
            patch("sourcerykit.cli.sandbox.console"),
        ):
            mock_svc.create_sandbox = AsyncMock(return_value="postgresql://sandbox/db")

            create()

        mock_svc.create_sandbox.assert_awaited_once()
        mock_save.assert_called_once_with(SOURCERYKIT_POSTGRES_URL="postgresql://sandbox/db")

    def test_exits_when_no_org_id(self) -> None:
        mock_settings = MagicMock()
        mock_settings.org_id = None
        with (
            patch("sourcerykit.cli.sandbox.require_settings", return_value=mock_settings),
            patch("sourcerykit.cli.sandbox.console"),
        ):
            with pytest.raises(typer.Exit):
                create()

    def test_api_error_propagates(self) -> None:
        mock_settings = MagicMock()
        mock_settings.org_id = "org-123"
        with (
            patch("sourcerykit.cli.sandbox.require_settings", return_value=mock_settings),
            patch("sourcerykit.cli.sandbox.service") as mock_svc,
            patch("sourcerykit.cli.sandbox.console"),
        ):
            mock_svc.create_sandbox = AsyncMock(side_effect=RuntimeError("API down"))

            with pytest.raises(RuntimeError, match="API down"):
                create()


# ---------------------------------------------------------------------------
# sandbox status
# ---------------------------------------------------------------------------


class TestSandboxStatus:
    def test_active_sandbox(self) -> None:
        mock_settings = MagicMock()
        mock_settings.postgres_url = "postgresql://sandbox/db"
        sandbox_data = {"status": "active", "connection_uri": "postgresql://sandbox/db"}
        with (
            patch("sourcerykit.cli.sandbox.require_settings", return_value=mock_settings),
            patch("sourcerykit.cli.sandbox.service") as mock_svc,
            patch("sourcerykit.cli.sandbox.console") as mock_console,
        ):
            mock_svc.get_sandbox_status = AsyncMock(return_value=(sandbox_data, True))

            status()

        mock_console.print.assert_any_call("  status          = active")

    def test_no_sandbox_found(self) -> None:
        mock_settings = MagicMock()
        mock_settings.postgres_url = "postgresql://host/db"
        with (
            patch("sourcerykit.cli.sandbox.require_settings", return_value=mock_settings),
            patch("sourcerykit.cli.sandbox.service") as mock_svc,
            patch("sourcerykit.cli.sandbox.console") as mock_console,
        ):
            mock_svc.get_sandbox_status = AsyncMock(return_value=(None, False))

            status()

        mock_console.print.assert_any_call("[yellow]No sandbox found.[/yellow]")

    def test_personal_db_not_in_use(self) -> None:
        mock_settings = MagicMock()
        mock_settings.postgres_url = "postgresql://myhost/db"
        sandbox_data = {"status": "active", "connection_uri": "postgresql://sandbox/db"}
        with (
            patch("sourcerykit.cli.sandbox.require_settings", return_value=mock_settings),
            patch("sourcerykit.cli.sandbox.service") as mock_svc,
            patch("sourcerykit.cli.sandbox.console") as mock_console,
        ):
            mock_svc.get_sandbox_status = AsyncMock(return_value=(sandbox_data, False))

            status()

        mock_console.print.assert_any_call("  in_use          = False")


# ---------------------------------------------------------------------------
# sandbox delete
# ---------------------------------------------------------------------------


class TestSandboxDelete:
    def test_deletes_with_yes_flag(self) -> None:
        mock_settings = MagicMock()
        with (
            patch("sourcerykit.cli.sandbox.require_settings", return_value=mock_settings),
            patch("sourcerykit.cli.sandbox.service") as mock_svc,
            patch("sourcerykit.cli.sandbox.unset_key") as mock_unset,
            patch("sourcerykit.cli.sandbox.console"),
        ):
            mock_svc.delete_sandbox = AsyncMock()

            delete(yes=True)

        mock_svc.delete_sandbox.assert_awaited_once()
        mock_unset.assert_called_once()

    def test_deletes_after_confirmation(self) -> None:
        mock_settings = MagicMock()
        with (
            patch("sourcerykit.cli.sandbox.require_settings", return_value=mock_settings),
            patch("sourcerykit.cli.sandbox.questionary") as mock_q,
            patch("sourcerykit.cli.sandbox.service") as mock_svc,
            patch("sourcerykit.cli.sandbox.unset_key"),
            patch("sourcerykit.cli.sandbox.console"),
        ):
            mock_q.confirm.return_value.ask.return_value = True
            mock_svc.delete_sandbox = AsyncMock()

            delete(yes=False)

        mock_svc.delete_sandbox.assert_awaited_once()

    def test_cancels_on_no(self) -> None:
        mock_settings = MagicMock()
        with (
            patch("sourcerykit.cli.sandbox.require_settings", return_value=mock_settings),
            patch("sourcerykit.cli.sandbox.questionary") as mock_q,
            patch("sourcerykit.cli.sandbox.service") as mock_svc,
            patch("sourcerykit.cli.sandbox.console"),
        ):
            mock_q.confirm.return_value.ask.return_value = False

            delete(yes=False)

        mock_svc.delete_sandbox.assert_not_called()

    def test_removes_postgres_url_from_env(self) -> None:
        mock_settings = MagicMock()
        with (
            patch("sourcerykit.cli.sandbox.require_settings", return_value=mock_settings),
            patch("sourcerykit.cli.sandbox.service") as mock_svc,
            patch("sourcerykit.cli.sandbox.unset_key") as mock_unset,
            patch("sourcerykit.cli.sandbox.console"),
        ):
            mock_svc.delete_sandbox = AsyncMock()

            delete(yes=True)

        mock_unset.assert_called_once()
        args = mock_unset.call_args[0]
        assert "SOURCERYKIT_POSTGRES_URL" in args
