# Dev Container Configuration

This directory contains the configuration for VS Code Dev Containers, allowing you to develop the Apuntador Backend in a consistent, reproducible environment.

## What's Included

- **Python 3.12**: Latest Python version
- **uv**: Fast Python package installer and resolver
- **AWS CLI v2**: For managing AWS resources (Secrets Manager, DynamoDB, etc.)
- **jq**: JSON processor for testing API responses
- **VS Code Extensions**:
  - Python (with Pylance)
  - Ruff (linting and formatting)
  - Mypy (type checking)
  - Docker support
  - TOML/YAML language support

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [VS Code](https://code.visualstudio.com/)
- [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## Quick Start

1. Open VS Code
2. Open the command palette (Cmd/Ctrl + Shift + P)
3. Select **"Dev Containers: Reopen in Container"**
4. Wait for the container to build and dependencies to install

The `postCreateCommand` automatically:
- Creates a virtual environment (`.venv`)
- Installs all dependencies via `uv sync`

## Features

### Port Forwarding

Port **8000** is automatically forwarded for the FastAPI backend. Start the server with:

```bash
make dev
# or
uvicorn apuntador.main:app --reload --host 0.0.0.0 --port 8000
```

### AWS Credentials

Your local AWS credentials, Git config, and SSH keys are mounted into the container:
- `~/.aws` → `/home/vscode/.aws`
- `~/.gitconfig` → `/home/vscode/.gitconfig`
- `~/.ssh` → `/home/vscode/.ssh`

### Python Tools

All tools are pre-configured:
- **Pytest**: Run tests with `pytest` or use VS Code Test Explorer
- **Ruff**: Auto-format on save, organize imports
- **Mypy**: Type checking from virtual environment

## Common Tasks

```bash
# Install dependencies
uv sync

# Run development server
make dev

# Run tests
pytest

# Lint and format
ruff check .
ruff format .

# Type checking
mypy src/apuntador

# Build Docker image
make docker-build

# Deploy to AWS
cd iac/stacks/01.applications
terraform apply -var-file=configuration.application.tfvars
```

## Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```bash
cp .env.example .env
# Edit .env with your credentials
```

## Troubleshooting

### Container won't start

```bash
# Rebuild without cache
docker compose -f .devcontainer/docker-compose.yml build --no-cache
```

### Dependencies not installing

```bash
# Inside container
uv sync --reinstall
```

### AWS credentials not working

Check that `~/.aws/credentials` exists and has valid credentials:

```bash
aws sts get-caller-identity
```

## Architecture Detection

The Dockerfile automatically detects your CPU architecture (x86_64 or ARM64) and installs the correct AWS CLI version.

## Extensions Installed

- `ms-python.python` - Python language support
- `ms-python.vscode-pylance` - Fast Python language server
- `charliermarsh.ruff` - Python linter and formatter
- `ms-python.mypy-type-checker` - Static type checker
- `tamasfe.even-better-toml` - TOML language support
- `redhat.vscode-yaml` - YAML language support
- `ms-azuretools.vscode-docker` - Docker support
