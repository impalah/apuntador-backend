# Migration Context - Python to Rust

**Archivo de contexto para agentes de IA (GitHub Copilot, Claude, etc.)**

Este documento contiene toda la información necesaria para que un agente de IA pueda continuar trabajando en la migración de Python/FastAPI a Rust/Axum.

---

## Objetivo de la Migración

Migrar el backend de OAuth 2.0 (Apuntador) de **Python/FastAPI** a **Rust/Axum** para:

1. **Performance**: 10x más rápido (PKCE: 500µs → 50µs, OAuth flow: 50ms → 5ms)
2. **Memory**: 4x menos memoria (128MB → 30MB)
3. **Cold Start**: 10x más rápido en Lambda (2s → 200ms)
4. **Type Safety**: Rust's ownership model y type system
5. **Production Ready**: Mismo nivel de features y estabilidad que Python

**Estrategia**: Incremental comparative development con parity testing (Python sigue en producción durante toda la migración).

---

## Estructura del Proyecto

```
apuntador-backend/
├── python/                      # Python/FastAPI (PRODUCCIÓN ACTUAL)
│   ├── src/apuntador/          # FastAPI app
│   │   ├── api/v1/             # API routes
│   │   │   ├── oauth/          # OAuth endpoints
│   │   │   ├── device/         # Device enrollment (mTLS)
│   │   │   └── health/         # Health check
│   │   ├── services/           # Business logic
│   │   │   ├── oauth_base.py   # Abstract OAuth service
│   │   │   └── dropbox.py      # Dropbox implementation
│   │   ├── infrastructure/     # Repository pattern
│   │   │   ├── implementations/
│   │   │   │   ├── aws/        # DynamoDB, S3, Secrets Manager
│   │   │   │   └── local/      # File-based (dev)
│   │   │   └── repositories/   # Interfaces
│   │   ├── utils/              # Utilities
│   │   │   ├── pkce.py         # PKCE implementation
│   │   │   └── security.py     # Token signing
│   │   └── middleware/         # Middleware
│   │       └── __init__.py     # TraceIDMiddleware
│   ├── tests/                  # Python tests
│   ├── pyproject.toml          # Dependencies
│   └── .devcontainer/          # Python 3.14 + uv
│
├── rust/                       # Rust/Axum (MIGRACIÓN EN PROGRESO)
│   ├── src/
│   │   ├── bin/
│   │   │   ├── server.rs       # Standalone server
│   │   │   └── lambda.rs       # AWS Lambda handler
│   │   ├── config.rs           # Settings (Pydantic-like)
│   │   ├── error.rs            # Error types
│   │   ├── core/
│   │   │   └── logging.rs      # Tracing setup
│   │   ├── middleware/
│   │   │   └── trace_id.rs     # Trace ID middleware
│   │   ├── models/
│   │   │   └── oauth.rs        # OAuth request/response
│   │   ├── routes/
│   │   │   ├── health.rs       # Health check
│   │   │   └── oauth.rs        # OAuth routes (TODO)
│   │   ├── services/
│   │   │   └── oauth.rs        # OAuth trait (TODO impl)
│   │   └── utils/
│   │       └── pkce.rs         # PKCE (100% parity)
│   ├── benches/                # Benchmarks
│   │   └── pkce.rs             # PKCE benchmarks
│   ├── Cargo.toml              # Dependencies
│   ├── Makefile                # Dev commands
│   └── .devcontainer/          # Rust 1.75+
│
├── comparison-tests/           # Parity testing infrastructure
│   ├── scenarios/              # Test vectors (JSON)
│   ├── scripts/                # Test runners (TODO)
│   └── README.md               # Testing strategy
│
├── iac/                        # Terraform (compartido)
│   └── stacks/
│       └── 02.aws.lambda/      # Lambda + API Gateway
│
└── docs/
    ├── DEVELOPMENT_WORKFLOW.md # Esta guía
    ├── MIGRATION_CONTEXT.md    # Este archivo
    └── AWS_DEPLOYMENT_GUIDE.md # Deployment
```

---

## Stack Técnico

### Python (Actual)

