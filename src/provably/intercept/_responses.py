"""Response wrappers that expose a mutated body to downstream callers."""

from __future__ import annotations

import json
from typing import Any

import httpx
import requests


def extract_raw(response: Any) -> Any:
    try:
        return response.json()
    except Exception:  # noqa: BLE001
        return {"text": getattr(response, "text", "")}


class RequestsJsonOverride:
    """Minimal ``requests.Response``-like wrapper returning an edited body (in-memory only)."""

    def __init__(self, orig: requests.Response, body: Any) -> None:
        self._orig = orig
        self._body = body

    def json(self, **kwargs: Any) -> Any:
        del kwargs
        return _as_json(self._body)

    @property
    def text(self) -> str:
        return _as_text(self._body)

    @property
    def content(self) -> bytes:
        return self.text.encode()

    def raise_for_status(self) -> None:
        self._orig.raise_for_status()

    @property
    def status_code(self) -> int:
        return self._orig.status_code

    @property
    def headers(self) -> Any:
        return self._orig.headers

    @property
    def url(self) -> str:
        return str(self._orig.url)


class HttpxJsonOverride:
    """Minimal ``httpx.Response``-like wrapper returning an edited body (in-memory only)."""

    def __init__(self, orig: httpx.Response, body: Any) -> None:
        self._orig = orig
        self._body = body

    def json(self) -> Any:
        return _as_json(self._body)

    @property
    def text(self) -> str:
        return _as_text(self._body)

    def raise_for_status(self) -> None:
        self._orig.raise_for_status()

    @property
    def status_code(self) -> int:
        return self._orig.status_code

    @property
    def headers(self) -> Any:
        return self._orig.headers


def _as_json(body: Any) -> Any:
    if isinstance(body, dict | list):
        return body
    if isinstance(body, str):
        return json.loads(body)
    return body


def _as_text(body: Any) -> str:
    if isinstance(body, str):
        return body
    return json.dumps(body, ensure_ascii=False)
