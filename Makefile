SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help install test lint type-check clean build preflight-check release-patch release-minor release-major release-alpha release-rc verify-release

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

preflight-check: ## Check if repository is ready for release
	@echo "Running preflight checks..."
	@if [ "$$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then \
		echo "❌ Error: Not on main branch. Current branch: $$(git rev-parse --abbrev-ref HEAD)"; \
		echo "Please switch to main branch before releasing."; \
		exit 1; \
	fi
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "❌ Error: Working directory is dirty. Please commit or stash changes."; \
		git status --short; \
		exit 1; \
	fi
	@if [ -n "$$(git log origin/main..HEAD 2>/dev/null)" ]; then \
		echo "❌ Error: Local main branch is ahead of origin/main. Please push changes first."; \
		exit 1; \
	fi
	@echo "✅ Repository is ready for release"

release-patch: preflight-check ## Release a patch version (x.x.X)
	poetry run cz bump --increment patch

release-minor: preflight-check ## Release a minor version (x.X.x)
	poetry run cz bump --increment minor

release-major: preflight-check ## Release a major version (X.x.x)
	poetry run cz bump --increment major

release-alpha: preflight-check ## Release an alpha pre-release
	poetry run cz bump --prerelease alpha

release-rc: preflight-check ## Release a release candidate
	poetry run cz bump --prerelease rc

verify-release: ## Verify the current project version's tag exists
	@echo "Verifying current project version has corresponding git tag..."
	@VERSION=$$(poetry version --short); \
	TAG="v$$VERSION"; \
	echo "Current project version: $$VERSION"; \
	echo "Expected git tag: $$TAG"; \
	git fetch --tags >/dev/null 2>&1; \
	if git rev-parse "$$TAG" >/dev/null 2>&1; then \
		echo "✅ Tag $$TAG exists"; \
		git show --format="%h %s" --no-patch "$$TAG"; \
	else \
		echo "❌ Error: Tag $$TAG does not exist"; \
		echo "Available tags:"; \
		git tag --sort=-version:refname | head -5; \
		exit 1; \
	fi