| Categoría | Tecnología |
|-----------|------------|
| Framework | FastAPI 0.115+ |
| ASGI Server | Uvicorn / Gunicorn |
| Config | Pydantic Settings v2 |
| HTTP Client | httpx (async) |
| Logging | Loguru (structured) |
| AWS | boto3 |
| Lambda | Mangum (ASGI adapter) |
| OAuth | Custom PKCE implementation |
| Telemetry | OpenTelemetry + AWS X-Ray |

### Rust (Migración)

| Categoría | Tecnología |
|-----------|------------|
| Framework | Axum 0.7 + Tower middleware |
| Runtime | Tokio (async) |
| Config | config + dotenvy |
| Serialization | serde + serde_json |
| Validation | validator |
| HTTP Client | reqwest 0.12 |
| Logging | tracing-subscriber (JSON) |
| AWS SDK | aws-sdk-dynamodb, aws-sdk-s3, aws-sdk-secretsmanager |
| Lambda | lambda_runtime + lambda_http |
| OAuth | oauth2 crate + custom PKCE |
| Telemetry | opentelemetry-otlp + opentelemetry-aws |
| Error Handling | thiserror + anyhow |

---

## Estado de Implementación

### Completado (100%)

#### 1. PKCE Utilities (`rust/src/utils/pkce.rs`)

**Python** (`python/src/apuntador/utils/pkce.py`):
```python
def generate_code_verifier(length: int = 128) -> str:
    return base64.urlsafe_b64encode(os.urandom(length)).decode("utf-8").rstrip("=")

def generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
```

**Rust** (`rust/src/utils/pkce.rs`):
```rust
pub fn generate_code_verifier(length: usize) -> String {
    let mut rng = rand::thread_rng();
    let random_bytes: Vec<u8> = (0..length).map(|_| rng.gen()).collect();
    general_purpose::URL_SAFE_NO_PAD.encode(&random_bytes)
}

pub fn generate_code_challenge(code_verifier: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(code_verifier.as_bytes());
    let hash = hasher.finalize();
    general_purpose::URL_SAFE_NO_PAD.encode(&hash)
}
```

**Status**: Parity achieved
- Tests: 3/3 passing
- Benchmarks: Configured
- Performance: ~10x faster than Python

#### 2. Health Check Endpoint

**Python** (`python/src/apuntador/api/v1/health/api.py`):
```python
@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="healthy", version=__version__)
```

**Rust** (`rust/src/routes/health.rs`):
```rust
async fn health() -> Json<Value> {
    Json(json!({
        "status": "healthy",
        "version": env!("CARGO_PKG_VERSION")
    }))
}
```

**Status**: Functional parity

#### 3. Infrastructure

- Repository structure
- Devcontainers (Python + Rust)
- Cargo.toml with all dependencies
- Makefile with dev commands
- Error handling (`AppError` + `IntoResponse`)
- Configuration from `.env`
- Trace ID middleware
- Structured logging (tracing)

---

### En Progreso (0-50%)

#### 1. OAuth Service Layer

**Objetivo**: Implementar `GoogleDriveOAuthService` y `DropboxOAuthService` en Rust.

**Python Pattern** (`python/src/apuntador/services/oauth_base.py`):
```python
class OAuthServiceBase(ABC):
    @abstractmethod
    def get_authorization_url(self, code_challenge: str, state: str) -> str:
        pass
    
    @abstractmethod
    async def exchange_code_for_token(self, code: str, code_verifier: str) -> dict:
        pass
```

**Rust Pattern** (`rust/src/services/oauth.rs`):
```rust
#[async_trait]
pub trait OAuthService: Send + Sync {
    fn get_authorization_url(&self, code_challenge: &str, state: &str) -> String;
    async fn exchange_code_for_token(&self, code: &str, code_verifier: &str) 
        -> anyhow::Result<serde_json::Value>;
}
```

**Next Steps**:
1. Implement `GoogleDriveOAuthService` struct
2. Implement trait methods
3. Write unit tests
4. Generate test vectors from Python
5. Run parity tests

#### 2. OAuth Endpoints

