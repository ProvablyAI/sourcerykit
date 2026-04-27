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
"""

from __future__ import annotations
