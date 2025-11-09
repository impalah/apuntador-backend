# Copilot Instructions for **Apuntador OAuth Backend**

A unified OAuth 2.0 proxy backend built with **FastAPI**, **Pydantic Settings v2**, and **Loguru** logging. Provides secure authentication for multiple cloud providers (Google Drive, Dropbox, OneDrive) using PKCE flow. **Now includes mTLS (Mutual TLS) authentication for physical devices with self-managed Certificate Authority**.

## Architecture Overview

**OAuth Proxy Pattern**: Acts as secure intermediary between client applications and OAuth providers.
- Clients (Web/Android/iOS/Desktop) → FastAPI Backend → OAuth Providers
- Backend securely stores client secrets
- Implements PKCE (Proof Key for Code Exchange) for enhanced security
- Unified REST API for all cloud providers

**Authentication Architecture**:
- **Physical Devices** (Android/iOS/Desktop): mTLS with client certificates signed by private CA
- **Web Browsers**: OAuth 2.0 + PKCE + CORS (no mTLS)
- **Certificate Authority**: Self-managed CA for device enrollment (stored in AWS Secrets Manager)
- **Certificate Lifecycle**: Short-lived certificates (7-30 days) with automatic renewal

**Multi-Provider Support**:
- **Google Drive**: Full OAuth 2.0 with offline access and refresh tokens
- **Dropbox**: OAuth with file access scopes
- **OneDrive**: Extensible architecture ready for Microsoft integration

## Key Tech Stack

- **Core**: Python 3.12+, FastAPI 0.115+, Uvicorn (ASGI server)
- **Configuration**: Pydantic Settings v2 with automatic type validation and .env support
- **Logging**: Loguru with trace ID middleware for request tracking
- **OAuth**: httpx (async HTTP client), itsdangerous (token signing), PKCE implementation
- **Validation**: Pydantic v2 for request/response models
- **Testing**: pytest with pytest-asyncio, pytest-cov for coverage
- **Linting**: Ruff (fast Python linter/formatter), mypy (type checking)
- **Deployment**: Docker, AWS Lambda (via Mangum), Gunicorn + Uvicorn workers

## Directory Structure (Actual)

```
```
apuntador-backend/
├── src/
│   └── apuntador/
│       ├── __init__.py           # Package initialization with version
│       ├── main.py               # FastAPI app entry point
│       ├── application.py        # FastAPI app factory
│       ├── lambda_main.py        # AWS Lambda handler (Mangum)
│       ├── config.py             # Pydantic Settings configuration
│       ├── openapi.py            # OpenAPI/Swagger documentation
│       ├── core/
│       │   └── logging.py        # Loguru configuration
│       ├── middleware/
│       │   ├── __init__.py       # TraceIDMiddleware for request tracking
│       │   └── mtls_validation.py  # mTLS certificate validation
│       ├── api/
│       │   └── v1/
│       │       ├── __init__.py   # API route prefixes (no /api prefix)
│       │       ├── oauth/        # OAuth 2.0 endpoints
│       │       │   ├── api.py    # authorize, callback, token, refresh, revoke
│       │       │   └── services.py  # OAuth service factory
│       │       └── device/       # Device enrollment & mTLS
│       │           ├── api.py    # enroll, renew, revoke, status, CA cert
│       │           └── attestation/  # Device attestation
│       │               ├── api.py    # android, ios, desktop attestation
│       │               └── services.py  # Attestation implementations
│       ├── models/
│       │   ├── __init__.py
│       │   ├── oauth.py          # OAuth request/response models
│       │   ├── device.py         # Device enrollment models
│       │   └── errors.py         # RFC 7807 Problem Details
│       ├── services/
│       │   ├── oauth/
│       │   │   ├── oauth_base.py      # Abstract OAuth service
│       │   │   ├── googledrive.py     # Google Drive OAuth
│       │   │   └── dropbox.py         # Dropbox OAuth
│       │   ├── certificate/
│       │   │   ├── certificate_authority.py  # CA signing
│       │   │   ├── certificate_manager.py    # Certificate lifecycle
│       │   │   └── certificate_storage.py    # DynamoDB interface
│       │   └── device_attestation/
│       │       ├── android_safetynet.py      # Android attestation
│       │       └── ios_devicecheck.py        # iOS attestation
│       ├── infrastructure/       # Repository pattern for cloud abstraction
│       │   ├── repositories/
│       │   │   ├── certificate_repository.py
│       │   │   ├── secrets_repository.py
│       │   │   └── storage_repository.py
│       │   ├── implementations/
│       │   │   ├── local/        # File-based (development)
│       │   │   └── aws/          # DynamoDB, S3, Secrets Manager
│       │   └── factory.py        # Provider selection
│       ├── utils/
│       │   ├── pkce.py           # PKCE utilities (code_verifier, code_challenge)
│       │   └── security.py       # Token signing and state generation
│       └── examples/
│           └── settings_usage.py # Configuration usage examples (English)
├── tests/
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   └── fixtures/                 # Test fixtures
├── iac/                          # Terraform infrastructure
│   ├── modules/
│   │   └── lambda/               # Reusable Lambda module
│   └── stacks/
│       └── 01.applications/
│           ├── 01.network.tf     # VPC, subnets (if needed)
│           ├── 02.domain-ssl.tf  # API Gateway, ACM, Route53
│           ├── 03.database.tf    # DynamoDB tables
│           └── 04.application.tf # Lambda function
├── docs/
│   ├── AWS_DEPLOYMENT_GUIDE.md
│   ├── CERTIFICATE_LIFECYCLE.md
│   └── INFRASTRUCTURE_ABSTRACTION.md
├── .devcontainer/                # VS Code Dev Container
│   ├── devcontainer.json         # Container configuration
│   ├── Dockerfile                # Python 3.12 + uv + AWS CLI
│   └── README.md                 # Dev container usage guide
├── .env.example                  # Environment variables template
├── pyproject.toml                # Project dependencies and tool config
├── Dockerfile                    # Standard container deployment
├── Dockerfile.lambda             # AWS Lambda deployment
├── Makefile                      # Development and deployment commands
└── README.md                     # Project overview
```

## Critical Implementation Patterns

### Configuration Management (Pydantic Settings v2)
```python
# src/apuntador/config.py
class Settings(BaseSettings):
    """Unified configuration with automatic type validation."""
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,  # Allows GOOGLE_CLIENT_ID or google_client_id
        extra="ignore"
    )
    
    # Naming convention:
    # - Python code: snake_case (google_client_id)
    # - .env file: UPPER_CASE (GOOGLE_CLIENT_ID)
    # - Pydantic converts automatically
    
    google_client_id: str = Field(description="Google OAuth client ID")
    google_client_secret: str = Field(description="Google OAuth client secret")
    
