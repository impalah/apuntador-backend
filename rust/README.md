# Apuntador Backend - Rust Implementation

Rust/Axum implementation of the Apuntador OAuth 2.0 proxy backend.

**Status**: **Migration in Progress** - Incremental migration from Python/FastAPI.

## Tech Stack

- **Web Framework**: Axum 0.7 + Tower middleware
- **Runtime**: Tokio (async)
- **Serialization**: serde + validator
- **HTTP Client**: reqwest
- **Logging**: tracing-subscriber (structured JSON logs)
- **AWS SDK**: aws-sdk-dynamodb, aws-sdk-s3, aws-sdk-secretsmanager
- **Lambda**: lambda_runtime + lambda_http
- **OAuth**: oauth2 crate + custom PKCE implementation

## Quick Start

### Prerequisites

- Rust 1.75+ (`rustup` installed)
- Docker (for devcontainer)

### Development (Local)

```bash
# Build project
make build

# Run tests
make test

# Run server with hot reload
make dev

# Run benchmarks
make bench

# Format and check
make fmt-fix
make check
```

### Development (VS Code Devcontainer)

1. Open `rust/` folder in VS Code
2. Click "Reopen in Container" when prompted
3. Wait for container build and post-create scripts
4. Run `make dev`

The devcontainer includes:
- Rust 1.75+ with all components
- rust-analyzer extension
- cargo-watch, cargo-edit, cargo-audit
- All dependencies pre-fetched

## Project Structure

```
src/
├── lib.rs              # Library root
├── bin/
│   ├── server.rs       # Standalone server binary
│   └── lambda.rs       # AWS Lambda handler
├── config.rs           # Pydantic-like settings
├── error.rs            # Error types with IntoResponse
├── core/
│   └── logging.rs      # Tracing setup
├── middleware/
│   └── trace_id.rs     # Request trace ID middleware
├── models/
│   └── oauth.rs        # Request/response models
├── routes/
│   ├── health.rs       # Health check endpoint
│   └── oauth.rs        # OAuth endpoints (TODO)
├── services/
│   └── oauth.rs        # OAuth service trait
└── utils/
    └── pkce.rs         # PKCE code_verifier/code_challenge

benches/
└── pkce.rs             # PKCE benchmarks
```

## Configuration

Create `.env` file in `rust/`:

```env
HOST=0.0.0.0
PORT=8000
DEBUG=true
SECRET_KEY=your-secret-key

ALLOWED_ORIGINS=http://localhost:3000,capacitor://localhost

GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/oauth/callback/googledrive

DROPBOX_CLIENT_ID=...
DROPBOX_CLIENT_SECRET=...
DROPBOX_REDIRECT_URI=http://localhost:8000/oauth/callback/dropbox
```

## Running

### Standalone Server

```bash
cargo run --bin server
# Server listening on http://0.0.0.0:8000
```

### AWS Lambda (local testing)

```bash
cargo build --bin lambda --release --profile lambda
# Use AWS SAM or Lambda emulator to test
```

## Testing

```bash
# Run all tests
cargo test

# Run with output
cargo test -- --nocapture

# Run specific test
cargo test test_generate_code_verifier

# Run benchmarks
cargo bench
```

## Current Implementation Status

### Completed

- [x] Project structure and Cargo configuration
- [x] Error handling with Axum IntoResponse
- [x] Configuration management (Settings from .env)
- [x] Structured logging with tracing
- [x] Trace ID middleware
- [x] Health check endpoint
- [x] PKCE utilities (code_verifier, code_challenge)
- [x] OAuth request/response models
- [x] Benchmarking setup

### In Progress

- [ ] OAuth service implementations (Google Drive, Dropbox)
- [ ] OAuth endpoints (authorize, callback, refresh)
- [ ] AWS SDK integration (DynamoDB, S3, Secrets Manager)
- [ ] Lambda runtime adapter

### Planned

- [ ] Device enrollment (mTLS)
- [ ] Certificate management
- [ ] Device attestation (Android SafetyNet, iOS DeviceCheck)
- [ ] OpenTelemetry integration
- [ ] Production Dockerfile
- [ ] Lambda deployment pipeline

## Migration Strategy

We are using **comparative development** with test vectors:

1. **Generate test vectors** from Python implementation
2. **Implement feature** in Rust
3. **Run parity tests** (both implementations produce identical output)
4. **Benchmark** and compare performance
5. **Deploy** Rust when parity is achieved

See [Comparison Tests](../comparison-tests/README.md) for test vector generation.

## Performance Targets

Based on initial benchmarks:

| Operation | Python (FastAPI) | Rust (Axum) Target | Improvement |
|-----------|------------------|---------------------|-------------|
| PKCE generation | ~500 µs | < 50 µs | **10x faster** |
| OAuth flow | ~50 ms | < 5 ms | **10x faster** |
| Cold start (Lambda) | ~2s | < 200ms | **10x faster** |
| Memory usage | ~128 MB | < 30 MB | **4x reduction** |

## Deployment

### Docker

```bash
docker build -t apuntador-rust -f Dockerfile .
docker run -p 8000:8000 --env-file .env apuntador-rust
```

### AWS Lambda

```bash
# Build for Lambda
cargo build --bin lambda --release --target x86_64-unknown-linux-musl --profile lambda

# Deploy via Terraform (from repository root)
cd ../iac/stacks/02.aws.lambda
terraform apply
```

## Contributing

This is part of an active migration project. Key principles:

- **Maintain parity**: Rust behavior must match Python exactly
- **Type safety**: Leverage Rust's type system for correctness
- **Performance**: Optimize for speed and memory efficiency
- **Documentation**: All public APIs must have doc comments
- **Testing**: Unit tests + integration tests + benchmarks

## Resources

- [Axum Documentation](https://docs.rs/axum/)
- [Tokio Runtime](https://tokio.rs/)
- [AWS SDK for Rust](https://aws.amazon.com/sdk-for-rust/)
- [Lambda Runtime](https://github.com/awslabs/aws-lambda-rust-runtime)

## License

Same as parent repository - see [LICENSE](../LICENSE).
