"""Shared fixtures for end-to-end tests.

Spins up a real HTTP server on a loopback port for each test that requests one.
The server is fully programmable per-test: register handlers as ``(method, path) -> (status, body)``
and the fixture returns its base URL so the test can drive the SDK against it.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

import provably.intercept.interceptor as _interceptor_module

Handler = Callable[["RecordedRequest"], "FakeResponse"]


@dataclass
class RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes


@dataclass
class FakeResponse:
    status: int = 200
    body: Any = b""
    headers: dict[str, str] = field(default_factory=dict)

    def encoded(self) -> tuple[bytes, dict[str, str]]:
        if isinstance(self.body, (dict, list)):
            payload = json.dumps(self.body).encode("utf-8")
            hdrs = {"Content-Type": "application/json", **self.headers}
            return payload, hdrs
        if isinstance(self.body, str):
            return self.body.encode("utf-8"), {"Content-Type": "text/plain", **self.headers}
        return self.body, dict(self.headers)


class FakeHttpServer:
    """Loopback HTTP server with per-test programmable routes and a request log."""

    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], Handler] = {}
        self.requests: list[RecordedRequest] = []
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        assert self._httpd is not None, "server not started"
        host, port = self._httpd.server_address[:2]
        if isinstance(host, bytes):
            host = host.decode("ascii")
        return f"http://{host}:{port}"

    def route(self, method: str, path: str, handler: Handler) -> None:
        self._routes[(method.upper(), path)] = handler

    def respond(self, method: str, path: str, *, status: int = 200, body: Any = b"") -> None:
        """Convenience wrapper for static responses."""
        self.route(method, path, lambda _req: FakeResponse(status=status, body=body))

    def start(self) -> None:
        owner = self

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: Any, **_kwargs: Any) -> None:  # silence
                return

            def _serve(self, method: str) -> None:
                length = int(self.headers.get("Content-Length", "0") or 0)
                body = self.rfile.read(length) if length > 0 else b""
                owner.requests.append(
                    RecordedRequest(
                        method=method,
                        path=self.path,
                        headers={k: v for k, v in self.headers.items()},
                        body=body,
                    )
                )
                handler = owner._routes.get((method, self.path.split("?", 1)[0]))
                if handler is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                resp = handler(owner.requests[-1])
                payload, hdrs = resp.encoded()
                self.send_response(resp.status)
                for key, value in hdrs.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if payload:
                    self.wfile.write(payload)

            def do_GET(self) -> None:  # noqa: N802
                self._serve("GET")

            def do_POST(self) -> None:  # noqa: N802
                self._serve("POST")

        self._httpd = HTTPServer(("127.0.0.1", 0), _Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)


@pytest.fixture
def fake_server_factory() -> Iterator[Callable[[], FakeHttpServer]]:
    """Factory fixture that creates and tracks multiple FakeHttpServer instances.

    Each call to the returned factory function starts a new server; all servers
    are shut down after the test finishes.
    """
    servers: list[FakeHttpServer] = []

    def _make() -> FakeHttpServer:
        s = FakeHttpServer()
        s.start()
        servers.append(s)
        return s

    yield _make

    for s in servers:
        s.stop()


@pytest.fixture
def patched_interceptor(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Install the real interceptor with the storage layer redirected to an in-memory list.

    Yields the list of recorded rows so tests can assert against it.
    This fixture is shared between test_interceptor_e2e.py and test_openai_agents_e2e.py.
    """
    rows: list[dict[str, Any]] = []

    def fake_insert(_url: str, request_payload: dict[str, Any], raw: Any, *, method: str = "GET") -> None:
        rows.append({"url": _url, "method": method, "request": request_payload, "raw": raw})

    monkeypatch.setattr(_interceptor_module, "_insert_row", fake_insert)
    _interceptor_module.init_interceptor()
    monkeypatch.setattr(_interceptor_module, "_enabled", True)
    return rows
