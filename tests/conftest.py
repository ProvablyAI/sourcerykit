"""Shared pytest configuration.

The SDK has two test layers:

- ``tests/unit/`` — fast, isolated tests with no real I/O. Mocks for ``httpx.Client``,
  ``psycopg2`` connections, and the interceptor's storage layer.
- ``tests/e2e/`` — black-box tests that drive the SDK against a real local HTTP
  server (started in-process with stdlib's ``http.server``) and the real
  ``requests`` / ``httpx`` libraries the SDK monkey-patches. The Postgres-touching
  storage layer is patched per-test so the suite stays hermetic and runs without a
  live database.

Both layers run by default. To run only one layer:

    pytest tests/unit          # fast inner loop
    pytest tests/e2e           # contract tests against a real loopback server
    pytest -m "not e2e"        # skip e2e tests

Coverage is gated on the hermetic unit suite only (CI + Docker enforce a 60%
floor); the threshold lives in ``[tool.coverage.report]`` in ``pyproject.toml``.
Coverage is not in the default ``pytest`` options, so the inner loop stays fast.
To check it locally:

    pytest tests/unit --cov=sourcerykit --cov-report=term-missing
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.e2e.conftest import FakeHttpServer


@pytest.fixture
def fake_server() -> Iterator[FakeHttpServer]:
    """Loopback HTTP server fixture available to both unit and e2e tests.

    Provides a real in-process loopback server so tests can drive SDK HTTP patches
    without any external network access.
    """
    server = FakeHttpServer()
    server.start()
    try:
        yield server
    finally:
        server.stop()
