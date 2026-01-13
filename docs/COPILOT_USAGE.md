# GitHub Copilot - Guía de Uso con Archivos de Contexto

Esta guía te muestra cómo recuperar y mantener el contexto durante la migración usando GitHub Copilot.

---

## 🎯 Archivos de Contexto Disponibles

### 1. **MIGRATION_CONTEXT.md** - Contexto Completo para IA
- Roadmap completo (14 fases, 35-45 días)
- Comparación Python ↔ Rust con ejemplos de código
- Estado actual de implementación
- Patrones de diseño y decisiones técnicas
- Performance targets y benchmarks

**Cuándo usar**: Al empezar a trabajar en una nueva funcionalidad o después de cambiar de devcontainer.

### 2. **DEVELOPMENT_WORKFLOW.md** - Guía de Desarrollo Diario
- Cómo lanzar proyectos Python/Rust
- Workflow de testing y parity validation
- Comandos disponibles (Makefile)
- Troubleshooting común

**Cuándo usar**: Para recordar comandos o flujos de trabajo específicos.

### 3. **copilot-instructions.md** - Reglas de Desarrollo
- Convenciones de código
- Patrones establecidos
- Archivos clave de referencia

**Cuándo usar**: Se carga automáticamente, pero puedes mencionarlo para recordar convenciones.

---

## 💬 Cómo Usar @-Mentions en GitHub Copilot Chat

### Sintaxis Básica

```
@ARCHIVO.md Tu pregunta o solicitud aquí
```

### Ejemplos Prácticos

#### 1. Continuar después de cambiar devcontainer

```
@MIGRATION_CONTEXT.md Estoy en el devcontainer de Rust. 
¿Cuál es el siguiente paso en la migración? 
Estaba implementando PKCE utilities.
```

**Copilot responderá con**:
- Estado actual de PKCE (✅ completado)
- Siguiente tarea: OAuth Service implementations
- Código de referencia Python
- Patrón a seguir en Rust

#### 2. Implementar nueva funcionalidad

```
@MIGRATION_CONTEXT.md Implementa GoogleDriveOAuthService en Rust.

Requisitos:
- Seguir el patrón de python/src/apuntador/infrastructure/providers/googledrive.py
- Usar el trait OAuthService
- Incluir tests unitarios
```

#### 3. Recordar comandos

```
@DEVELOPMENT_WORKFLOW.md ¿Cómo lanzo ambos servidores (Python y Rust) 
simultáneamente para hacer parity testing?
```

#### 4. Debugging con contexto

```
@MIGRATION_CONTEXT.md El test de PKCE está fallando en Rust. 
El challenge generado no coincide con Python.

Error:
assertion failed: challenge == expected
  left: "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
 right: "47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU"
```

**Copilot analizará**:
- Implementación Python de `generate_code_challenge()`
- Implementación Rust
- Detectará diferencia: base64 estándar vs base64url (sin padding)

#### 5. Generar test vectors

```
@MIGRATION_CONTEXT.md Crea un script Python que genere test vectors 
para PKCE (100 casos) y los guarde en JSON para usar en Rust tests.
```

---

## 🔄 Workflow Completo de Desarrollo

### Escenario: Implementar OAuth Endpoints en Rust

#### Paso 1: Cargar contexto completo

```
@MIGRATION_CONTEXT.md Voy a implementar el endpoint POST /oauth/authorize/{provider} 
en Rust. Dame un resumen de:
- Implementación actual en Python
- Estructura que debo seguir en Rust
- Tests que debo escribir
```

#### Paso 2: Implementación guiada

```
@MIGRATION_CONTEXT.md Implementa authorize endpoint siguiendo el patrón Python.

Archivos de referencia:
- python/src/apuntador/api/v1/oauth/api.py
- rust/src/routes/oauth.rs (skeleton existente)

Incluye:
- Validación con validator crate
- Error handling con AppError
- Tests unitarios
```

#### Paso 3: Verificar parity

```
@DEVELOPMENT_WORKFLOW.md ¿Cómo genero test vectors desde Python 
y los valido en Rust para este endpoint?
```

#### Paso 4: Recordar siguiente paso

Antes de cerrar sesión, crea una nota:

```bash
cat > docs/current_work.md << 'EOF'
# Trabajo actual

## Completado hoy (2026-01-13)
- [x] OAuth authorize endpoint en Rust
- [x] Tests unitarios
- [x] Parity validation

## Siguiente sesión
- [ ] OAuth callback endpoint
- [ ] Generar test vectors para callback
- [ ] Integration tests

## Notas
- El endpoint authorize funciona, pero falta validar edge cases
- Pendiente: agregar test para CORS headers
EOF

git add docs/current_work.md
git commit -m "docs: Update current work progress"
```

