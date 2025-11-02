.PHONY: help install dev test lint format clean docker-build docker-run sync kill-port

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

docker-build: ## Build Docker image
	docker build -t apuntador-backend .

docker-run: ## Run Docker container
	docker run -p 8000:8000 --env-file .env apuntador-backend

env: ## Create .env file from .env.example
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env file created. Please edit the variables."; \
	else \
		echo "⚠️  .env file already exists."; \
	fi
