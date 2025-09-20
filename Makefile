SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help install test lint type-check clean build release-patch release-minor release-major release-alpha release-rc verify-release

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies using Poetry
	poetry install

test: ## Run all tests
	poetry run pytest --cov=confluence_markdown --cov-report=term-missing

lint: ## Run linting checks
	poetry run ruff check .

type-check: ## Run type checking
	poetry run mypy src

clean: ## Clean build artifacts and cache
	rm -rf dist/ build/ *.egg-info/ .coverage .pytest_cache/ .mypy_cache/ .ruff_cache/

build: ## Build the package
	poetry build

release-patch: ## Release a patch version (x.x.X)
	cz bump --increment patch

release-minor: ## Release a minor version (x.X.x)
	cz bump --increment minor

release-major: ## Release a major version (X.x.x)
	cz bump --increment major

release-alpha: ## Release an alpha pre-release
	cz bump --prerelease alpha

release-rc: ## Release a release candidate
	cz bump --prerelease rc

verify-release: ## Verify the current release tag
	git fetch --tags
	git describe --tags --always
