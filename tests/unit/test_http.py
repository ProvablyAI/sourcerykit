"""Tests for sourcerykit.provably._http.ProvablyHTTPClient."""

import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sourcerykit.config import Settings
from sourcerykit.provably._http import ProvablyHTTPClient, _clear_refresh_token, _persist_tokens

_ORG = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Provide env so _fetch's default Bearer resolution (get_settings) succeeds."""
    from sourcerykit.config import get_settings, load_app_dir_config, load_local_env

    get_settings.cache_clear()
    load_app_dir_config.cache_clear()
    load_local_env.cache_clear()
    monkeypatch.setenv("PROVABLY_ACCESS_TOKEN", "test-access-token")
    monkeypatch.setenv("SOURCERYKIT_ORG_ID", _ORG)
    yield
    get_settings.cache_clear()
    load_app_dir_config.cache_clear()
    load_local_env.cache_clear()


def _make_settings(api_url: str = "https://api.provably.ai") -> Settings:
    import uuid

    return Settings(
        access_token="test-access-token",
        org_id=uuid.UUID(_ORG),
        postgres_url="postgresql://user:pass@localhost/db",
        provably_api=api_url,
    )


def _make_client(api_url: str = "https://api.provably.ai") -> ProvablyHTTPClient:
    return ProvablyHTTPClient(settings=_make_settings(api_url))


class TestProvablyHTTPClientInit:
    def test_base_url_stripped_of_trailing_slash(self) -> None:
        client = _make_client("https://api.provably.ai/")
        assert client.base_url == "https://api.provably.ai"

    def test_headers_do_not_include_auth(self) -> None:
        client = _make_client()
        assert "x-api-key" not in client._headers
        assert "Authorization" not in client._headers

    def test_headers_include_content_type(self) -> None:
        client = _make_client()
        assert client._headers["Content-Type"] == "application/json"


