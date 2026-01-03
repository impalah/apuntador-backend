# Apuntador Backend - API Testing with cURL

Ejemplos de comandos `curl` para probar el backend mientras está ejecutándose en el debugger de VS Code.

---

##  Cómo Iniciar

1. **Abrir VS Code**
2. **Ir a la vista de Debug** (D o Ctrl+Shift+D)
3. **Seleccionar "API - apuntador-backend"** en el dropdown
4. **Presionar F5** o hacer clic en el botón verde "Start Debugging"
5. **Esperar a ver** en el terminal: `Application startup complete`

El servidor estará en: `http://localhost:8000`

---

##  Health & Info Endpoints

### Health Check
```bash
curl -s http://localhost:8000/health | jq .
```

**Respuesta esperada**:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### API Documentation (OpenAPI/Swagger)
```bash
# Abrir en el navegador (solo si ENABLE_DOCS=true)
open http://localhost:8000/docs

# O ver el JSON schema
curl -s http://localhost:8000/openapi.json | jq .
```

**Nota de Seguridad**: 
- La documentación está controlada por la variable `ENABLE_DOCS` en `.env`
- En **desarrollo**: `ENABLE_DOCS=true` (documentación disponible)
- En **producción**: `ENABLE_DOCS=false` (documentación deshabilitada por seguridad)
- Si cambias esta variable, **reinicia el servidor** para que tome efecto

---

##  Certificate Authority Endpoints

### Get CA Certificate (Public)
```bash
curl -s http://localhost:8000/device/ca-certificate | jq .
```

**Respuesta esperada**:
```json
{
  "certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
  "format": "PEM",
  "usage": "Add to client truststore for mTLS verification"
}
```

**Nota**: El certificado se recupera desde AWS Secrets Manager (`apuntador/ca-certificate`). 
Si obtienes un error 500 "CA certificate not found", verifica que:
1. El secret existe en AWS: `aws secretsmanager list-secrets --region eu-west-1`
2. El nombre sea `apuntador/ca-certificate` (con guiones, no guiones bajos)
3. Tus credenciales AWS tengan permisos: `secretsmanager:GetSecretValue`

**Guardar certificado a archivo**:
```bash
curl -s http://localhost:8000/device/ca-certificate | jq -r '.certificate' > ca_cert.pem
openssl x509 -in ca_cert.pem -text -noout
```

---

##  Device Enrollment (mTLS)

### Enroll Android Device

**1. Generar un CSR de prueba** (simular Android Keystore):
```bash
# Generar clave privada de prueba
openssl genrsa -out test_device.key 2048

# Generar CSR
openssl req -new -key test_device.key -out test_device.csr \
  -subj "/C=ES/O=Apuntador/CN=android-device-12345"

# Ver el CSR
cat test_device.csr
```

**2. Enviar CSR al backend**:
```bash
CSR_CONTENT=$(cat test_device.csr)

curl -X POST http://localhost:8000/device/enroll \
  -H "Content-Type: application/json" \
  -d "{
    \"csr\": \"$CSR_CONTENT\",
    \"device_id\": \"android-device-12345\",
    \"platform\": \"android\",
    \"attestation\": null
  }" | jq .
```

**Respuesta esperada**:
```json
{
  "certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
  "serial": "1234567890ABCDEF",
  "expires_at": "2025-11-26T12:00:00+00:00",
  "device_id": "android-device-12345"
}
```

**3. Guardar certificado del dispositivo**:
```bash
curl -X POST http://localhost:8000/device/enroll \
  -H "Content-Type: application/json" \
  -d "{
    \"csr\": \"$(cat test_device.csr)\",
    \"device_id\": \"android-device-12345\",
    \"platform\": \"android\",
    \"attestation\": null
  }" | jq -r '.certificate' > device_cert.pem

# Verificar el certificado
openssl x509 -in device_cert.pem -text -noout
```

---

##  mTLS Protected Endpoints

Para acceder a endpoints protegidos con mTLS, necesitas enviar el certificado del cliente.

