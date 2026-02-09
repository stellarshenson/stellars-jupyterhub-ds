.PHONY: help install build test clean lint

VENV := .venv
PYTHON := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: $(VENV) ## Install package in editable mode with test dependencies
	uv pip install -e ".[test]" --python $(PYTHON)

$(VENV):
	uv venv $(VENV)

build: ## Build distribution package
	uv build

test: ## Run pytest test suite
	$(PYTEST) tests/ -v

clean: ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info stellars_hub.egg-info stellars_hub/*.egg-info $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

lint: ## Run basic syntax checks
	$(PYTHON) -m py_compile stellars_hub/__init__.py
	$(PYTHON) -m py_compile stellars_hub/configure.py
	$(PYTHON) -m py_compile stellars_hub/constants.py
	$(PYTHON) -m py_compile stellars_hub/handlers/__init__.py
	@echo "Syntax check passed"
