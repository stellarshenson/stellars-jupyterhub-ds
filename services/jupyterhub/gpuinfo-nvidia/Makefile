.PHONY: help install build test image clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
IMAGE := stellars/stellars-gpuinfo-nvidia:latest
# Build context is the repo root so the Dockerfile can COPY the package by path.
REPO_ROOT := ../../..

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: $(VENV) ## Install package in editable mode with test dependencies
	uv pip install -e ".[test]" --python $(PYTHON)

$(VENV):
	uv venv $(VENV)

build: ## Build distribution package
	uv build

test: ## Run pytest test suite (subprocess mocked - no GPU required)
	$(PYTEST) tests/ -v

image: ## Build the sidecar image (context = repo root)
	docker build -f Dockerfile -t $(IMAGE) $(REPO_ROOT)

clean: ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info gpuinfo_nvidia/*.egg-info $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
