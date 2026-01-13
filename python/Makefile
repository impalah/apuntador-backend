# Variables
PROFILE="pak"
DOMAIN="apuntador"
AWS_REGION="eu-west-1"
REGISTRY_URI="670089840758.dkr.ecr.eu-west-1.amazonaws.com"
REPOSITORY_NAME="backend"
PLATFORM="linux/amd64"
BUILDER_NAME="mybuilder"
PART ?= patch  # Can be overwritten with: make bump-version PART=minor


.PHONY: help install dev test lint format clean docker-build docker-run sync kill-port docker-builder-reset

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

sync: ## Sync dependencies with uv
	uv sync

install: sync ## Alias for sync (install dependencies)

kill-port: ## Kill process on port 8000
	@lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✅ Process on port 8000 terminated" || echo "⚠️  No process on port 8000"

dev: ## Run development server
	uv run uvicorn apuntador.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	uv run pytest -v

test-cov: ## Run tests with coverage report
	uv run pytest --cov --cov-report=xml --cov-report=term --cov-report=html

lint: ## Check code with ruff
	uv run ruff check .

format: ## Format code
	uv run ruff format .

typecheck: ## Check types with mypy
	uv run mypy src/apuntador/

clean: ## Clean temporary files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

env: ## Create .env file from .env.example
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env file created. Please edit the variables."; \
	else \
		echo "⚠️  .env file already exists."; \
	fi

docker-builder-reset: ## Reset Docker buildx builder
	@echo "🔧 Resetting Docker buildx builder..."
	@docker buildx rm $(BUILDER_NAME) 2>/dev/null || echo "⚠️  Builder '$(BUILDER_NAME)' not found"
	@docker buildx create --name $(BUILDER_NAME) --driver docker-container --bootstrap --use
	@echo "✅ Builder '$(BUILDER_NAME)' created and activated"


# Bump patch/minor/major version
bump-version:
	@v=$$(uvx --from=toml-cli toml get --toml-path=pyproject.toml project.version) && \
	echo "🔧 Current version: $$v" && \
	uvx --from bump2version bumpversion --allow-dirty --current-version "$$v" $(PART) pyproject.toml && \
	echo "✅ Version bumped to new $(PART)"

# Build docker image
# docker-build:
docker-build: bump-version
	@BASE_VERSION=$$(uvx --from=toml-cli toml get --toml-path=pyproject.toml project.version) && \
	echo "✅ Using version $$BASE_VERSION" && \
	echo " Logging into ECR..." && \
	aws --profile $(PROFILE) ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(REGISTRY_URI) && \
	echo "🏗️  Building image for $(PLATFORM)..." && \
	docker buildx build \
		--provenance=false \
		--progress=plain \
		--platform $(PLATFORM) \
		-t $(REGISTRY_URI)/$(DOMAIN)/$(REPOSITORY_NAME):$$BASE_VERSION \
		-f Dockerfile.lambda \
		--push \
		. && \
	echo "✅ Image built and pushed successfully!"
