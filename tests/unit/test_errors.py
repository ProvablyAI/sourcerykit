"""Tests for sourcerykit.provably._errors — error hierarchy and provably_error_handler."""

import httpx
import pytest

from sourcerykit.errors import SourceryKitError
from sourcerykit.provably._errors import (
    ProvablyAPIError,
    ProvablyConnectionError,
    ProvablyDataError,
    ProvablyError,
    provably_error_handler,
)

# ---------------------------------------------------------------------------
# Error class hierarchy
# ---------------------------------------------------------------------------


class TestErrorHierarchy:
    def test_provably_error_is_sourcerykit_error(self) -> None:
        assert issubclass(ProvablyError, SourceryKitError)

    def test_api_error_is_provably_error(self) -> None:
        assert issubclass(ProvablyAPIError, ProvablyError)

    def test_connection_error_is_provably_error(self) -> None:
        assert issubclass(ProvablyConnectionError, ProvablyError)

    def test_data_error_is_provably_error(self) -> None:
        assert issubclass(ProvablyDataError, ProvablyError)

    def test_api_error_stores_status_code(self) -> None:
        err = ProvablyAPIError("bad request", status_code=400, response_body="oops")
        assert err.status_code == 400
        assert err.response_body == "oops"

    def test_api_error_status_code_defaults_to_none(self) -> None:
        err = ProvablyAPIError("bad request")
        assert err.status_code is None


# ---------------------------------------------------------------------------
# provably_error_handler
# ---------------------------------------------------------------------------


class TestProvablyErrorHandler:
    async def test_no_exception_passes_through(self) -> None:
        async with provably_error_handler("test_op"):
            pass  # must not raise

    async def test_http_status_error_raises_api_error(self) -> None:
        mock_request = httpx.Request("GET", "https://api.provably.ai/test")
        mock_response = httpx.Response(422, request=mock_request, text="Unprocessable")
        http_err = httpx.HTTPStatusError("422", request=mock_request, response=mock_response)

        with pytest.raises(ProvablyAPIError) as exc_info:
            async with provably_error_handler("run_query"):
                raise http_err

        assert exc_info.value.status_code == 422
        assert "run query" in str(exc_info.value).lower()

    async def test_value_error_raises_data_error(self) -> None:
        with pytest.raises(ProvablyDataError):
            async with provably_error_handler("get_collection"):
                raise ValueError("unexpected key in response")

    async def test_key_error_raises_data_error(self) -> None:
        with pytest.raises(ProvablyDataError):
            async with provably_error_handler("get_database"):
                raise KeyError("missing_field")

    async def test_request_error_raises_connection_error(self) -> None:
        req = httpx.Request("GET", "https://api.provably.ai/")
        with pytest.raises(ProvablyConnectionError):
            async with provably_error_handler("create_middleware"):
                raise httpx.ConnectError("connection refused", request=req)

    async def test_unexpected_exception_raises_provably_error(self) -> None:
        with pytest.raises(ProvablyError):
            async with provably_error_handler("run_query"):
                raise RuntimeError("something unexpected")