#### Paso 5: Recuperar contexto en nueva sesión

```
@current_work.md @MIGRATION_CONTEXT.md Continúa con el desarrollo. 
¿Qué estaba haciendo y cuál es el siguiente paso?
```

---

## 🎓 Tips Avanzados

### 1. Combinar Múltiples Archivos

```
@MIGRATION_CONTEXT.md @python/src/apuntador/api/v1/oauth/api.py 
Implementa el mismo comportamiento en Rust manteniendo 100% de parity.
```

### 2. Comparación Directa

```
@python/src/apuntador/utils/pkce.py @rust/src/utils/pkce.rs 
Verifica que estas implementaciones sean equivalentes. 
Encuentra cualquier diferencia de comportamiento.
```

### 3. Debugging Específico

```
@MIGRATION_CONTEXT.md Mi código Rust compila pero los benchmarks 
muestran que es MÁS LENTO que Python (200µs vs 50µs para PKCE).

Código Rust actual:
[pega tu código]

¿Qué estoy haciendo mal?
```

### 4. Generar Tests

```
@python/tests/test_pkce.py Genera tests equivalentes en Rust 
usando el framework de testing de Rust. Mantén la misma cobertura.
```

### 5. Actualizar Documentación

```
@MIGRATION_CONTEXT.md Acabo de completar OAuth endpoints en Rust. 
Actualiza la sección "Estado de Implementación" para reflejar esto.
```

---

## 📋 Checklist de Contexto

Antes de empezar cada sesión:

```
- [ ] Hice git pull origin main
- [ ] Leí docs/current_work.md (si existe)
- [ ] Mencioné @MIGRATION_CONTEXT.md en Copilot Chat
- [ ] Confirmé en qué devcontainer estoy (Python o Rust)
- [ ] Revisé el roadmap (Phase actual)
```

Antes de terminar cada sesión:

```
- [ ] Actualicé docs/current_work.md con progreso
- [ ] Hice commit de cambios
- [ ] Actualicé MIGRATION_CONTEXT.md si completé una fase
- [ ] Dejé nota de siguiente paso en commit message
```

---

## 🔗 Atajos de Contexto Rápido

Crea estos snippets en `.vscode/copilot-snippets.json`:

```json
{
  "Continue Migration": {
    "prefix": "@continue",
    "body": [
      "@MIGRATION_CONTEXT.md @current_work.md",
      "Estoy en el devcontainer de ${1:Python/Rust}.",
      "Continúa con la implementación del siguiente paso."
    ]
  },
  "Implement Feature": {
    "prefix": "@implement",
    "body": [
      "@MIGRATION_CONTEXT.md",
      "Implementa ${1:feature_name} en Rust.",
      "",
      "Referencia Python:",
      "- ${2:python/file/path.py}",
      "",
      "Requisitos:",
      "- Parity con Python",
      "- Tests unitarios",
      "- ${3:additional_requirements}"
    ]
  },
  "Debug Issue": {
    "prefix": "@debug",
    "body": [
      "@MIGRATION_CONTEXT.md",
      "Tengo el siguiente error:",
      "",
      "${1:error_message}",
      "",
      "Código afectado:",
      "${2:code_snippet}",
      "",
      "¿Cómo lo soluciono manteniendo parity con Python?"
    ]
  }
}
```

---

## 🆘 Troubleshooting

### "Copilot no recuerda conversaciones anteriores"

**Solución**: Usa archivos de contexto con @-mentions
```
@MIGRATION_CONTEXT.md Antes estábamos hablando de OAuth. Continúa.
```

### "Respuestas genéricas sin contexto del proyecto"

**Solución**: Siempre menciona archivos de contexto
```
@MIGRATION_CONTEXT.md @copilot-instructions.md 
[tu pregunta aquí]
```

### "No sé en qué estaba trabajando"

**Solución 1**: Lee el último commit
```bash
git log -1 --pretty=format:"%B"
```

**Solución 2**: Usa current_work.md
```
@current_work.md ¿En qué estaba trabajando?
```

### "Copilot sugiere código que no sigue convenciones"

**Solución**: Recuerda las convenciones
```
@copilot-instructions.md Regenera el código anterior 
siguiendo las convenciones del proyecto.
```

---

## 📚 Recursos

- [GitHub Copilot Chat Documentation](https://docs.github.com/en/copilot/github-copilot-chat)
- [MIGRATION_CONTEXT.md](MIGRATION_CONTEXT.md) - Contexto completo
- [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md) - Workflow diario

---

**Última actualización**: 2026-01-13  
**Tip**: Agrega este archivo a favoritos de Copilot: `@COPILOT_USAGE.md`
