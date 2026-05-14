# syntax=docker/dockerfile:1.7

# ----------------------------------------------------------------------------
# provably-sdk container layout
# ----------------------------------------------------------------------------
# Stage 1 (builder)  : produces a wheel from the current source tree.
# Stage 2 (runtime)  : minimal image with just the wheel installed, suitable
#                      for use as a base by services that consume the SDK.
#
# Local development and CI run via `uv` directly; the image intentionally
# does not bundle test tooling. See README.md "Development" / "Tests" for
# the uv-based workflow.
#
# Build:
#   docker build -t provably-sdk:runtime .
#
# Smoke-import:
#   docker run --rm provably-sdk:runtime
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

RUN python -m build --wheel --outdir /dist

# ---------- Stage 2: runtime ------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg2-binary ships its own libpq, but installing libpq5 keeps
# runtime tooling (psql, diagnostics) usable in derived images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /dist /dist

RUN pip install --upgrade pip \
    && pip install /dist/*.whl \
    && rm -rf /dist

CMD ["python", "-c", "import importlib.metadata as m, provably; print('provably-sdk', m.version('provably-sdk'), 'imported as', provably.__name__)"]
