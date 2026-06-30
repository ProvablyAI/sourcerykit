"""Tests for sourcerykit.intercept._loader.load_latest_intercept_payload."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcerykit.errors import SourceryKitStorageError
from sourcerykit.intercept._loader import load_latest_intercept_payload


def _make_engine(row: Any = None, raise_exc: Exception | None = None) -> MagicMock:
    """Build a mock async engine whose connect() context yields a result."""
    mock_result = MagicMock()
    mock_result.fetchone.return_value = row

    mock_conn = AsyncMock()
    if raise_exc:
        mock_conn.execute = AsyncMock(side_effect=raise_exc)
    else:
        mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_ctx
    return mock_engine


def _make_row(request_payload: str | None = None, raw_response: str | None = None) -> MagicMock:
    row = MagicMock()
    row.request_payload = request_payload
    row.raw_response = raw_response
    return row


class TestLoadLatestInterceptPayload:
    async def test_returns_empty_dict_and_none_when_no_row(self) -> None:
        engine = _make_engine(row=None)
        with patch("sourcerykit.intercept._loader.get_engine", return_value=engine):
            req, resp = await load_latest_intercept_payload("agent-1", "action-a")
        assert req == {}
        assert resp is None

    async def test_returns_parsed_request_and_response(self) -> None:
        row = _make_row(
            request_payload=json.dumps({"method": "POST", "url": "https://api.example.com"}),
            raw_response=json.dumps({"status": "ok"}),
        )
        engine = _make_engine(row=row)
        with patch("sourcerykit.intercept._loader.get_engine", return_value=engine):
            req, resp = await load_latest_intercept_payload("agent-1", "action-a")
        assert req == {"method": "POST", "url": "https://api.example.com"}
        assert resp == {"status": "ok"}

    async def test_returns_empty_request_when_payload_is_none(self) -> None:
        row = _make_row(request_payload=None, raw_response=None)
        engine = _make_engine(row=row)
        with patch("sourcerykit.intercept._loader.get_engine", return_value=engine):
            req, resp = await load_latest_intercept_payload("agent-1", "action-a")
        assert req == {}
        assert resp is None

    async def test_raises_storage_error_on_corrupt_request_payload(self) -> None:
        row = _make_row(request_payload="not-valid-json", raw_response=None)
        engine = _make_engine(row=row)
        with patch("sourcerykit.intercept._loader.get_engine", return_value=engine):
            with pytest.raises(SourceryKitStorageError, match="request_payload"):
                await load_latest_intercept_payload("agent-1", "action-a")

    async def test_raises_storage_error_on_corrupt_raw_response(self) -> None:
        row = _make_row(request_payload=json.dumps({}), raw_response="not-valid-json")
        engine = _make_engine(row=row)
        with patch("sourcerykit.intercept._loader.get_engine", return_value=engine):
            with pytest.raises(SourceryKitStorageError, match="raw_response"):
                await load_latest_intercept_payload("agent-1", "action-a")
