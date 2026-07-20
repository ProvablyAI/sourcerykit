"""Tests for sourcerykit.cli.upgrade."""

from unittest.mock import MagicMock, patch

from sourcerykit.cli.upgrade import _get_latest_pypi_version, _run_migrations, run_upgrade


class TestGetLatestPypiVersion:
    def test_returns_version_on_success(self) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"info": {"version": "2.0.0"}}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("sourcerykit.cli.upgrade.urlopen", return_value=mock_resp):
            assert _get_latest_pypi_version() == "2.0.0"

    def test_returns_none_on_network_error(self) -> None:
        from urllib.error import URLError

        with patch("sourcerykit.cli.upgrade.urlopen", side_effect=URLError("timeout")):
            assert _get_latest_pypi_version() is None

    def test_returns_none_on_bad_json(self) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"info": {}}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("sourcerykit.cli.upgrade.urlopen", return_value=mock_resp):
            assert _get_latest_pypi_version() is None


class TestRunMigrations:
    def test_returns_true_on_success(self) -> None:
        mock_alembic_dir = MagicMock(is_dir=MagicMock(return_value=True))
        mock_parent = MagicMock(__truediv__=MagicMock(return_value=mock_alembic_dir))
        mock_parents = MagicMock(__getitem__=MagicMock(return_value=mock_parent))
        mock_resolved = MagicMock(parents=mock_parents)
        mock_path_instance = MagicMock(resolve=MagicMock(return_value=mock_resolved))
        with (
            patch("sourcerykit.cli.upgrade.Path", return_value=mock_path_instance),
            patch("alembic.config.Config"),
            patch("alembic.command.upgrade") as mock_upgrade,
        ):
            assert _run_migrations() is True
            mock_upgrade.assert_called_once()

    def test_returns_false_when_alembic_dir_missing(self) -> None:
        mock_alembic_dir = MagicMock(is_dir=MagicMock(return_value=False))
        mock_parent = MagicMock(__truediv__=MagicMock(return_value=mock_alembic_dir))
        mock_parents = MagicMock(__getitem__=MagicMock(return_value=mock_parent))
        mock_resolved = MagicMock(parents=mock_parents)
        mock_path_instance = MagicMock(resolve=MagicMock(return_value=mock_resolved))
        with patch("sourcerykit.cli.upgrade.Path", return_value=mock_path_instance):
            assert _run_migrations() is False

    def test_returns_false_on_upgrade_error(self) -> None:
        mock_alembic_dir = MagicMock(is_dir=MagicMock(return_value=True))
        mock_parent = MagicMock(__truediv__=MagicMock(return_value=mock_alembic_dir))
        mock_parents = MagicMock(__getitem__=MagicMock(return_value=mock_parent))
        mock_resolved = MagicMock(parents=mock_parents)
        mock_path_instance = MagicMock(resolve=MagicMock(return_value=mock_resolved))
        with (
            patch("sourcerykit.cli.upgrade.Path", return_value=mock_path_instance),
            patch("alembic.config.Config"),
            patch("alembic.command.upgrade", side_effect=RuntimeError("migration failed")),
        ):
            assert _run_migrations() is False


class TestRunUpgrade:
    def test_already_on_latest(self) -> None:
        with (
            patch("sourcerykit.cli.upgrade.importlib.metadata.version", return_value="1.0.0"),
            patch("sourcerykit.cli.upgrade._get_latest_pypi_version", return_value="1.0.0"),
            patch("sourcerykit.cli.upgrade._run_migrations", return_value=True),
            patch("sourcerykit.cli.upgrade.console") as mock_console,
        ):
            run_upgrade()
        assert any("Already on latest" in str(c) for c in mock_console.print.call_args_list)

    def test_new_version_user_confirms(self) -> None:
        with (
            patch("sourcerykit.cli.upgrade.importlib.metadata.version", return_value="1.0.0"),
            patch("sourcerykit.cli.upgrade._get_latest_pypi_version", return_value="2.0.0"),
            patch("sourcerykit.cli.upgrade._run_migrations", return_value=True),
            patch("sourcerykit.cli.upgrade.questionary.confirm") as mock_confirm,
            patch("sourcerykit.cli.upgrade.subprocess.run", return_value=MagicMock(returncode=0)),
            patch("sourcerykit.cli.upgrade.console"),
        ):
            mock_confirm.return_value.ask.return_value = True
            run_upgrade()
        mock_confirm.assert_called_once()

    def test_new_version_user_declines(self) -> None:
        with (
            patch("sourcerykit.cli.upgrade.importlib.metadata.version", return_value="1.0.0"),
            patch("sourcerykit.cli.upgrade._get_latest_pypi_version", return_value="2.0.0"),
            patch("sourcerykit.cli.upgrade._run_migrations", return_value=True),
            patch("sourcerykit.cli.upgrade.questionary.confirm") as mock_confirm,
            patch("sourcerykit.cli.upgrade.console") as mock_console,
        ):
            mock_confirm.return_value.ask.return_value = False
            run_upgrade()
        assert any("Skipping" in str(c) for c in mock_console.print.call_args_list)

    def test_pypi_unreachable(self) -> None:
        with (
            patch("sourcerykit.cli.upgrade.importlib.metadata.version", return_value="1.0.0"),
            patch("sourcerykit.cli.upgrade._get_latest_pypi_version", return_value=None),
            patch("sourcerykit.cli.upgrade._run_migrations", return_value=True),
            patch("sourcerykit.cli.upgrade.console") as mock_console,
        ):
            run_upgrade()
        assert any("could not check PyPI" in str(c) for c in mock_console.print.call_args_list)

    def test_pip_upgrade_fails_skips_migrations(self) -> None:
        with (
            patch("sourcerykit.cli.upgrade.importlib.metadata.version", return_value="1.0.0"),
            patch("sourcerykit.cli.upgrade._get_latest_pypi_version", return_value="2.0.0"),
            patch("sourcerykit.cli.upgrade._run_migrations") as mock_mig,
            patch("sourcerykit.cli.upgrade.questionary.confirm") as mock_confirm,
            patch("sourcerykit.cli.upgrade.subprocess.run", return_value=MagicMock(returncode=1, stderr=b"err")),
            patch("sourcerykit.cli.upgrade.console"),
        ):
            mock_confirm.return_value.ask.return_value = True
            run_upgrade()
        mock_mig.assert_not_called()

    def test_migrations_fail_prints_error(self) -> None:
        with (
            patch("sourcerykit.cli.upgrade.importlib.metadata.version", return_value="1.0.0"),
            patch("sourcerykit.cli.upgrade._get_latest_pypi_version", return_value="1.0.0"),
            patch("sourcerykit.cli.upgrade._run_migrations", return_value=False),
            patch("sourcerykit.cli.upgrade.console") as mock_console,
        ):
            run_upgrade()
        assert any("FAILED" in str(c) for c in mock_console.print.call_args_list)
