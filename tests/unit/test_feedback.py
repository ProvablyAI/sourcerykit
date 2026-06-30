"""Tests for sourcerykit.cli.feedback."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import typer

from sourcerykit.cli.feedback import send_feedback


class TestSendFeedback:
    def test_success_description_only(self) -> None:
        with (
            patch("sourcerykit.cli.feedback.require_settings"),
            patch("sourcerykit.cli.feedback.questionary") as mock_q,
            patch("sourcerykit.cli.feedback.service") as mock_svc,
            patch("sourcerykit.cli.feedback.console"),
        ):
            mock_q.text.return_value.ask.return_value = "Great product!"
            mock_q.confirm.return_value.ask.return_value = False
            mock_svc.create_feedback = AsyncMock()

            send_feedback()

        mock_svc.create_feedback.assert_called_once_with("Great product!", b"")

    def test_success_with_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "log.txt"
        test_file.write_text("some log content")

        with (
            patch("sourcerykit.cli.feedback.require_settings"),
            patch("sourcerykit.cli.feedback.questionary") as mock_q,
            patch("sourcerykit.cli.feedback.service") as mock_svc,
            patch("sourcerykit.cli.feedback.console"),
        ):
            mock_q.text.return_value.ask.return_value = "Bug report"
            mock_q.confirm.return_value.ask.return_value = True
            mock_q.text.return_value.ask.side_effect = ["Bug report", str(test_file)]
            mock_svc.create_feedback = AsyncMock()

            send_feedback()

        mock_svc.create_feedback.assert_called_once()
        args = mock_svc.create_feedback.call_args[0]
        assert args[0] == "Bug report"
        assert len(args[1]) > 0  # file bytes

    def test_empty_description_exits(self) -> None:
        with (
            patch("sourcerykit.cli.feedback.require_settings"),
            patch("sourcerykit.cli.feedback.questionary") as mock_q,
            patch("sourcerykit.cli.feedback.console"),
        ):
            mock_q.text.return_value.ask.return_value = ""

            with pytest.raises(typer.Exit) as exc_info:
                send_feedback()
            assert exc_info.value.exit_code == 1

    def test_file_not_found_exits(self) -> None:
        with (
            patch("sourcerykit.cli.feedback.require_settings"),
            patch("sourcerykit.cli.feedback.questionary") as mock_q,
            patch("sourcerykit.cli.feedback.console"),
        ):
            mock_q.text.return_value.ask.side_effect = ["Bug report", "/nonexistent/file.txt"]
            mock_q.confirm.return_value.ask.return_value = True

            with pytest.raises(typer.Exit) as exc_info:
                send_feedback()
            assert exc_info.value.exit_code == 1

    def test_api_failure_exits(self) -> None:
        with (
            patch("sourcerykit.cli.feedback.require_settings"),
            patch("sourcerykit.cli.feedback.questionary") as mock_q,
            patch("sourcerykit.cli.feedback.service") as mock_svc,
            patch("sourcerykit.cli.feedback.console"),
        ):
            mock_q.text.return_value.ask.return_value = "Feedback"
            mock_q.confirm.return_value.ask.return_value = False
            mock_svc.create_feedback = AsyncMock(side_effect=Exception("API down"))

            with pytest.raises(typer.Exit) as exc_info:
                send_feedback()
            assert exc_info.value.exit_code == 1
