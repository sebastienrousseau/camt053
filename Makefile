.PHONY: help install dev test lint format type-check security clean docs docker smoke examples pip-compile

PYTHON ?= python3
POETRY ?= poetry

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(POETRY) install --only main

dev: ## Install all dependencies (including dev)
	$(POETRY) install

test: ## Run tests with coverage
	$(POETRY) run pytest tests/ -v

test-fast: ## Run tests without coverage (faster)
	$(POETRY) run pytest tests/ -v --no-cov

test-parallel: ## Run tests in parallel
	$(POETRY) run pytest tests/ -v -n auto

lint: ## Run linters (ruff + black check)
	$(POETRY) run ruff check camt053/ tests/
	$(POETRY) run black --check camt053/ tests/

format: ## Auto-format code (ruff fix + black)
	$(POETRY) run ruff check --fix camt053/ tests/
	$(POETRY) run black camt053/ tests/

type-check: ## Run mypy type checking
	$(POETRY) run mypy camt053/

security: ## Run security scan (bandit)
	$(POETRY) run bandit -r camt053/ -c pyproject.toml 2>/dev/null || \
		$(POETRY) run bandit -r camt053/ -ll

pip-compile: ## Regenerate hash-pinned requirements/*.txt from requirements/*.in
	@command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/"; exit 1; }
	@for f in requirements/*.in; do \
		echo "compiling $$f"; \
		uv pip compile --quiet --generate-hashes --universal \
			--python-version 3.10 "$$f" -o "$${f%.in}.txt"; \
	done

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info .eggs/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/
	rm -rf coverage.xml .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

docs: ## Build Sphinx documentation
	$(POETRY) run sphinx-build -b html docs/ docs/_build/html

docker: ## Build Docker image
	docker build -t camt053:latest .

docker-run: ## Run Docker container
	docker run -p 8000:8000 camt053:latest

smoke: ## Run smoke tests only
	$(POETRY) run pytest tests/ -m smoke -v --no-cov

examples: ## Verify example scripts run
	$(POETRY) run python examples/reverse_ac04.py
	$(POETRY) run python examples/parse_statement.py
	$(POETRY) run python examples/services_facade.py
	$(POETRY) run python examples/validate_identifiers.py
	@rm -f reversal_ac04.xml

check: lint type-check security test examples ## Run all checks