### Ejemplo: Acceder con mTLS

**Sin certificado** (debería fallar):
```bash
curl -s http://localhost:8000/protected/example
```

**Respuesta esperada**:
```json
{
  "detail": "Client certificate required for mTLS authentication"
}
```

**With certificate** (using nginx or proxy):
```bash
# This requires configuring an HTTPS proxy with mTLS
# See mTLS documentation for complete configuration

curl -s https://localhost:8443/protected/example \
  --cert device_cert.pem \
  --key test_device.key \
  --cacert ca_cert.pem
```

---

##  OAuth Endpoints (Google Drive, Dropbox)

### Google Drive - Authorization

**1. Start OAuth flow**:
```bash
curl -X POST http://localhost:8000/oauth/authorize/googledrive \
  -H "Content-Type: application/json" \
  -d '{
    "redirect_uri": "http://localhost:3000/callback"
  }' | jq .
```

**Expected response**:
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "signed-state-token-here"
}
```

**2. Simulate callback** (after user authorizes):
```bash
# Note: The actual code will come from Google after authorization
curl "http://localhost:8000/oauth/callback/googledrive?code=AUTHORIZATION_CODE&state=SIGNED_STATE" | jq .
```

**Expected response**:
```json
{
  "access_token": "ya29.a0AfB_...",
  "refresh_token": "1//0gZ8k...",
  "expires_in": 3599,
  "token_type": "Bearer"
}
```

### Dropbox - Authorization

Similar al flujo de Google Drive:
```bash
curl -X POST http://localhost:8000/oauth/authorize/dropbox \
  -H "Content-Type: application/json" \
  -d '{
    "redirect_uri": "http://localhost:3000/callback"
  }' | jq .
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/oauth/token/refresh/googledrive \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "1//0gZ8k..."
  }' | jq .
```

---

##  Testing Certificate Lifecycle

### List All Certificates (DynamoDB)
```bash
# Listar todos los certificados (sin paginación)
AWS_PAGER="" aws dynamodb scan \
  --table-name apuntador-tls-certificates \
  --region eu-west-1 \
  --output json | jq '.Items[] | {device_id: .device_id.S, serial: .serial_number.S, platform: .platform.S, issued_at: .issued_at.S, expires_at: .expires_at.S, revoked: .revoked.BOOL}'

# O en formato tabla
AWS_PAGER="" aws dynamodb scan \
  --table-name apuntador-tls-certificates \
  --region eu-west-1 \
  --query 'Items[].{DeviceID:device_id.S,Serial:serial_number.S,Platform:platform.S,ExpiresAt:expires_at.S}' \
  --output table
```

### Check Certificate by Serial (via DynamoDB)
```bash
# Ejemplo con un serial específico
SERIAL="93BB75CB9862C509323ED9C769EF1002"

AWS_PAGER="" aws dynamodb query \
  --table-name apuntador-tls-certificates \
  --index-name SerialIndex \
  --key-condition-expression "serial_number = :serial" \
  --expression-attribute-values "{\":serial\":{\"S\":\"$SERIAL\"}}" \
  --region eu-west-1 \
  --output json | jq '.Items[0] | {device_id: .device_id.S, serial: .serial_number.S, platform: .platform.S, expires_at: .expires_at.S}'
```

### List Expiring Certificates
```bash
# Certificados que expiran en los próximos 7 días
THRESHOLD=$(date -u -v+7d +"%Y-%m-%dT%H:%M:%S+00:00")

AWS_PAGER="" aws dynamodb scan \
  --table-name apuntador-tls-certificates \
  --region eu-west-1 \
  --filter-expression "expires_at < :threshold AND revoked = :false" \
  --expression-attribute-values "{\":threshold\":{\"S\":\"$THRESHOLD\"},\":false\":{\"BOOL\":false}}" \
  --output json | jq '.Items[] | {device_id: .device_id.S, serial: .serial_number.S, expires_at: .expires_at.S}'
