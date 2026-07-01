"""Tests for sourcerykit.cli.endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
import typer

from sourcerykit.cli.endpoints import add, list, remove
from sourcerykit.errors import SourceryKitTrustError


class TestEndpointsAdd:
    def test_add_valid_url(self) -> None:
        with (
            patch("sourcerykit.cli.endpoints.require_settings"),
            patch("sourcerykit.cli.endpoints.sanitize_and_extract_trusted_url", return_value="https://api.example.com"),
            patch("sourcerykit.cli.endpoints.service") as mock_svc,
            patch("sourcerykit.cli.endpoints.console"),
        ):
            mock_svc.insert_trusted_endpoint = AsyncMock()
            add("https://api.example.com", label=None)

        mock_svc.insert_trusted_endpoint.assert_called_once_with(url="https://api.example.com", display_label=None)

    def test_add_with_label(self) -> None:
        with (
            patch("sourcerykit.cli.endpoints.require_settings"),
            patch("sourcerykit.cli.endpoints.sanitize_and_extract_trusted_url", return_value="https://api.example.com"),
            patch("sourcerykit.cli.endpoints.service") as mock_svc,
            patch("sourcerykit.cli.endpoints.console"),
        ):
            mock_svc.insert_trusted_endpoint = AsyncMock()
            add("https://api.example.com", label="My API")

        mock_svc.insert_trusted_endpoint.assert_called_once_with(url="https://api.example.com", display_label="My API")

    def test_add_invalid_url_exits_with_error(self) -> None:
        with (
            patch("sourcerykit.cli.endpoints.require_settings"),
            patch(
                "sourcerykit.cli.endpoints.sanitize_and_extract_trusted_url",
                side_effect=SourceryKitTrustError("bad url"),
            ),
            patch("sourcerykit.cli.endpoints.console"),
        ):
            with pytest.raises(typer.Exit) as exc_info:
                add("not-a-url")
            assert exc_info.value.exit_code == 1


class TestEndpointsList:
    def test_list_shows_table(self) -> None:
        rows = [
            {"url": "https://a.com", "label": "A", "policy_version": "v1", "created_by": "user1"},
            {"url": "https://b.com", "label": "B", "policy_version": "v1", "created_by": "user2"},
        ]
        with (
            patch("sourcerykit.cli.endpoints.require_settings"),
            patch("sourcerykit.cli.endpoints.service") as mock_svc,
            patch("sourcerykit.cli.endpoints.console"),
        ):
            mock_svc.list_all_trusted_endpoints_detailed = AsyncMock(return_value=rows)
            list()

    def test_list_empty(self) -> None:
        with (
            patch("sourcerykit.cli.endpoints.require_settings"),
            patch("sourcerykit.cli.endpoints.service") as mock_svc,
            patch("sourcerykit.cli.endpoints.console"),
        ):
            mock_svc.list_all_trusted_endpoints_detailed = AsyncMock(return_value=[])
            list()  # must not raise


class TestEndpointsRemove:
    def test_remove_confirmed(self) -> None:
        with (
            patch("sourcerykit.cli.endpoints.require_settings"),
            patch("sourcerykit.cli.endpoints.questionary") as mock_q,
            patch("sourcerykit.cli.endpoints.service") as mock_svc,
            patch("sourcerykit.cli.endpoints.console"),
        ):
            mock_q.confirm.return_value.ask.return_value = True
            mock_svc.remove_trusted_endpoint = AsyncMock()
            remove("https://bad.com")

        mock_svc.remove_trusted_endpoint.assert_called_once_with(url="https://bad.com")

    def test_remove_cancelled(self) -> None:
        with (
            patch("sourcerykit.cli.endpoints.require_settings"),
            patch("sourcerykit.cli.endpoints.questionary") as mock_q,
            patch("sourcerykit.cli.endpoints.service") as mock_svc,
            patch("sourcerykit.cli.endpoints.console"),
        ):
            mock_q.confirm.return_value.ask.return_value = False
            mock_svc.remove_trusted_endpoint = AsyncMock()
            remove("https://bad.com", yes=False)

        mock_svc.remove_trusted_endpoint.assert_not_called()
