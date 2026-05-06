# syntax=docker/dockerfile:1.7

# ----------------------------------------------------------------------------
# provably-sdk container layout
# ----------------------------------------------------------------------------
# Stage 1 (builder)  : produces a wheel + sdist from the current source tree.
# Stage 2 (test)     : installs the built wheel with [dev] extras and runs
#                      `ruff check` + `pytest -q` (default CMD).
# Stage 3 (runtime)  : minimal image with just the wheel installed, suitable
#                      for use as a base by services that consume the SDK.
#
# Build all stages:
#   docker build -t provably-sdk:test --target test .
#   docker build -t provably-sdk:runtime --target runtime .
#
# Run the test suite in a container:
#   docker run --rm provably-sdk:test
# ----------------------------------------------------------------------------

ARG PYTHON_VERSION=3.12

# ---------- Stage 1: builder ------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN pip install --upgrade pip build

COPY pyproject.toml README.md LICENSE.md ./
COPY src ./src

RUN python -m build --wheel --sdist --outdir /dist

# ---------- Stage 2: test ---------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS test

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg2-binary ships its own libpq, but pytest invocations may still
# benefit from the runtime libpq presence on slim images for diagnostic tools.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /dist /dist

RUN pip install --upgrade pip \
    && pip install /dist/*.whl \
    && pip install "pytest>=8.0" "pytest-asyncio>=0.23" "ruff>=0.3" "build>=1.2" "openai-agents" "aiohttp>=3.9"

COPY pyproject.toml ./
COPY tests ./tests

CMD ["sh", "-lc", "ruff check . && pytest -q"]

# ---------- Stage 3: runtime ------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /dist /dist

RUN pip install --upgrade pip \
    && pip install /dist/*.whl \
    && rm -rf /dist

CMD ["python", "-c", "import importlib.metadata as m, provably; print('provably-sdk', m.version('provably-sdk'), 'imported as', provably.__name__)"]