```

---

##  Debugging Tips

### Ver logs en tiempo real
El debugger de VS Code mostrará todos los logs. También puedes:

```bash
# Ver logs de PynamoDB
tail -f /tmp/apuntador-backend.log | grep pynamodb

# Ver logs de requests
tail -f /tmp/apuntador-backend.log | grep "trace_id"
```

### Breakpoints Útiles

Coloca breakpoints en:
- `src/apuntador/routers/device_enrollment.py` línea ~50 (enroll_device)
- `src/apuntador/services/certificate_authority.py` línea ~100 (sign_csr)
- `src/apuntador/middleware/mtls_validation.py` línea ~150 (validate_certificate)
- `src/apuntador/infrastructure/implementations/aws/certificate_repository.py` línea ~170 (save_certificate)

### Variables de Entorno en Debug

El debugger usa las variables de `.env`. Para cambiar temporalmente:
```bash
# En el terminal de VS Code
export INFRASTRUCTURE_PROVIDER=local
# Luego relanzar el debugger
```

---

##  Verificar DynamoDB con PynamoDB

### Test Connection
```bash
# Enrollar un dispositivo de prueba
DEVICE_ID="test-$(date +%s)"
CSR_CONTENT=$(cat /tmp/test_device.csr | sed 's/$/\\n/' | tr -d '\n')

curl -X POST http://localhost:8000/device/enroll \
  -H "Content-Type: application/json" \
  -d "{\"csr\":\"$CSR_CONTENT\",\"device_id\":\"$DEVICE_ID\",\"platform\":\"android\",\"attestation\":null}" \
  | jq .

# Luego verificar en DynamoDB (sin paginación)
AWS_PAGER="" aws dynamodb scan \
  --table-name apuntador-tls-certificates \
  --region eu-west-1 \
  --filter-expression "device_id = :device_id" \
  --expression-attribute-values "{\":device_id\":{\"S\":\"$DEVICE_ID\"}}" \
  --output json | jq '.Items[0] | {device_id: .device_id.S, serial: .serial_number.S, platform: .platform.S}'
```

---

##  Monitoring

### Check DynamoDB Metrics
```bash
AWS_PAGER="" aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=apuntador-tls-certificates \
  --start-time $(date -u -v-1H +"%Y-%m-%dT%H:%M:%S") \
  --end-time $(date -u +"%Y-%m-%dT%H:%M:%S") \
  --period 300 \
  --statistics Sum \
  --region eu-west-1
```

### Check S3 Bucket
```bash
AWS_PAGER="" aws s3 ls s3://apuntador.io-tls-cert-storage/ --region eu-west-1
```

### Check Secrets
```bash
# Ver el certificado de la CA (sin paginación)
AWS_PAGER="" aws secretsmanager get-secret-value \
  --secret-id apuntador/ca-certificate \
  --region eu-west-1 \
  --query SecretString \
  --output text | openssl x509 -text -noout

# Listar todos los secrets de apuntador (sin paginación)
AWS_PAGER="" aws secretsmanager list-secrets \
  --region eu-west-1 \
  --output json | jq -r '.SecretList[] | select(.Name | contains("apuntador")) | .Name'
```

**Nota importante sobre nombres**: 
Los secrets en AWS deben usar **guiones** (`-`), no guiones bajos (`_`):
-  Correcto: `apuntador/ca-private-key`, `apuntador/ca-certificate`
-  Incorrecto: `apuntador/ca_private_key`, `apuntador/ca_certificate`

---

##  Escenarios de Prueba Completos

### Script Automatizado (Recomendado)

Usa el script de prueba automatizado que verifica todo el flujo:

```bash
# Desde el directorio raíz del proyecto
./scripts/test-enrollment-flow.sh
```

Este script:
1.  Obtiene el certificado de la CA
2.  Genera credenciales del dispositivo (clave + CSR)
3.  Enrolla el dispositivo en el backend
4.  Verifica el certificado con OpenSSL
5.  Comprueba que se guardó en DynamoDB (scan + índice)
6.  Muestra resumen completo con todos los checks

### Escenario 1: Enrollment + Verificación (Manual)

```bash
#!/bin/bash
echo " Testing complete device enrollment flow..."

