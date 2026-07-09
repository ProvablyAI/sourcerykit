"""Tests for sourcerykit.provably._errors — error hierarchy and provably_error_handler."""

import httpx
import pytest

from sourcerykit.errors import SourceryKitError
from sourcerykit.provably._errors import (
    ProvablyAPIError,
    ProvablyAuthError,
    ProvablyConnectionError,
    ProvablyDataError,
    ProvablyError,
    ProvablyNotFoundError,
    ProvablyResourceAlreadyExistsError,
    ProvablyUnauthorizedError,
    provably_auth_error_handler,
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

    def test_not_found_is_api_error(self) -> None:
        assert issubclass(ProvablyNotFoundError, ProvablyAPIError)

    def test_not_found_stores_status_code(self) -> None:
        err = ProvablyNotFoundError("not found", status_code=404, response_body="Not Found")
        assert err.status_code == 404


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

    async def test_http_404_raises_not_found_error(self) -> None:
        mock_request = httpx.Request("GET", "https://api.provably.ai/test")
        mock_response = httpx.Response(404, request=mock_request, text="Not Found")
        http_err = httpx.HTTPStatusError("404", request=mock_request, response=mock_response)

        with pytest.raises(ProvablyNotFoundError) as exc_info:
            async with provably_error_handler("get_preprocess_status"):
                raise http_err

        assert exc_info.value.status_code == 404

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


# ---------------------------------------------------------------------------
# Auth error class hierarchy
# ---------------------------------------------------------------------------


class TestAuthErrorHierarchy:
    def test_auth_error_is_api_error(self) -> None:
        assert issubclass(ProvablyAuthError, ProvablyAPIError)

    def test_resource_already_exists_is_auth_error(self) -> None:
        assert issubclass(ProvablyResourceAlreadyExistsError, ProvablyAuthError)

    def test_unauthorized_is_auth_error(self) -> None:
        assert issubclass(ProvablyUnauthorizedError, ProvablyAuthError)

    def test_auth_error_stores_status_code_and_body(self) -> None:
        err = ProvablyAuthError("bad auth", status_code=403, response_body="Forbidden")
        assert err.status_code == 403
        assert err.response_body == "Forbidden"

    def test_unauthorized_error_stores_status_code(self) -> None:
        err = ProvablyUnauthorizedError("wrong credentials", status_code=401, response_body="Unauthorized")
        assert err.status_code == 401

    def test_resource_already_exists_is_sourcerykit_error(self) -> None:
        assert issubclass(ProvablyResourceAlreadyExistsError, SourceryKitError)


# ---------------------------------------------------------------------------
# provably_auth_error_handler
# ---------------------------------------------------------------------------


class TestProvablyAuthErrorHandler:
    async def test_no_exception_passes_through(self) -> None:
        async with provably_auth_error_handler("test_op"):
            pass  # must not raise

    async def test_http_401_raises_unauthorized_error(self) -> None:
        mock_request = httpx.Request("POST", "https://api.provably.ai/api/v1/auth/login")
        mock_response = httpx.Response(401, request=mock_request, text="Unauthorized")
        http_err = httpx.HTTPStatusError("401", request=mock_request, response=mock_response)

        with pytest.raises(ProvablyUnauthorizedError) as exc_info:
            async with provably_auth_error_handler("login"):
                raise http_err

        assert exc_info.value.status_code == 401
        assert "login" in str(exc_info.value).lower()

    async def test_http_400_raises_auth_error(self) -> None:
        mock_request = httpx.Request("POST", "https://api.provably.ai/api/v1/auth/register")
        mock_response = httpx.Response(400, request=mock_request, json={"description": "Email already registered"})
        http_err = httpx.HTTPStatusError("400", request=mock_request, response=mock_response)

        with pytest.raises(ProvablyAuthError) as exc_info:
            async with provably_auth_error_handler("create_account"):
                raise http_err

        assert exc_info.value.status_code == 400

    async def test_http_500_raises_auth_error(self) -> None:
        mock_request = httpx.Request("POST", "https://api.provably.ai/api/v1/auth/login")
        mock_response = httpx.Response(500, request=mock_request, text="Internal Server Error")
        http_err = httpx.HTTPStatusError("500", request=mock_request, response=mock_response)

        with pytest.raises(ProvablyAuthError) as exc_info:
            async with provably_auth_error_handler("login"):
                raise http_err

        assert exc_info.value.status_code == 500

    async def test_http_409_raises_resource_already_exists(self) -> None:
        mock_request = httpx.Request("POST", "https://api.provably.ai/api/v1/organizations")
        mock_response = httpx.Response(409, request=mock_request, text="Conflict")
        http_err = httpx.HTTPStatusError("409", request=mock_request, response=mock_response)

        with pytest.raises(ProvablyResourceAlreadyExistsError) as exc_info:
            async with provably_auth_error_handler("create_organization"):
                raise http_err

        assert exc_info.value.status_code == 409

    async def test_value_error_raises_data_error(self) -> None:
        with pytest.raises(ProvablyDataError):
            async with provably_auth_error_handler("get_api_key"):
                raise ValueError("unexpected key in response")

    async def test_key_error_raises_data_error(self) -> None:
        with pytest.raises(ProvablyDataError):
            async with provably_auth_error_handler("get_api_key"):
                raise KeyError("api_key")

    async def test_type_error_raises_data_error(self) -> None:
        with pytest.raises(ProvablyDataError):
            async with provably_auth_error_handler("create_organization"):
                raise TypeError("cannot convert")

    async def test_request_error_raises_connection_error(self) -> None:
        req = httpx.Request("POST", "https://api.provably.ai/api/v1/auth/login")
        with pytest.raises(ProvablyConnectionError):
            async with provably_auth_error_handler("login"):
                raise httpx.ConnectError("connection refused", request=req)
