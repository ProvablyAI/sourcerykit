#!/usr/bin/env bash
# Mirror CI lint + unit (coverage-gated) + e2e without Docker.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> sync dev extras"
uv sync --extra dev

echo "==> pytest-cov present?"
uv run python -c "import pytest_cov; print('pytest-cov', pytest_cov.__version__)"

echo "==> ruff"
uv run ruff check

echo "==> unit (coverage gate 60%)"
uv run pytest tests/unit -q --cov=provably --cov-report=term-missing --cov-fail-under=60

echo "==> e2e"
uv run pytest tests/e2e -q

echo "==> all CI-local checks passed"
