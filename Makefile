# ----------------------------------------------------------------------------
# sourcerykit — developer Makefile
# ----------------------------------------------------------------------------
# All targets are thin wrappers over `uv`. The aliases here match what
# .github/workflows/ci.yml runs, so "green locally" maps 1:1 to "green in CI".
#
# Quick start:
#   make install          # uv sync --extra dev --locked
#   make check            # pre-commit + test + docs + build (CI parity)
#
# Run `make help` to list everything.
# ----------------------------------------------------------------------------

UV ?= uv
PYTEST_ARGS ?= --cov=sourcerykit --cov-report=term-missing --cov-fail-under=60
RUFF_ARGS ?=
MYPY_TARGETS ?= src tests
DOCS_DIR ?= docs
DOCS_BUILD ?= $(DOCS_DIR)/_build

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

.PHONY: pre-commit
pre-commit: ## Run all pre-commit hooks (matches CI)
	$(UV) run pre-commit run --all-files

.PHONY: lint
lint: ## Run ruff lint
	$(UV) run ruff check $(RUFF_ARGS)

.PHONY: format
format: ## Apply ruff formatter
	$(UV) run ruff format $(RUFF_ARGS)

.PHONY: format-check
format-check: ## Verify formatting without writing changes
	$(UV) run ruff format --check $(RUFF_ARGS)

.PHONY: typecheck
typecheck: ## Run mypy in strict mode
	$(UV) run mypy $(MYPY_TARGETS)

# --- tests ------------------------------------------------------------------

.PHONY: test
test: ## Run the full pytest suite with coverage gate (unit + e2e)
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

# --- versioning -------------------------------------------------------------

.PHONY: bump-release bump-patch bump-minor bump-major bump-beta bump-rc bump-pr tag

bump-release: ## Promote to stable release (e.g. 1.0.0b3 -> 1.0.0)
	$(UV) run bump-my-version bump --new-version $(shell sed -n 's/^current_version = "\([0-9.]*\).*/\1/p' pyproject.toml)

bump-patch: ## Bump patch version (e.g. 1.0.0 -> 1.0.1)
	$(UV) run bump-my-version bump patch

bump-minor: ## Bump minor version (e.g. 1.0.0 -> 1.1.0)
	$(UV) run bump-my-version bump minor

bump-major: ## Bump major version (e.g. 1.0.0 -> 2.0.0)
	$(UV) run bump-my-version bump major

bump-beta: ## Bump beta version (e.g. 1.0.0b3 -> 1.0.0b4)
	$(UV) run bump-my-version bump pre_num

bump-rc: ## Promote to release candidate (e.g. 1.0.0b3 -> 1.0.0rc1)
	$(UV) run bump-my-version bump pre

bump-pr: ## Bump version, commit, push branch (usage: make bump-pr TYPE=beta)
	git fetch origin main
	git checkout -b release/v$$($(UV) run bump-my-version show current_version)
	make bump-$(TYPE)
	make lock
	git add pyproject.toml README.md uv.lock CHANGELOG.md
	NEW_VER=$$($(UV) run bump-my-version show current_version) && \
	git commit -m "bump: $$NEW_VER" && \
	git push -u origin HEAD

tag: ## Create and push a version tag from current HEAD
	VERSION=$$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml) && \
	CHANGELOG=$$(awk "/^## $$VERSION/{found=1;next} /^## /{if(found)exit} found{print}" CHANGELOG.md | sed '/./,$!d') && \
	git tag -a v$$VERSION -m "$$CHANGELOG" && \
	git push origin v$$VERSION

# --- docs -------------------------------------------------------------------

.PHONY: docs
docs: ## Build Sphinx HTML under docs/_build
	$(UV) run sphinx-build -W -b html $(DOCS_DIR) $(DOCS_BUILD)

# --- meta workflows ---------------------------------------------------------

.PHONY: check
check: pre-commit test docs build ## Run the full CI-equivalent gate

.PHONY: clean
clean: ## Remove build artifacts and cache directories
	rm -rf build/ dist/ *.egg-info src/*.egg-info \
	       $(DOCS_BUILD) \
	       .pytest_cache .ruff_cache .mypy_cache \
	       .coverage .coverage.* htmlcov coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