**Pendiente**:
- `POST /oauth/authorize/{provider}` - Generate authorization URL
- `GET /oauth/callback/{provider}` - Handle OAuth callback
- `POST /oauth/token/refresh/{provider}` - Refresh access token
- `POST /oauth/token/revoke/{provider}` - Revoke token

**Template** (`rust/src/routes/oauth.rs`):
```rust
async fn authorize(
    Path(provider): Path<String>,
    Json(request): Json<AuthorizeRequest>,
) -> Result<Json<AuthorizeResponse>, AppError> {
    // TODO: Implement
    todo!()
}
```

---

### Pendiente (0%)

#### 1. AWS SDK Integration

**Objetivo**: Repository pattern con DynamoDB, S3, Secrets Manager.

**Python** (`python/src/apuntador/infrastructure/implementations/aws/`):
- `certificate_repository.py` - DynamoDB for certificates
- `secrets_repository.py` - Secrets Manager for OAuth credentials
- `storage_repository.py` - S3 for file storage

**Rust**: Crear equivalentes usando `aws-sdk-*` crates.

#### 2. Device Enrollment (mTLS)

- Certificate Authority (sign CSRs)
- Certificate lifecycle (enrollment, renewal, revocation)
- Device attestation (Android SafetyNet, iOS DeviceCheck)

#### 3. Comparison Testing

- Script para generar test vectors desde Python
- Parity test runner
- CI/CD integration

#### 4. OpenTelemetry

- Configure `opentelemetry-otlp`
- AWS X-Ray integration
- Trace propagation

#### 5. Lambda Deployment

- Dockerfile optimizado para Lambda
- Terraform module updates
- CI/CD pipeline

---

## Testing Strategy

### 1. Test Vectors (Python → JSON)

**Script** (`comparison-tests/scripts/generate_vectors.py`):
```python
import json
from apuntador.utils.pkce import generate_code_verifier, generate_code_challenge

vectors = []
for i in range(100):
    verifier = generate_code_verifier(128)
    challenge = generate_code_challenge(verifier)
    vectors.append({
        "verifier": verifier,
        "challenge": challenge
    })

with open("../scenarios/pkce/test_vectors.json", "w") as f:
    json.dump(vectors, f, indent=2)
```

### 2. Parity Testing (Both implementations)

**Runner** (`comparison-tests/scripts/run_parity_tests.sh`):
```bash
#!/bin/bash
# Load test vectors
# Run Python implementation
# Run Rust implementation
# Compare outputs
# Report: PASS/FAIL
```

### 3. Benchmarking

**Rust** (Criterion):
```rust
// benches/pkce.rs
fn benchmark_code_verifier(c: &mut Criterion) {
    c.bench_function("generate_code_verifier", |b| {
        b.iter(|| generate_code_verifier(black_box(128)))
    });
}
```

**Python** (pytest-benchmark):
```python
# tests/benchmarks/test_pkce_bench.py
def test_benchmark_code_verifier(benchmark):
    benchmark(generate_code_verifier, 128)
```

---

## Patrones de Desarrollo

### 1. Error Handling

**Python**:
```python
from fastapi import HTTPException

raise HTTPException(status_code=400, detail="Invalid code_verifier")
```

**Rust**:
```rust
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};

#[derive(Error, Debug)]
pub enum AppError {
    #[error("OAuth error: {0}")]
    OAuth(String),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            AppError::OAuth(msg) => (StatusCode::BAD_REQUEST, msg),
        };
        (status, Json(json!({"error": message}))).into_response()
    }
}
```

### 2. Configuration

**Python** (Pydantic Settings):
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str
    
    class Config:
        env_file = ".env"
```

**Rust** (config + serde):
```rust
use serde::Deserialize;

#[derive(Debug, Deserialize, Clone)]
pub struct Settings {
    pub google_client_id: String,
    pub google_client_secret: String,
}

impl Settings {
    pub fn from_env() -> Result<Self, config::ConfigError> {
        dotenvy::dotenv().ok();
        config::Config::builder()
            .add_source(config::Environment::default())
            .build()?
            .try_deserialize()
    }
}
```

### 3. Async HTTP Requests

**Python** (httpx):
```python
async with httpx.AsyncClient() as client:
    response = await client.post(url, data=data)
    return response.json()
