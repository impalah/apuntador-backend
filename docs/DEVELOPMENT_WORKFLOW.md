# Development Workflow - Dual Python/Rust Development

Guía práctica para trabajar con el monorepo durante la migración.

## Estructura de Devcontainers

El proyecto ofrece **3 opciones de devcontainer**:

### 1. **Raíz** (`.devcontainer/`) - RECOMENDADO para Migración ✅

**Contiene**: Python 3.14 + Rust 1.75+ + uv + cargo tools  
**Cuándo usar**: Durante la migración (necesitas ver código Python y Rust simultáneamente)  
**Ventajas**:
- Copilot ve **todo** el código
- Comparación directa Python ↔ Rust
- Tests de paridad más fáciles
- No necesitas cambiar de devcontainer

**Cómo usar**:
```bash
# 1. Abrir carpeta raíz: /workspaces/apuntador-backend
# 2. Reopen in Container
# 3. Terminal 1: cd python && make dev
# 4. Terminal 2: cd rust && make dev
```

### 2. **Python** (`python/.devcontainer/`) - Solo Python

**Contiene**: Python 3.14 + uv + AWS CLI  
**Cuándo usar**: Mantenimiento Python sin tocar Rust  
**Más ligero**: ~200MB vs ~500MB del unificado

### 3. **Rust** (`rust/.devcontainer/`) - Solo Rust

**Contiene**: Rust 1.75+ + cargo tools  
**Cuándo usar**: Desarrollo Rust avanzado (después de la migración)  
**Más ligero**: ~200MB

---

## Recomendación

**Durante la migración (ahora)**: Usa el **devcontainer de la raíz** para que GitHub Copilot tenga acceso al código Python y Rust simultáneamente.

---

## Cómo Lanzar Cada Proyecto

### Python/FastAPI (Producción Actual)

#### Opción 1: VS Code Devcontainer

```bash
# 1. Abrir la carpeta python/ en VS Code
# 2. Cmd/Ctrl + Shift + P → "Dev Containers: Reopen in Container"
# 3. Esperar a que construya (solo la primera vez)

# 4. Dentro del devcontainer:
cd /workspaces/apuntador-backend/python
make dev

# O manualmente:
uvicorn apuntador.main:app --reload --host 0.0.0.0 --port 8000
```

**URL**: http://localhost:8000  
**Docs**: http://localhost:8000/docs  
**Health**: http://localhost:8000/health

#### Opción 2: Local (sin devcontainer)

```bash
cd python/
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .

# Copiar .env.example a .env y configurar
cp ../.env.example .env
vim .env

# Lanzar
uvicorn apuntador.main:app --reload
```

#### Tests Python

```bash
cd python/
make test           # Todos los tests
make test-unit      # Solo unit tests
make test-integration  # Solo integration tests
make coverage       # Con reporte de cobertura
```

---

### Rust/Axum (Migración)

#### Opción 1: VS Code Devcontainer

```bash
# 1. Abrir la carpeta rust/ en VS Code
# 2. Cmd/Ctrl + Shift + P → "Dev Containers: Reopen in Container"
# 3. Esperar a que construya y ejecute post-create.sh

# 4. Dentro del devcontainer:
cd /workspaces/apuntador-backend/rust
make dev

# O manualmente:
cargo run --bin server
```

**URL**: http://localhost:8000  
**Health**: http://localhost:8000/health

#### Opción 2: Local (sin devcontainer)

```bash
# Instalar Rust (si no está instalado)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

cd rust/

# Copiar .env (compartido con Python)
cp ../.env.example .env
vim .env

# Compilar y lanzar
cargo run --bin server

# Con hot reload (requiere cargo-watch)
cargo install cargo-watch
cargo watch -x 'run --bin server'
```

#### Tests Rust

```bash
cd rust/
make test           # Todos los tests
make test -- --nocapture  # Con output
cargo test pkce     # Solo tests de PKCE
make bench          # Benchmarks
```

---

## Flujo de Trabajo Recomendado

### Escenario 1: Desarrollo Python (Mantenimiento)

```bash
# 1. Abrir python/ en VS Code
# 2. Reopen in Container
# 3. Desarrollar normalmente
# 4. Commit y push desde dentro del devcontainer
```