@lru_cache
def get_settings() -> Settings:
    """Cached settings instance for performance."""
    return Settings()
```

**Usage in FastAPI**:
```python
from fastapi import Depends
from apuntador.config import Settings, get_settings

@app.get("/example")
async def example(settings: Settings = Depends(get_settings)):
    # Settings injected automatically, cached via @lru_cache
    return {"client_id": settings.google_client_id}
```

### Logging with Trace IDs (Loguru + Middleware)
```python
# All requests automatically get a trace_id for tracking across logs
# src/apuntador/middleware/__init__.py
class TraceIDMiddleware:
    """Adds unique trace_id to each request for log correlation."""
    async def __call__(self, request: Request, call_next):
        trace_id = generate_ksuid()  # Time-sortable unique ID
        request.state.trace_id = trace_id
        
        # All logger calls within this request include trace_id automatically
        logger.info(f"Request started: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"Request completed: status={response.status_code}")
```

**Log output format**:
```
2025-01-15 10:23:45.123 | INFO | trace_id=2ZkABC123 | oauth.py:45 | Starting OAuth authorization for provider=googledrive
```

### OAuth Service Architecture (Abstract Base + Implementations)
```python
# src/apuntador/services/oauth_base.py
class OAuthServiceBase(ABC):
    """Abstract base class defining OAuth 2.0 contract."""
    
    @abstractmethod
    def get_authorization_url(self, code_challenge: str, state: str) -> str:
        """Generate provider-specific authorization URL."""
        pass
    
    @abstractmethod
    async def exchange_code_for_token(self, code: str, code_verifier: str) -> dict:
        """Exchange authorization code for access/refresh tokens."""
        pass

# src/apuntador/services/googledrive.py
class GoogleDriveOAuthService(OAuthServiceBase):
    """Google Drive OAuth implementation with offline access."""
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    
    def get_authorization_url(self, code_challenge: str, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",  # Critical for refresh token
            "prompt": "consent"
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"
```

### PKCE Implementation (OAuth Security)
```python
# src/apuntador/utils/pkce.py
def generate_code_verifier(length: int = 128) -> str:
    """Generate cryptographically secure random string (43-128 chars)."""
    return base64.urlsafe_b64encode(os.urandom(length)).decode("utf-8").rstrip("=")

def generate_code_challenge(code_verifier: str) -> str:
    """SHA256 hash of code_verifier, base64url encoded."""
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

def verify_code_challenge(code_verifier: str, code_challenge: str) -> bool:
    """Verify code_challenge matches code_verifier."""
    return generate_code_challenge(code_verifier) == code_challenge
```

### OAuth Flow Endpoints
```python
# src/apuntador/v1/oauth/api.py
@router.post("/authorize/{provider}")
async def authorize(provider: str, request: OAuthAuthorizeRequest):
    """
    Step 1: Generate authorization URL with PKCE challenge.
    Client receives URL and opens in browser for user consent.
    """
    service = get_oauth_service(provider, settings)
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = generate_state()
    
    auth_url = service.get_authorization_url(code_challenge, state)
    signed_data = sign_data({"code_verifier": code_verifier, "state": state})
    
    return {"authorization_url": auth_url, "state": signed_data}

@router.get("/callback/{provider}")
async def callback(provider: str, code: str, state: str):
    """
    Step 2: OAuth provider redirects here with authorization code.
    Exchange code for access/refresh tokens.
    """
    service = get_oauth_service(provider, settings)
    verified_data = verify_signed_data(state)
    code_verifier = verified_data["code_verifier"]
    
    tokens = await service.exchange_code_for_token(code, code_verifier)
    return tokens  # {access_token, refresh_token, expires_in, ...}

@router.post("/token/refresh/{provider}")
async def refresh_token(provider: str, refresh_token: str):
    """Step 3: Refresh expired access token using refresh token."""
    service = get_oauth_service(provider, settings)
    new_tokens = await service.refresh_access_token(refresh_token)
    return new_tokens
```

## Development Workflow

**Core Commands** (via Makefile):
```bash
make install        # Install dependencies with uv (or pip)
make dev            # Start development server with auto-reload
make test           # Run pytest with coverage
make lint           # Run ruff linter and formatter
make typecheck      # Run mypy type checking
make format         # Auto-format code with ruff
make clean          # Remove cache and build artifacts
```

**Manual Commands**:
```bash
# Development server
uvicorn apuntador.main:app --reload --host 0.0.0.0 --port 8000

# Production server (Gunicorn + Uvicorn workers)
gunicorn apuntador.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000

# Run tests with coverage
pytest --cov=src/apuntador --cov-report=html --cov-report=term

# Type checking
mypy src/apuntador

# Linting and formatting
ruff check src/  # Check for issues
ruff format src/ # Auto-format code
```

## Testing Strategy

**Unit Tests** (pytest):
- **PKCE utilities**: Verify code_verifier/code_challenge generation and validation
- **Security utilities**: Test state generation and token signing/verification
- **Configuration**: Validate Pydantic Settings with mock environment variables
- **OAuth services**: Mock httpx responses to test token exchange logic

**Integration Tests**:
- **OAuth flow**: Test full authorize → callback → token → refresh sequence
- **Middleware**: Verify trace_id propagation through request lifecycle
- **Error handling**: Test invalid codes, expired tokens, malformed requests

**Coverage Requirements**:
- Core utilities (pkce.py, security.py): **≥ 90%**
- Services (oauth_base.py, googledrive.py, dropbox.py): **≥ 85%**
- Routers (oauth.py): **≥ 80%**
- Overall project: **≥ 80%**

## Coding Conventions

- **Type hints required**: All functions must have parameter and return type annotations
- **Docstrings**: Google-style format with Args, Returns, Raises sections
- **Naming conventions**:
  - Python code: `snake_case` for functions/variables, `PascalCase` for classes
  - .env variables: `UPPER_CASE` with underscores
  - Private methods: `_leading_underscore`
- **Async/await**: Use for all I/O operations (HTTP requests, database queries)
- **Error handling**: Raise HTTPException with appropriate status codes
- **Logging**: Use `logger.info/warning/error` with structured context

**Example function**:
```python
async def exchange_code_for_token(
    self,
    code: str,
    code_verifier: str,
) -> dict[str, any]:
    """
    Exchanges authorization code for access and refresh tokens.
    
    Args:
        code: Authorization code from OAuth provider callback
        code_verifier: PKCE code verifier (128-char random string)
    
    Returns:
        Dictionary containing:
        - access_token: OAuth access token
        - refresh_token: OAuth refresh token (if offline access granted)
        - expires_in: Token expiration in seconds
        - token_type: Usually "Bearer"
    
    Raises:
        HTTPException: If token exchange fails (400/401/500)
    """
    data = {
        "client_id": self.client_id,
        "code": code,
        "code_verifier": code_verifier,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()
```

## Environment Variables (`.env`)

**Required Variables**:
```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
SECRET_KEY=your-super-secure-secret-key-min-32-chars

# CORS - Comma-separated allowed origins
ALLOWED_ORIGINS=http://localhost:3000,capacitor://localhost,tauri://localhost

# Google Drive OAuth
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret-here
GOOGLE_REDIRECT_URI=https://apuntador.ngrok.app/oauth/callback/googledrive

# Dropbox OAuth
DROPBOX_CLIENT_ID=your-dropbox-app-key
DROPBOX_CLIENT_SECRET=your-dropbox-app-secret
DROPBOX_REDIRECT_URI=https://apuntador.ngrok.app/oauth/callback/dropbox
```

**Optional Variables**:
```env
# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=human                  # human or json
ENABLE_REQUEST_LOGGING=true       # Log all HTTP requests

# OneDrive OAuth (not yet implemented)
ONEDRIVE_CLIENT_ID=your-client-id
ONEDRIVE_CLIENT_SECRET=your-client-secret
ONEDRIVE_REDIRECT_URI=https://apuntador.ngrok.app/oauth/callback/onedrive
```

## API Endpoints Reference

### Health Check
```http
GET /health
Response: {"status": "healthy", "version": "1.0.0"}
```

### OAuth Authorization
```http
POST /oauth/authorize/{provider}
Body: {
  "redirect_uri": "your-app-callback-url",
  "state": "optional-client-state"
}
Response: {
  "authorization_url": "https://provider.com/oauth/authorize?...",
  "state": "signed-backend-state-token"
}
```

### OAuth Callback
```http
GET /oauth/callback/{provider}?code=AUTH_CODE&state=SIGNED_STATE
Response: {
  "access_token": "ya29.a0AfB_...",
  "refresh_token": "1//0gZ8k...",
  "expires_in": 3599,
  "token_type": "Bearer"
}
```

### Token Refresh
```http
POST /oauth/token/refresh/{provider}
Body: {"refresh_token": "1//0gZ8k..."}
Response: {
  "access_token": "ya29.a0AfB_...",
  "expires_in": 3599,
  "token_type": "Bearer"
}
```

### Token Revocation
```http
POST /oauth/token/revoke/{provider}
Body: {"token": "ya29.a0AfB_..."}
Response: {"success": true}
```

## Deployment Options

### Docker
```bash
# Build image
docker build -t apuntador-backend .

# Run container
docker run -p 8000:8000 --env-file .env apuntador-backend
```

### AWS Lambda (via Mangum)
```python
# src/apuntador/main.py already configured
from mangum import Mangum
handler = Mangum(app)  # Lambda handler

# Deploy using Dockerfile.lambda or SAM/Serverless framework
```

### Production (Gunicorn + Uvicorn)
```bash
# Install production dependencies
pip install gunicorn

# Run with 4 workers
gunicorn apuntador.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## Security Best Practices

1. **Never commit `.env` file**: Always use `.env.example` as template
2. **Rotate SECRET_KEY regularly**: Used for signing state tokens
3. **Use HTTPS in production**: Required for OAuth redirect URIs
4. **Validate redirect_uri**: Ensure client redirect URIs match registered ones
5. **Store refresh tokens securely**: Never log or expose in responses
6. **Implement rate limiting**: Protect OAuth endpoints from abuse
7. **CORS configuration**: Restrict allowed origins in production
8. **PKCE always enabled**: Never skip code_challenge/code_verifier validation

## Common Pitfalls & Solutions

### Issue: "Token expired" errors
**Solution**: Implement automatic token refresh on 401 responses in client

### Issue: "Invalid code_verifier" from OAuth provider
**Solution**: Ensure code_verifier is stored securely between authorize and callback steps (signed state token pattern)

### Issue: CORS errors from browser clients
**Solution**: Add client origin to `ALLOWED_ORIGINS` environment variable

### Issue: Missing refresh_token in Google OAuth response
**Solution**: Set `access_type=offline` and `prompt=consent` in authorization URL

### Issue: Pydantic validation errors for configuration
**Solution**: Check `.env` variable names match Python field names (case-insensitive but must match after conversion)

## Key Files to Reference

- `src/apuntador/config.py` - Configuration patterns with Pydantic Settings v2
- `src/apuntador/v1/oauth/api.py` - OAuth endpoint implementation
- `src/apuntador/services/oauth/oauth_base.py` - Abstract base class for new providers
- `src/apuntador/utils/pkce.py` - PKCE implementation reference
- `src/apuntador/middleware/__init__.py` - Trace ID middleware pattern
- `src/apuntador/middleware/mtls_validation.py` - mTLS certificate validation
- `docs/AWS_DEPLOYMENT_GUIDE.md` - AWS Lambda deployment guide
- `docs/CERTIFICATE_LIFECYCLE.md` - Certificate enrollment, renewal, revocation
- `docs/INFRASTRUCTURE_ABSTRACTION.md` - Repository pattern for cloud providers
- `CLIENT_INTEGRATION.md` - Client-side integration instructions

## Infrastructure Abstraction Pattern

All cloud-specific operations are abstracted behind repository interfaces to enable migration between providers (AWS ↔ Azure ↔ Local):

```python
# src/apuntador/infrastructure/repositories/certificate_repository.py
class CertificateRepository(ABC):
    """Abstract interface for certificate storage."""
    
    @abstractmethod
    async def save_certificate(self, device_id: str, certificate: Certificate) -> None:
        pass
    
    @abstractmethod
    async def get_certificate(self, device_id: str) -> Optional[Certificate]:
        pass
    
    @abstractmethod
    async def is_serial_whitelisted(self, serial: str) -> bool:
        pass

# Implementations:
# - src/apuntador/infrastructure/implementations/local/ (development)
# - src/apuntador/infrastructure/implementations/aws/ (production)
# - src/apuntador/infrastructure/implementations/azure/ (future)

# Factory selection via environment variable:
# INFRASTRUCTURE_PROVIDER=local|aws|azure
```

## mTLS Device Enrollment Flow

```python
# src/apuntador/v1/device/api.py
@router.post("/enroll")
async def enroll_device(request: EnrollmentRequest):
    """
    Enrolls a device by signing its CSR.
    
    Flow:
    1. Client generates key pair (in HSM if mobile)
    2. Client creates CSR with public key
    3. Backend validates device attestation (SafetyNet/DeviceCheck)
    4. Backend signs CSR with private CA
    5. Backend stores certificate serial in whitelist
    6. Client receives signed certificate (valid 7-30 days)
    """
    ca = CertificateAuthority()
    certificate = ca.sign_csr(
        csr=parse_csr(request.csr),
        device_id=request.device_id,
        platform=request.platform,
        validity_days=30  # Configurable per platform
    )
    
    await certificate_repo.save_certificate(request.device_id, certificate)
    return EnrollmentResponse(certificate=certificate, serial=certificate.serial_number)
```

## Adding a New OAuth Provider

1. **Create service class** in `src/apuntador/services/oauth/`:
```python
# src/apuntador/services/oauth/onedrive.py
class OneDriveOAuthService(OAuthServiceBase):
    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    
    @property
    def provider_name(self) -> str:
        return "onedrive"
    
    @property
    def scopes(self) -> list[str]:
        return ["Files.ReadWrite", "offline_access"]
    
    # Implement all abstract methods from OAuthServiceBase
```

2. **Add configuration** to `src/apuntador/config.py`:
```python
onedrive_client_id: str = Field(description="OneDrive OAuth client ID")
onedrive_client_secret: str = Field(description="OneDrive OAuth client secret")
onedrive_redirect_uri: str = Field(description="OneDrive OAuth redirect URI")
```

3. **Register in service factory** (`src/apuntador/v1/oauth/services.py`):
```python
def get_oauth_service(provider: str, settings: Settings) -> OAuthServiceBase:
    services = {
        "googledrive": GoogleDriveOAuthService(...),
        "dropbox": DropboxOAuthService(...),
        "onedrive": OneDriveOAuthService(...)  # Add here
    }
    return services[provider]
```

4. **Add tests** in `tests/test_onedrive.py`

5. **Update documentation** in `README.md` and `CLIENT_INTEGRATION.md`

---

## Development Workflow for mTLS Features

When implementing mTLS-related features:

1. **Always use infrastructure abstraction**: Never directly import `boto3` or Azure SDKs
2. **Test locally first**: Use local file-based implementations before AWS
3. **Certificate validity**: Default to short-lived (7-30 days) with auto-renewal
4. **Security**: CA private key ONLY in Secrets Manager, never in code/logs
5. **Platform detection**: Use certificate CN to determine platform (android/ios/desktop)
6. **Error handling**: Graceful degradation when attestation fails

**Local Development Setup**:
```bash
# Generate local CA
./scripts/setup-ca.sh --local

# Start with local infrastructure
export INFRASTRUCTURE_PROVIDER=local
export SECRETS_PROVIDER=local
export CERTIFICATE_DB_PROVIDER=local

# Run backend
uv run uvicorn apuntador.main:app --reload
```

---

When modifying this codebase, maintain the established patterns: Pydantic Settings for configuration, Loguru for logging with trace IDs, abstract base classes for OAuth services, infrastructure abstraction for cloud services, and comprehensive Google-style docstrings. Always run tests and type checking before committing.