```

**Rust** (reqwest):
```rust
let client = reqwest::Client::new();
let response = client.post(url)
    .form(&data)
    .send()
    .await?;
let json = response.json::<serde_json::Value>().await?;
```

### 4. Logging

**Python** (Loguru):
```python
from loguru import logger

logger.info(f"Starting OAuth flow for provider={provider}")
```

**Rust** (tracing):
```rust
use tracing::info;

info!(provider = %provider, "Starting OAuth flow");
```

---

## Performance Targets

| Operation | Python | Rust Target | Status |
|-----------|--------|-------------|--------|
| PKCE code_verifier | ~500 µs | < 50 µs | Achieved (~30 µs) |
| PKCE code_challenge | ~100 µs | < 10 µs | Achieved (~5 µs) |
| OAuth authorize (URL gen) | ~5 ms | < 500 µs | Pending |
| OAuth callback (token exchange) | ~50 ms | < 5 ms | Pending |
| Health check | ~2 ms | < 200 µs | Achieved (~100 µs) |
| Lambda cold start | ~2000 ms | < 200 ms | Pending |
| Memory usage (idle) | ~128 MB | < 30 MB | Pending |

---

## Roadmap (14 Fases, 35-45 días)

### Phase 1: Setup (Días 1-2) - COMPLETADO
- [x] Repository reorganization
- [x] Rust project initialization
- [x] Devcontainers setup
- [x] PKCE utilities implementation
- [x] Health check endpoint
- [x] Documentation

### Phase 2: OAuth Core (Días 3-5) - SIGUIENTE
- [ ] Implement `OAuthService` trait
- [ ] Google Drive OAuth service
- [ ] Dropbox OAuth service
- [ ] Unit tests
- [ ] Test vectors generation
- [ ] Parity tests

### Phase 3: OAuth Endpoints (Días 6-8)
- [ ] `/oauth/authorize/{provider}` endpoint
- [ ] `/oauth/callback/{provider}` endpoint
- [ ] `/oauth/token/refresh/{provider}` endpoint
- [ ] `/oauth/token/revoke/{provider}` endpoint
- [ ] Integration tests

### Phase 4: AWS SDK (Días 9-12)
- [ ] Repository interfaces
- [ ] DynamoDB implementation
- [ ] S3 implementation
- [ ] Secrets Manager implementation
- [ ] Local file-based implementation (dev)

### Phase 5: Device Enrollment (Días 13-16)
- [ ] Certificate Authority
- [ ] CSR signing
- [ ] Certificate storage
- [ ] Device attestation (Android/iOS)

### Phase 6: mTLS Middleware (Días 17-19)
- [ ] Certificate validation
- [ ] Serial number whitelist check
- [ ] Error handling

### Phase 7: OpenTelemetry (Días 20-22)
- [ ] Tracing setup
- [ ] AWS X-Ray integration
- [ ] Metrics

### Phase 8: Comparison Testing (Días 23-25)
- [ ] Complete test vector suite
- [ ] Parity test runner
- [ ] Benchmarking framework

### Phase 9: Lambda Optimization (Días 26-28)
- [ ] Lambda-specific Dockerfile
- [ ] Binary size optimization
- [ ] Cold start optimization

### Phase 10: Deployment (Días 29-31)
- [ ] Terraform updates
- [ ] CI/CD pipeline
- [ ] Staging deployment

### Phase 11: Performance Testing (Días 32-34)
- [ ] Load testing (K6)
- [ ] Stress testing
- [ ] Memory profiling

### Phase 12: Security Audit (Días 35-37)
- [ ] Dependency audit (cargo-audit)
- [ ] OWASP checks
- [ ] mTLS validation

### Phase 13: Migration (Días 38-40)
- [ ] Blue/green deployment
- [ ] Traffic shifting (10% → 50% → 100%)
- [ ] Monitoring

### Phase 14: Cleanup (Días 41-45)
- [ ] Python deprecation
- [ ] Documentation updates
- [ ] Final benchmarks

---

## Cómo Usar Este Contexto

### Para GitHub Copilot

```
@MIGRATION_CONTEXT.md Implementa GoogleDriveOAuthService en Rust siguiendo el patrón de Python
```

### Para Claude/ChatGPT

```
Usa el archivo MIGRATION_CONTEXT.md como contexto completo del proyecto.

