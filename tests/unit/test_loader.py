"""Tests for sourcerykit.intercept._loader.load_intercept_payload_by_call_ref."""

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcerykit.errors import SourceryKitStorageError
from sourcerykit.intercept._loader import load_intercept_payload_by_call_ref


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


def _make_row(
    request_payload: str | None = None,
    raw_response: str | None = None,
    row_id: uuid.UUID | None = None,
) -> MagicMock:
    row = MagicMock()
    row.request_payload = request_payload
    row.raw_response = raw_response
    row.id = row_id or uuid.uuid4()
    return row


class TestLoadInterceptPayloadByCallRef:
    async def test_raises_when_no_row(self) -> None:
        engine = _make_engine(row=None)
        ref = uuid.uuid4()
        with patch("sourcerykit.intercept._loader.get_engine", return_value=engine):
            with pytest.raises(SourceryKitStorageError, match="No intercept found"):
                await load_intercept_payload_by_call_ref(ref)

    async def test_returns_parsed_request_response_and_row_id(self) -> None:
        rid = uuid.uuid4()
        row = _make_row(
            request_payload=json.dumps({"method": "POST", "url": "https://api.example.com"}),
            raw_response=json.dumps({"status": "ok"}),
            row_id=rid,
        )
        engine = _make_engine(row=row)
        ref = uuid.uuid4()
        with patch("sourcerykit.intercept._loader.get_engine", return_value=engine):
            req, resp, row_id = await load_intercept_payload_by_call_ref(ref)
        assert req == {"method": "POST", "url": "https://api.example.com"}
        assert resp == {"status": "ok"}
        assert row_id == rid

    async def test_returns_empty_request_when_payload_is_none(self) -> None:
        rid = uuid.uuid4()
        row = _make_row(request_payload=None, raw_response=None, row_id=rid)
        engine = _make_engine(row=row)
        ref = uuid.uuid4()
        with patch("sourcerykit.intercept._loader.get_engine", return_value=engine):
            req, resp, row_id = await load_intercept_payload_by_call_ref(ref)
        assert req == {}
        assert resp is None
        assert row_id == rid

    async def test_raises_storage_error_on_corrupt_request_payload(self) -> None:
        row = _make_row(request_payload="not-valid-json", raw_response=None)
        engine = _make_engine(row=row)
        ref = uuid.uuid4()
        with patch("sourcerykit.intercept._loader.get_engine", return_value=engine):
            with pytest.raises(SourceryKitStorageError, match="request_payload"):
                await load_intercept_payload_by_call_ref(ref)

    async def test_raises_storage_error_on_corrupt_raw_response(self) -> None:
        row = _make_row(request_payload=json.dumps({}), raw_response="not-valid-json")
        engine = _make_engine(row=row)
        ref = uuid.uuid4()
        with patch("sourcerykit.intercept._loader.get_engine", return_value=engine):
            with pytest.raises(SourceryKitStorageError, match="raw_response"):
                await load_intercept_payload_by_call_ref(ref)
