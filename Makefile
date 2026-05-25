# ----------------------------------------------------------------------------
# provably-sdk — developer Makefile
# ----------------------------------------------------------------------------
# All targets are thin wrappers over `uv`. The aliases here match what
# .github/workflows/ci.yml runs, so "green locally" maps 1:1 to "green in CI".
#
# Quick start:
#   make install          # uv sync --extra dev --locked
#   make check            # lint + typecheck + test (CI parity)
#
# Run `make help` to list everything.
# ----------------------------------------------------------------------------

UV ?= uv
PYTEST_ARGS ?=
RUFF_ARGS ?=
MYPY_TARGETS ?= src tests
DOCS_DIR ?= docs

.DEFAULT_GOAL := help

# --- meta -------------------------------------------------------------------

.PHONY: help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# --- environment ------------------------------------------------------------

.PHONY: install
install: ## Sync the dev virtualenv (matches CI: lock must match pyproject)
	$(UV) sync --extra dev --locked

.PHONY: lock
lock: ## Refresh uv.lock from pyproject.toml
	$(UV) lock

.PHONY: lock-upgrade
lock-upgrade: ## Refresh uv.lock and upgrade pinned versions
	$(UV) lock --upgrade

# --- quality ----------------------------------------------------------------

.PHONY: lint
lint: ## Run ruff lint (matches CI)
	$(UV) run ruff check $(RUFF_ARGS)

.PHONY: format
format: ## Apply ruff formatter
	$(UV) run ruff format $(RUFF_ARGS)

.PHONY: format-check
format-check: ## Verify formatting without writing changes
	$(UV) run ruff format --check $(RUFF_ARGS)

.PHONY: typecheck
typecheck: ## Run mypy in strict mode (requires the dev extra; see point 5)
	$(UV) run mypy $(MYPY_TARGETS)

# --- tests ------------------------------------------------------------------

.PHONY: test
test: ## Run the full pytest suite (unit + e2e)
	$(UV) run pytest -q $(PYTEST_ARGS)

.PHONY: test-unit
test-unit: ## Run only the fast hermetic unit suite
	$(UV) run pytest -q -m "not e2e" $(PYTEST_ARGS)

.PHONY: test-e2e
test-e2e: ## Run only the loopback-server e2e suite
	$(UV) run pytest -q -m e2e $(PYTEST_ARGS)

# --- packaging --------------------------------------------------------------

.PHONY: build
build: ## Build wheel + sdist into ./dist via uv build
	$(UV) build

# --- docs -------------------------------------------------------------------

.PHONY: docs
docs: ## Point at the canonical Markdown docs (no doc-site tooling in Phase 1)
	@echo "Docs are Markdown under $(DOCS_DIR)/. Entry points:"
	@echo "  README.md            top-level intro + quickstart"
	@echo "  CONTEXT.md           agent contract: invariants + dependency rules"
	@echo "  $(DOCS_DIR)/README.md           per-pillar deep-dives index"
	@echo "  $(DOCS_DIR)/architecture.md     module map + I/O boundaries"
	@echo "  $(DOCS_DIR)/intercept.md        intercept pillar"
	@echo "  $(DOCS_DIR)/handoff.md          handoff pillar"
	@echo "  $(DOCS_DIR)/trusted-endpoints.md trusted-endpoint registry"

# --- meta workflows ---------------------------------------------------------

.PHONY: check
check: lint typecheck test ## Run the full CI-equivalent gate (lint + typecheck + test)

.PHONY: clean
clean: ## Remove build artifacts and cache directories
	rm -rf build/ dist/ *.egg-info src/*.egg-info \
	       .pytest_cache .ruff_cache .mypy_cache \
	       .coverage .coverage.* htmlcov coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
