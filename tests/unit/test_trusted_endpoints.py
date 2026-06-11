"""Tests for sourcerykit.trusted_endpoints.service"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcerykit.errors import SourceryKitStorageError, SourceryKitTrustError
from sourcerykit.schemas import HandoffClaim, HandoffPayload
from sourcerykit.trusted_endpoints.service import (
    insert_trusted_endpoint,
    is_endpoint_trusted,
    sanitize_and_extract_trusted_url,
    verify_claim_endpoints,
)

_ORG = uuid.uuid4()


# ---------------------------------------------------------------------------
# sanitize_and_extract_trusted_url
# ---------------------------------------------------------------------------


class TestSanitizeAndExtractTrustedUrl:
    def test_strips_query_string(self) -> None:
        assert sanitize_and_extract_trusted_url("https://api.example.com/v1?foo=1") == "https://api.example.com/v1"

    def test_strips_trailing_slash(self) -> None:
        assert sanitize_and_extract_trusted_url("https://api.example.com/") == "https://api.example.com"

    def test_adds_https_scheme_when_missing(self) -> None:
        result = sanitize_and_extract_trusted_url("api.example.com")
        assert result == "https://api.example.com"

    def test_keeps_http_scheme(self) -> None:
        assert sanitize_and_extract_trusted_url("http://localhost:8080/path") == "http://localhost:8080/path"

    def test_preserves_path(self) -> None:
        assert sanitize_and_extract_trusted_url("https://example.com/api/v2") == "https://example.com/api/v2"

    def test_strips_surrounding_whitespace(self) -> None:
        assert sanitize_and_extract_trusted_url("  https://example.com  ") == "https://example.com"

    def test_raises_trust_error_when_no_netloc(self) -> None:
        with pytest.raises(SourceryKitTrustError):
            sanitize_and_extract_trusted_url("///not-a-url")


# ---------------------------------------------------------------------------
# is_endpoint_trusted
# ---------------------------------------------------------------------------


def _make_connect_mock(scalar_return: bool = True, raise_exc: Exception | None = None) -> MagicMock:
    """Build a mock async engine where .connect() returns a scalar bool."""
    mock_result = MagicMock()
    mock_conn = AsyncMock()

    if raise_exc:
        mock_conn.execute = AsyncMock(side_effect=raise_exc)
    else:
        mock_result.scalar.return_value = scalar_return
        mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_ctx
    return mock_engine


def _make_begin_mock(raise_exc: Exception | None = None) -> MagicMock:
    """Build a mock async engine where .begin() supports execute."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_ctx = AsyncMock()
    if raise_exc:
        mock_ctx.__aenter__ = AsyncMock(side_effect=raise_exc)
    else:
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_ctx
    return mock_engine


class TestIsEndpointTrusted:
    async def test_returns_true_when_db_says_trusted(self) -> None:
        mock_engine = _make_connect_mock(scalar_return=True)
        with (
            patch("sourcerykit.trusted_endpoints.service.get_engine", return_value=mock_engine),
            patch("sourcerykit.trusted_endpoints.service.get_settings") as ms,
        ):
            ms.return_value.org_id = _ORG
            assert await is_endpoint_trusted("https://trusted.example.com") is True

    async def test_returns_false_when_db_says_not_trusted(self) -> None:
        mock_engine = _make_connect_mock(scalar_return=False)
        with (
            patch("sourcerykit.trusted_endpoints.service.get_engine", return_value=mock_engine),
            patch("sourcerykit.trusted_endpoints.service.get_settings") as ms,
        ):
            ms.return_value.org_id = _ORG
            assert await is_endpoint_trusted("https://untrusted.example.com") is False

    async def test_raises_storage_error_on_db_failure(self) -> None:
        mock_engine = _make_connect_mock(raise_exc=RuntimeError("db down"))
        with (
            patch("sourcerykit.trusted_endpoints.service.get_engine", return_value=mock_engine),
            patch("sourcerykit.trusted_endpoints.service.get_settings") as ms,
        ):
            ms.return_value.org_id = _ORG
            with pytest.raises(SourceryKitStorageError):
                await is_endpoint_trusted("https://example.com")

    async def test_url_is_sanitized_before_query(self) -> None:
        """A URL with a path and query string should be sanitized before lookup."""
        mock_engine = _make_connect_mock(scalar_return=True)
        with (
            patch("sourcerykit.trusted_endpoints.service.get_engine", return_value=mock_engine),
            patch("sourcerykit.trusted_endpoints.service.get_settings") as ms,
            patch("sourcerykit.trusted_endpoints.service.select_trusted_endpoint_prefix") as mock_stmt,
        ):
            ms.return_value.org_id = _ORG
            mock_stmt.return_value = MagicMock()
            await is_endpoint_trusted("https://example.com/v1/path?foo=bar")
            # Sanitized URL passed to the DB helper should strip query
            called_url = mock_stmt.call_args[0][1]
            assert "?" not in called_url


# ---------------------------------------------------------------------------
# insert_trusted_endpoint
# ---------------------------------------------------------------------------


class TestInsertTrustedEndpoint:
    async def test_inserts_successfully(self) -> None:
        mock_engine = _make_begin_mock()
        with (
            patch("sourcerykit.trusted_endpoints.service.get_engine", return_value=mock_engine),
            patch("sourcerykit.trusted_endpoints.service.get_settings") as ms,
        ):
            ms.return_value.org_id = _ORG
            await insert_trusted_endpoint("https://new.example.com", display_label="My EP")
        mock_engine.begin.assert_called_once()

    async def test_raises_storage_error_on_db_failure(self) -> None:
        mock_engine = _make_begin_mock(raise_exc=RuntimeError("fail"))
        with (
            patch("sourcerykit.trusted_endpoints.service.get_engine", return_value=mock_engine),
            patch("sourcerykit.trusted_endpoints.service.get_settings") as ms,
        ):
            ms.return_value.org_id = _ORG
            with pytest.raises(SourceryKitStorageError):
                await insert_trusted_endpoint("https://example.com")

    async def test_rejects_display_label_over_255_chars(self) -> None:
        with patch("sourcerykit.trusted_endpoints.service.get_settings") as ms:
            ms.return_value.org_id = _ORG
            with pytest.raises(ValueError, match="display_label"):
                await insert_trusted_endpoint("https://example.com", display_label="x" * 256)


# ---------------------------------------------------------------------------
# verify_claim_endpoints
# ---------------------------------------------------------------------------


class TestVerifyClaimEndpoints:
    async def test_passes_when_all_source_urls_trusted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "sourcerykit.trusted_endpoints.service.is_endpoint_trusted",
            AsyncMock(return_value=True),
        )
        payload = HandoffPayload(claims=[HandoffClaim(action_name="a", request_payload={"url": "https://api.ok.com"})])
        await verify_claim_endpoints(payload)  # must not raise

    async def test_raises_when_endpoint_not_trusted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "sourcerykit.trusted_endpoints.service.is_endpoint_trusted",
            AsyncMock(return_value=False),
        )
        payload = HandoffPayload(claims=[HandoffClaim(action_name="a", request_payload={"url": "https://bad.com"})])
        with pytest.raises((ValueError, SourceryKitTrustError, SourceryKitStorageError)):
            await verify_claim_endpoints(payload)

    async def test_empty_claims_does_not_raise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "sourcerykit.trusted_endpoints.service.is_endpoint_trusted",
            AsyncMock(return_value=True),
        )
        await verify_claim_endpoints(HandoffPayload())  # must not raise