Tarea: Implementar el endpoint /oauth/authorize/{provider} en Rust.

Requisitos:
- Seguir el patrón de la implementación Python
- Usar el OAuthService trait
- Incluir validación con validator crate
- Tests unitarios
```

### Para Nuevos Desarrolladores

1. Lee este archivo completo
2. Lee `DEVELOPMENT_WORKFLOW.md` para setup
3. Revisa el código Python equivalente
4. Implementa en Rust manteniendo parity
5. Genera test vectors
6. Valida parity

---

## Referencias Clave

### Archivos Python a Replicar

1. **OAuth Base**: `python/src/apuntador/services/oauth_base.py`
2. **Google Drive**: `python/src/apuntador/infrastructure/providers/googledrive.py`
3. **Dropbox**: `python/src/apuntador/infrastructure/providers/dropbox.py`
4. **OAuth Endpoints**: `python/src/apuntador/api/v1/oauth/api.py`
5. **Certificate Authority**: `python/src/apuntador/services/certificate_authority.py`

### Archivos Rust a Completar

1. **OAuth Service**: `rust/src/services/oauth.rs` (trait definido, implementations pendientes)
2. **OAuth Routes**: `rust/src/routes/oauth.rs` (skeleton, endpoints pendientes)
3. **AWS Repositories**: `rust/src/infrastructure/` (estructura pendiente)

### Documentación Externa

- [Axum Docs](https://docs.rs/axum/)
- [AWS SDK Rust](https://docs.aws.amazon.com/sdk-for-rust/)
- [Lambda Runtime](https://github.com/awslabs/aws-lambda-rust-runtime)
- [OAuth2 Crate](https://docs.rs/oauth2/)

---

## Decisiones de Diseño

### 1. Por qué Axum sobre Actix-web?

- Tower middleware ecosystem (más compatible con AWS SDK)
- Mejor integración con tokio
- Type-safe extractors
- Más activamente mantenido
- Mejor DX con async/await

### 2. Repository Pattern

Mantenemos el mismo patrón que Python para facilitar migración:
- Interfaces abstractas (`trait`)
- Implementaciones concretas (AWS, Local)
- Factory pattern para selección

### 3. Error Handling

Usamos `thiserror` para errors del dominio + `anyhow` para propagación:
```rust
#[derive(Error, Debug)]
pub enum AppError {
    #[error("OAuth error: {0}")]
    OAuth(String),
}
```

### 4. Configuración

Preferimos `config` + `serde` sobre alternativas porque:
- Soporta múltiples sources (.env, env vars, files)
- Compatible con Pydantic Settings pattern
- Type-safe deserialization

---

## Notas Importantes

1. **NO eliminar código Python**: Python sigue en producción durante toda la migración
2. **Parity primero, optimización después**: Comportamiento idéntico es priority #1
3. **Tests son obligatorios**: No merges sin tests
4. **Documentación en paralelo**: Actualizar MIGRATION_CONTEXT.md con cada cambio significativo
5. **Performance es métrica, no bloqueante**: Parity > Performance en primera iteración

---

## Debugging Tips

### Comparar implementaciones

```bash
# Python logs
cd python/ && make dev
# Observar logs de PKCE generation

# Rust logs
cd rust/ && RUST_LOG=debug make dev
# Comparar output
```

### Test vectors manual

```python
# Python shell
from apuntador.utils.pkce import generate_code_verifier, generate_code_challenge
v = generate_code_verifier(128)
c = generate_code_challenge(v)
print(f"Verifier: {v}")
print(f"Challenge: {c}")
```

```rust
// Rust test
#[test]
fn test_specific_verifier() {
    let verifier = "PYTHON_VERIFIER_AQUI";
    let challenge = generate_code_challenge(verifier);
    assert_eq!(challenge, "PYTHON_CHALLENGE_AQUI");
}
```

---

**Última actualización**: 2026-01-13  
**Versión**: 1.0.0  
**Estado**: Phase 1 completado, Phase 2 en progreso