**Extensiones disponibles**:
- Python extension
- Pylance
- Ruff (linting/formatting)
- Test Explorer

### Escenario 2: Desarrollo Rust (Migración)

```bash
# 1. Abrir rust/ en VS Code
# 2. Reopen in Container
# 3. Desarrollar con rust-analyzer
# 4. Tests con make test
# 5. Commit y push
```

**Extensiones disponibles**:
- rust-analyzer
- CodeLLDB (debugging)
- crates (dependency management)
- Even Better TOML

### Escenario 3: Desarrollo Dual (Parity Testing)

**Workflow simultáneo**:

1. **Terminal 1 (Python devcontainer)**:
   ```bash
   cd python/
   uvicorn apuntador.main:app --reload --port 8000
   ```

2. **Terminal 2 (Rust devcontainer)**:
   ```bash
   cd rust/
   cargo run --bin server -- --port 8001
   ```

3. **Terminal 3 (Cualquiera)**:
   ```bash
   cd comparison-tests/
   ./scripts/run_parity_tests.sh
   ```

**Alternativa sin devcontainer**: Usar dos instancias de VS Code
- VS Code 1: `python/` con devcontainer Python
- VS Code 2: `rust/` con devcontainer Rust

---

## Reconstruir Devcontainers

### Cuándo reconstruir:

- Primera vez que abres el proyecto
- Cambios en `Dockerfile` o `devcontainer.json`
- Cambios en dependencias (`pyproject.toml` / `Cargo.toml`)
- Después de `git pull` con cambios en devcontainer

### Cómo reconstruir:

```bash
# Opción 1: Desde VS Code
Cmd/Ctrl + Shift + P → "Dev Containers: Rebuild Container"

# Opción 2: Desde terminal (limpio)
docker system prune -a  # Elimina TODOS los containers/imágenes
# Luego reabrir en container
```

### Solo actualizar dependencias (sin rebuild):

**Python**:
```bash
# Dentro del devcontainer python/
cd python/
uv pip install -e .
```

**Rust**:
```bash
# Dentro del devcontainer rust/
cd rust/
cargo update
cargo build
```

---

## Testing Workflow

### 1. Test Vector Generation (Python → JSON)

```bash
# En python/ devcontainer
cd comparison-tests/scripts/
python generate_vectors.py --module pkce --output ../scenarios/pkce/

# Genera: comparison-tests/scenarios/pkce/test_vectors.json
```

### 2. Parity Testing (Python vs Rust)

```bash
# En cualquier devcontainer o local
cd comparison-tests/
./scripts/run_parity_tests.sh --scenario pkce

# Output:
# Python: code_verifier length = 171 chars
# Rust:   code_verifier length = 171 chars
# PASS: Both implementations match
```

### 3. Performance Benchmarking

```bash
# Benchmark Rust
cd rust/
cargo bench

# Benchmark Python (pytest-benchmark)
cd python/
pytest tests/benchmarks/ --benchmark-only

# Comparación
cd comparison-tests/
./scripts/benchmark_compare.sh
```

---

## GitHub Copilot Context

### Problema: Perder contexto al cambiar devcontainer

**Solución 1: Usar archivos de contexto (@-mentions)**

En el chat de Copilot, menciona:
```
@MIGRATION_CONTEXT.md Implementa Google Drive OAuth en Rust
```

**Solución 2: Workspace instructions (ya configurado)**

El archivo `.github/copilot-instructions.md` se carga automáticamente en ambos devcontainers.

**Solución 3: Crear snippets de contexto**

```bash
# Antes de cerrar un devcontainer, crea un resumen:
cat > docs/current_work.md << 'EOF'
# Trabajo actual: OAuth Google Drive

## Completado
- [x] PKCE utilities en Rust
- [x] Health check endpoint

## En progreso
- [ ] GoogleDriveOAuthService en Rust
- [ ] Parity tests para PKCE

## Siguiente paso
Implementar `get_authorization_url()` en Rust
EOF
```

Luego en el nuevo devcontainer:
```
@current_work.md Continúa con la implementación
```

**Solución 4: Git commit messages detallados**

```bash
git commit -m "feat(rust): Implement PKCE utilities

- Added generate_code_verifier(length)
- Added generate_code_challenge(verifier) with SHA256
- All tests passing (3/3)
- Benchmarks configured

Next: Implement GoogleDriveOAuthService"
```