# 1. Get CA certificate
echo "1 Getting CA certificate..."
curl -s http://localhost:8000/device/ca-certificate | jq -r '.certificate' > ca.pem
FINGERPRINT=$(curl -s http://localhost:8000/device/ca-certificate | jq -r '.fingerprint')
echo "   CA Fingerprint: $FINGERPRINT"

# 2. Generate device key and CSR
echo "2 Generating device credentials..."
openssl genrsa -out device.key 2048 2>/dev/null
openssl req -new -key device.key -out device.csr \
  -subj "/C=ES/O=Apuntador/CN=android-test-$(date +%s)" 2>/dev/null

# 3. Enroll device
echo "3 Enrolling device..."
DEVICE_ID="android-test-$(date +%s)"
RESPONSE=$(curl -s -X POST http://localhost:8000/device/enroll \
  -H "Content-Type: application/json" \
  -d "{
    \"csr\": \"$(cat device.csr)\",
    \"device_id\": \"$DEVICE_ID\",
    \"platform\": \"android\",
    \"attestation\": null
  }")

echo "$RESPONSE" | jq -r '.certificate' > device.pem
SERIAL=$(echo "$RESPONSE" | jq -r '.serial')
echo "   Device Serial: $SERIAL"

# 4. Verify certificate
echo "4 Verifying certificate..."
openssl verify -CAfile ca.pem device.pem

# 5. Check in DynamoDB
echo "5 Checking DynamoDB..."
AWS_PAGER="" aws dynamodb scan \
  --table-name apuntador-tls-certificates \
  --region eu-west-1 \
  --filter-expression "device_id = :device_id" \
  --expression-attribute-values "{\":device_id\":{\"S\":\"$DEVICE_ID\"}}" \
  --output json | jq '.Items[0] | {device_id: .device_id.S, serial: .serial_number.S, platform: .platform.S, expires_at: .expires_at.S}'

echo " Test completed!"
```

### Escenario 2: OAuth Flow Completo (Google Drive)

```bash
#!/bin/bash
echo " Testing OAuth flow..."

# 1. Start authorization
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8000/oauth/authorize/googledrive \
  -H "Content-Type: application/json" \
  -d '{"redirect_uri": "http://localhost:3000/callback"}')

AUTH_URL=$(echo "$AUTH_RESPONSE" | jq -r '.authorization_url')
STATE=$(echo "$AUTH_RESPONSE" | jq -r '.state')

echo "1 Authorization URL generated"
echo "   Open in browser: $AUTH_URL"
echo "   State: ${STATE:0:50}..."
echo ""
echo "2 After authorization, Google will redirect to:"
echo "   http://localhost:3000/callback?code=AUTHORIZATION_CODE&state=$STATE"
echo ""
echo "3 Then exchange code for token:"
echo "   curl \"http://localhost:8000/oauth/callback/googledrive?code=CODE&state=$STATE\""
```

---

##  Notes

- **Port**: El servidor corre en `http://localhost:8000`
- **Hot Reload**: El debugger tiene `--reload` activado, por lo que se reiniciará automáticamente al guardar cambios
- **Breakpoints**: Funcionan perfectamente mientras el servidor está corriendo
- **Environment**: Usa las variables de `.env` (actualmente `INFRASTRUCTURE_PROVIDER=aws`)
- **Region**: Todos los recursos AWS en `eu-west-1`

---

##  Troubleshooting

### Puerto ocupado
```bash
lsof -ti:8000 | xargs kill -9
```

### Ver qué proceso usa el puerto
```bash
lsof -i :8000
```

### Limpiar certificados de prueba
```bash
rm -f test_device.* device.* ca.pem device.pem
```

### Reset DynamoDB (¡CUIDADO! Borra todos los certificados)
```bash
aws dynamodb delete-table \
  --table-name apuntador-tls-certificates \
  --region eu-west-1

# Luego recrear con el script
bash scripts/setup-aws-infrastructure.sh
```

---

**Happy Testing!** 
