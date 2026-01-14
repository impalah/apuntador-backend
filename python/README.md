# Apuntador Backend - Python Implementation

FastAPI-based OAuth 2.0 proxy backend (Production-ready).

**Status**: **Production** - Fully functional, deployed in AWS Lambda

---

## Quick Start

### Option 1: VS Code Devcontainer (Recommended)

```bash
# 1. Open python/ folder in VS Code
# 2. Cmd/Ctrl + Shift + P → "Dev Containers: Reopen in Container"
# 3. Wait for container to build (first time only)

# 4. Run quick start script
./quickstart.sh

# Server starts at http://localhost:8000
```

### Option 2: Manual Setup

```bash
cd python/

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy and configure .env
cp ../.env.example .env
# Edit .env with your OAuth credentials

# Run development server
uvicorn apuntador.main:app --reload
```

---

## Available Commands

```bash
make dev              # Start development server
make test             # Run all tests
make test-unit        # Unit tests only
make test-integration # Integration tests only
make coverage         # Test coverage report
make lint             # Ruff linting
make format           # Auto-format code
make type-check       # mypy type checking
```

---

## Endpoints

### Health Check
```http
GET /health
```

### OAuth Authorization
```http
POST /oauth/authorize/{provider}
Body: {
  "redirect_uri": "your-app://callback",
  "state": "optional-state"
}
```

### OAuth Callback
```http
GET /oauth/callback/{provider}?code=AUTH_CODE&state=SIGNED_STATE
```

### Token Refresh
```http
POST /oauth/token/refresh/{provider}
Body: {"refresh_token": "..."}
```

### Token Revocation
```http
POST /oauth/token/revoke/{provider}
Body: {"token": "..."}
```

**Supported Providers**: `googledrive`, `dropbox`

---

## Configuration

Create `.env` file:

```env
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true
SECRET_KEY=your-super-secure-secret-key-min-32-chars

# CORS
ALLOWED_ORIGINS=http://localhost:3000,capacitor://localhost

# Google Drive OAuth
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/oauth/callback/googledrive

# Dropbox OAuth
DROPBOX_CLIENT_ID=your-dropbox-app-key
DROPBOX_CLIENT_SECRET=your-dropbox-secret
DROPBOX_REDIRECT_URI=http://localhost:8000/oauth/callback/dropbox
```

---

## Testing

### Run Tests
```bash
pytest tests/                  # All tests
pytest tests/unit/             # Unit tests
pytest tests/integration/      # Integration tests
pytest tests/test_pkce.py      # Specific test file
pytest -k "test_pkce"          # Tests matching pattern
```

### Coverage Report
```bash
make coverage
# Opens htmlcov/index.html
```

### Generate Test Vectors (for Rust parity)
```bash
cd ../comparison-tests/scripts/
python generate_vectors.py --module pkce
```

---

## Deployment

### Docker
```bash
docker build -t apuntador-python -f Dockerfile .
docker run -p 8000:8000 --env-file .env apuntador-python
```

### AWS Lambda
```bash
# Build Lambda image
docker build -t apuntador-lambda -f Dockerfile.lambda .

# Deploy with Terraform
cd ../iac/stacks/02.aws.lambda/
terraform apply -var-file=configuration.application.tfvars
```

---

## Project Structure

```
python/
├── src/apuntador/
│   ├── api/v1/              # API routes
│   │   ├── oauth/           # OAuth endpoints
│   │   ├── device/          # Device enrollment (mTLS)
│   │   └── health/          # Health check
│   ├── services/            # Business logic
│   │   ├── oauth_base.py    # Abstract OAuth service
│   │   └── dropbox.py       # Dropbox implementation
│   ├── infrastructure/      # Repository pattern
│   │   ├── implementations/ # AWS & Local implementations
│   │   └── repositories/    # Repository interfaces
│   ├── utils/               # Utilities
│   │   ├── pkce.py          # PKCE implementation
│   │   └── security.py      # Token signing
│   ├── middleware/          # Middleware
│   │   └── __init__.py      # TraceIDMiddleware
│   ├── config.py            # Pydantic Settings
│   └── main.py              # FastAPI app
├── tests/                   # Tests
├── pyproject.toml           # Dependencies
├── Makefile                 # Dev commands
└── .devcontainer/           # VS Code devcontainer
```

---

## Tech Stack

- **Framework**: FastAPI 0.115+
- **Config**: Pydantic Settings v2
- **HTTP Client**: httpx (async)
- **Logging**: Loguru (structured JSON)
- **AWS**: boto3
- **Lambda**: Mangum (ASGI adapter)
- **Testing**: pytest, pytest-asyncio
- **Linting**: Ruff, mypy

---

## Migration to Rust

This Python implementation is being migrated to Rust. See:
- [MIGRATION_CONTEXT.md](../docs/MIGRATION_CONTEXT.md) - Complete migration guide
- [DEVELOPMENT_WORKFLOW.md](../docs/DEVELOPMENT_WORKFLOW.md) - Dual development workflow

**Python remains in production during migration**.

---

## Troubleshooting

### Import errors
```bash
pip install -e .
```

### Port 8000 already in use
```bash
lsof -ti:8000 | xargs kill -9
# Or use different port
uvicorn apuntador.main:app --port 8001
```

### Tests failing
```bash
# Ensure in virtual environment
which python
# Should show: /workspaces/apuntador-backend/python/venv/bin/python

# Reinstall dependencies
pip install -e .
```

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [AWS Lambda Deployment](../docs/AWS_DEPLOYMENT_GUIDE.md)
- [Client Integration Guide](../CLIENT_INTEGRATION.md)