class TestProvablyHTTPClientGet:
    async def test_get_returns_parsed_json(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.content = b'{"result": "ok"}'
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": "ok"}

        with patch.object(client, "_request", AsyncMock(return_value=mock_response)):
            result = await client.get("/test-path")
        assert result == {"result": "ok"}

    async def test_get_raises_on_http_status_error(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        error = httpx.HTTPStatusError("404", request=MagicMock(), response=mock_response)

        with patch.object(client, "_request", AsyncMock(side_effect=error)):
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("/missing")

    async def test_get_passes_params(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.content = b"{}"
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {}

        with patch.object(client, "_request", AsyncMock(return_value=mock_response)) as mock_req:
            await client.get("/path", params={"key": "val"})
            _, kwargs = mock_req.call_args
            assert kwargs.get("params") == {"key": "val"}


class TestProvablyHTTPClientAuth:
    async def test_post_auth_injects_access_token_as_bearer(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.content = b'{"result": "ok"}'
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"result": "ok"}

        with (
            patch("sourcerykit.provably._http.get_settings", return_value=_make_settings()),
            patch.object(client, "_request", AsyncMock(return_value=mock_response)) as mock_req,
        ):
            await client.get("/path")

        _, kwargs = mock_req.call_args
        assert kwargs.get("token") == "test-access-token"

    async def test_api_key_override_suppresses_bearer(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.content = b'{"ok": true}'
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"ok": True}

        with (
            patch("sourcerykit.provably._http.get_settings", return_value=_make_settings()),
            patch.object(client, "_request", AsyncMock(return_value=mock_response)) as mock_req,
        ):
            await client.get("/path", api_key="i-zk-123")

        _, kwargs = mock_req.call_args
        assert kwargs.get("api_key") == "i-zk-123"
        assert kwargs.get("token") is None


class TestProvablyHTTPClientPost:
    async def test_post_returns_empty_dict_on_empty_body(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_request", AsyncMock(return_value=mock_response)):
            result = await client.post("/some/path", json={"payload": "data"})
        assert result == {}

    async def test_post_with_custom_api_key(self) -> None:
        client = _make_client()
        mock_response = MagicMock()
        mock_response.content = b'{"ok": true}'
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"ok": True}

        with patch.object(client, "_request", AsyncMock(return_value=mock_response)) as mock_req:
            await client.post("/path", json={}, api_key="custom-key")
            _, kwargs = mock_req.call_args
            assert kwargs.get("api_key") == "custom-key"


class TestProvablyHTTPClientPreAuth:
    def test_pre_auth_sets_content_type_only(self) -> None:
        with patch("sourcerykit.provably._http.get_bootstrap_settings", return_value="https://api.provably.ai"):
            client = ProvablyHTTPClient(pre_auth=True)
        assert "Content-Type" in client._headers
        assert "x-api-key" not in client._headers

    def test_pre_auth_base_url_from_bootstrap_settings(self) -> None:
        with patch("sourcerykit.provably._http.get_bootstrap_settings", return_value="https://custom.provably.ai"):
            client = ProvablyHTTPClient(pre_auth=True)
        assert client.base_url == "https://custom.provably.ai"

    async def test_pre_auth_token_sets_authorization_header(self) -> None:
        with patch("sourcerykit.provably._http.get_bootstrap_settings", return_value="https://api.provably.ai"):
            client = ProvablyHTTPClient(pre_auth=True)

        mock_response = MagicMock()
        mock_response.content = b'{"token": "abc"}'
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"token": "abc"}

        with patch.object(client, "_request", AsyncMock(return_value=mock_response)) as mock_req:
            await client.get("/api/v1/user/key", token="my-jwt-token")
            _, kwargs = mock_req.call_args
            assert kwargs.get("token") == "my-jwt-token"


class TestTokenStorePersistence:
    def test_persist_tokens_writes_to_app_store_and_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = tmp_path / "app.env"
        monkeypatch.setenv("SOURCERYKIT_TOKEN_STORE", str(store))

        with (
            patch("sourcerykit.provably._http.get_settings") as mock_gs,
            patch("sourcerykit.provably._http.load_local_env") as mock_lle,
            patch("sourcerykit.provably._http.save_app_dir_config") as mock_save,
        ):
            _persist_tokens("at2", "rt2")

        mock_save.assert_not_called()
        assert os.environ["PROVABLY_ACCESS_TOKEN"] == "at2"
        assert os.environ["PROVABLY_REFRESH_TOKEN"] == "rt2"
        content = store.read_text()
        assert "PROVABLY_ACCESS_TOKEN" in content and "at2" in content
        assert "PROVABLY_REFRESH_TOKEN" in content and "rt2" in content
        mock_lle.cache_clear.assert_called_once()
        mock_gs.cache_clear.assert_called_once()

    def test_persist_tokens_uses_global_json_when_no_store(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SOURCERYKIT_TOKEN_STORE", raising=False)
        with patch("sourcerykit.provably._http.save_app_dir_config") as mock_save:
            _persist_tokens("at", None)
        mock_save.assert_called_once_with(token="at", refresh_token=None)

    def test_clear_refresh_token_from_app_store(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        store = tmp_path / "app.env"
        monkeypatch.setenv("SOURCERYKIT_TOKEN_STORE", str(store))
        store.write_text("PROVABLY_REFRESH_TOKEN=rt\n")
        os.environ["PROVABLY_REFRESH_TOKEN"] = "rt"

        _clear_refresh_token()

        assert "PROVABLY_REFRESH_TOKEN" not in os.environ
        assert "PROVABLY_REFRESH_TOKEN=" in store.read_text()


class TestProvablyHTTPClientOAuthRefresh:
    def _make_401(self) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 401
        resp.text = "expired"
        req = httpx.Request("GET", "http://x")
        resp.raise_for_status.side_effect = httpx.HTTPStatusError("401", request=req, response=resp)
        return resp

    def _make_ok(self) -> MagicMock:
        resp = MagicMock()
        resp.content = b'{"ok": true}'
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"ok": True}
        return resp

    async def test_401_refreshes_once_and_retries(self) -> None:
        client = _make_client()
        calls = 0

        async def fake_request(method: str, path: str, **kwargs: object) -> MagicMock:
            nonlocal calls
            calls += 1
            return self._make_ok() if calls > 1 else self._make_401()

        client._request = fake_request  # type: ignore[method-assign]

        with patch("sourcerykit.provably._http._refresh_session", AsyncMock(return_value="new-token")) as refresh:
            result = await client.get("/api/v1/data", token="old-token")

        assert result == {"ok": True}
        refresh.assert_awaited_once()
        assert calls == 2

    async def test_401_without_refresh_token_raises(self) -> None:
        client = _make_client()
        client._request = AsyncMock(return_value=self._make_401())  # type: ignore[method-assign]

        with patch("sourcerykit.provably._http._refresh_session", AsyncMock(return_value=None)):
            with pytest.raises(httpx.HTTPStatusError):
                await client.get("/api/v1/data", token="old-token")