---

## Cheatsheet de Comandos

### Python Development

```bash
make dev              # Launch dev server
make test             # Run all tests
make test-unit        # Unit tests only
make lint             # Ruff linting
make format           # Auto-format code
make type-check       # mypy type checking
make coverage         # Test coverage report
```

### Rust Development

```bash
make dev              # Launch with hot reload
make build            # Build release binary
make test             # Run all tests
make bench            # Run benchmarks
make clippy           # Linting
make fmt              # Format code
make check            # Clippy + fmt + test
```

### Docker (Production)

```bash
# Python
cd python/
docker build -t apuntador-python -f Dockerfile .
docker run -p 8000:8000 --env-file .env apuntador-python

# Rust
cd rust/
docker build -t apuntador-rust -f Dockerfile .
docker run -p 8000:8000 --env-file .env apuntador-rust
```

---

## Troubleshooting

### Problema: "Module not found" en Python

```bash
# Dentro del devcontainer
pip install -e .
# O
make install
```

### Problema: Rust compiler error después de git pull

```bash
cargo clean
cargo build
```

### Problema: Puerto 8000 ya en uso

```bash
# Opción 1: Matar proceso
lsof -ti:8000 | xargs kill -9

# Opción 2: Usar otro puerto
cargo run --bin server -- --port 8001
uvicorn apuntador.main:app --port 8001
```

### Problema: Devcontainer no carga extensiones

```bash
# Reconstruir completamente
Cmd/Ctrl + Shift + P → "Dev Containers: Rebuild Container Without Cache"
```

---

## Tips Avanzados

### 1. Usar terminal multiplexer (tmux)

```bash
# Dentro del devcontainer
tmux new -s dev

# Panel 1: Python server
# Panel 2: Rust server
# Panel 3: Tests

# Ctrl+B, " → Split horizontal
# Ctrl+B, % → Split vertical
# Ctrl+B, arrows → Navigate
```

### 2. VS Code Multi-root Workspace

**Crear archivo `apuntador.code-workspace`**:

```json
{
  "folders": [
    { "path": "python", "name": "Python Backend" },
    { "path": "rust", "name": "Rust Backend" }
  ],
  "settings": {
    "files.exclude": {
      "**/__pycache__": true,
      "**/target": true
    }
  }
}
```

Luego: File → Open Workspace from File → `apuntador.code-workspace`

### 3. Git desde dentro de devcontainers

```bash
# Git config se hereda del host, pero verifica:
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# Branches y commits funcionan normalmente
git checkout -b feature/oauth-rust
git add .
git commit -m "feat: Add OAuth implementation"
git push origin feature/oauth-rust
```

---

## Recursos

- [Python README](../python/README.md) - Setup detallado Python
- [Rust README](../rust/README.md) - Setup detallado Rust
- [Migration Context](MIGRATION_CONTEXT.md) - Contexto completo para IA
- [Copilot Instructions](../.github/copilot-instructions.md) - Reglas de desarrollo

---

## Quick Start Checklist

**Primera vez**:
- [ ] Clonar repositorio
- [ ] Copiar `.env.example` → `python/.env` y `rust/.env`
- [ ] Configurar OAuth credentials en `.env`
- [ ] Abrir `python/` en VS Code → Reopen in Container
- [ ] Verificar: `make dev` (Python server arranca)
- [ ] Abrir `rust/` en VS Code → Reopen in Container  
- [ ] Verificar: `make dev` (Rust server arranca)

**Desarrollo diario**:
- [ ] `git pull origin main`
- [ ] Abrir carpeta correspondiente (`python/` o `rust/`)
- [ ] Reopen in Container (si no está abierto)
- [ ] `make dev` para lanzar servidor
- [ ] Desarrollar con hot reload activo
- [ ] `make test` antes de commit
- [ ] Commit y push

**Antes de PR**:
- [ ] `make test` pasa en ambos proyectos
- [ ] `make lint` y `make format` ejecutados
- [ ] Comparison tests pasan (si aplica)
- [ ] Documentación actualizada
- [ ] MIGRATION_CONTEXT.md actualizado (si aplica)
