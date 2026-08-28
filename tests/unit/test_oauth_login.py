"""Tests for sourcerykit.provably.oauth_login."""

import base64
import hashlib
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from sourcerykit.provably import oauth_login
from sourcerykit.provably.oauth_login import pkce_pair


def test_pkce_pair_s256_verifiable() -> None:
    verifier, challenge = pkce_pair()
    assert verifier and challenge
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == expected


def _json_response(status: int, payload: dict[str, object]) -> httpx.Response:
    return httpx.Response(status, json=payload, request=httpx.Request("GET", "http://test"))


def _mock_client(fake_request: Callable[..., Any]) -> MagicMock:
    client = MagicMock(spec=httpx.AsyncClient)
    client.request = fake_request
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class TestFetchUserEmail:
    async def test_returns_top_level_email(self) -> None:
        async def fake_request(method: str, url: str, **kwargs: object) -> httpx.Response:
            assert method == "GET"
            assert "/api/v1/user/current" in url
            assert kwargs["headers"]["Authorization"] == "Bearer at"  # type: ignore[index]
            return _json_response(200, {"email": "a@b.com"})

        with patch("sourcerykit.provably.oauth_login.httpx.AsyncClient", return_value=_mock_client(fake_request)):
            assert await oauth_login.fetch_user_email("at") == "a@b.com"

    async def test_missing_email_raises(self) -> None:
        async def fake_request(method: str, url: str, **kwargs: object) -> httpx.Response:
            return _json_response(200, {"name": "no email"})

        with patch("sourcerykit.provably.oauth_login.httpx.AsyncClient", return_value=_mock_client(fake_request)):
            try:
                await oauth_login.fetch_user_email("at")
            except ValueError as e:
                assert "email" in str(e)
                return
        raise AssertionError("expected ValueError for missing email")


class TestRefresh:
    async def test_refresh_tokens_rotates(self) -> None:
        tokens = _json_response(200, {"access_token": "new-at", "refresh_token": "new-rt"})

        async def fake_request(method: str, url: str, **kwargs: object) -> httpx.Response:
            assert "oauth/refresh" in url
            return tokens

        with patch("sourcerykit.provably.oauth_login.httpx.AsyncClient", return_value=_mock_client(fake_request)):
            result = await oauth_login.refresh_tokens("old-rt")

        assert result.access_token == "new-at"
        assert result.refresh_token == "new-rt"
