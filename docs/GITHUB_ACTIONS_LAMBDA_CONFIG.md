# Configuración de Variables para GitHub Actions - Auto Deploy Lambda

Este documento explica cómo configurar las variables necesarias para el workflow `auto-deploy.yml` que actualiza la función Lambda en AWS.

## Variables a Configurar en GitHub

### 1. Acceder a la Configuración

1. Ve a tu repositorio: `https://github.com/impalah/apuntador-backend`
2. Navega a: **Settings**  **Secrets and variables**  **Actions**
3. Selecciona la pestaña **Variables** (para variables) o **Secrets** (para información sensible)

### 2. Environment: `pro`

Todas las variables deben configurarse en el **Environment llamado `pro`**:

1. Ve a: **Settings**  **Environments**  **pro**
2. En la sección **Environment variables**, añade las siguientes:

---

## Variables Requeridas (Environment Variables)

### Variables Existentes (ya configuradas)

Estas variables ya deberían estar configuradas desde el workflow `inspect-test-release.yml`:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `AWS_REGION` | `eu-west-1` | Región de AWS donde está desplegado el Lambda |
| `AWS_ECR_REGISTRY` | `670089840758.dkr.ecr.eu-west-1.amazonaws.com` | URL del registro ECR |
| `REPOSITORY` | `apuntador/backend` | Nombre del repositorio en ECR |

### Nueva Variable para Lambda

Añade esta nueva variable en el environment `pro`:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `LAMBDA_FUNCTION_NAME` | `apuntador-api` | Nombre de la función Lambda (debe coincidir con el nombre en Terraform) |

---

## Secrets Requeridos (Environment Secrets)

Estos secrets ya deberían estar configurados:

| Secret | Descripción |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | Access Key ID de AWS con permisos para Lambda y ECR |
| `AWS_SECRET_ACCESS_KEY` | Secret Access Key correspondiente |

---

## Permisos IAM Necesarios

El usuario de AWS (cuyas credenciales están en los secrets) necesita los siguientes permisos:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration",
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:eu-west-1:670089840758:function:apuntador-api"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Pasos para Configurar la Nueva Variable

### Opción A: Vía Web UI

1. Ve a: `https://github.com/impalah/apuntador-backend/settings/environments`
2. Haz clic en **pro**
3. En la sección **Environment variables**, haz clic en **Add variable**
4. Configura:
   - **Name**: `LAMBDA_FUNCTION_NAME`
   - **Value**: `apuntador-api`
5. Haz clic en **Add variable**

### Opción B: Verificar Variables Existentes

Antes de añadir, verifica que estas variables ya existan:

```bash
# Deberías tener configuradas:
AWS_REGION = eu-west-1
AWS_ECR_REGISTRY = 670089840758.dkr.ecr.eu-west-1.amazonaws.com
REPOSITORY = apuntador/backend
```

---

## Cómo Funciona el Workflow

### Flujo de Trabajo

1. **Trigger**: Se ejecuta automáticamente cuando el workflow `Inspect, Test and Build` completa exitosamente en la rama `main`
2. **Download Artifact**: Descarga el archivo `image_tag.txt` que contiene la versión de la imagen Docker
3. **Configure AWS**: Autentica con AWS usando las credenciales configuradas
4. **Update Lambda**: Ejecuta `aws lambda update-function-code` con la nueva imagen
5. **Wait for Update**: Espera hasta 5 minutos a que la actualización se complete
6. **Verify Deployment**: Verifica que la función Lambda esté en estado `Active`
7. **Test Function** (opcional): Invoca el endpoint `/health` para verificar que funciona

### Ejemplo de Comando AWS CLI

El workflow ejecuta internamente:

```bash
aws lambda update-function-code \
  --function-name apuntador-api \
  --image-uri 670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:1.0.7 \
  --region eu-west-1
```

---

## Validación de la Configuración

### Verificar que el Nombre de la Función es Correcto

Ejecuta este comando localmente (si tienes AWS CLI configurado):

```bash
aws lambda get-function \
  --function-name apuntador-api \
  --region eu-west-1 \
  --query 'Configuration.{Name: FunctionName, Runtime: PackageType, Image: CodeSha256}' \
  --output table
```

Deberías ver algo como:

```
-------------------------------------------------------
|                    GetFunction                      |
+-------+-----------+----------------------------------+
| Image |   Name    |            Runtime               |
+-------+-----------+----------------------------------+
|  ...  | apuntador-api | Image                       |
+-------+-----------+----------------------------------+
```

### Verificar Permisos IAM

Ejecuta este comando para verificar que puedes actualizar la función:

```bash
aws lambda update-function-code \
  --function-name apuntador-api \
  --region eu-west-1 \
  --dry-run \
  --image-uri 670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:latest
```

Si no tienes permisos, verás un error como:
```
An error occurred (AccessDeniedException) when calling the UpdateFunctionCode operation: User is not authorized...
```

---

## Troubleshooting

### Error: "ResourceNotFoundException"

**Problema**: El nombre de la función Lambda no existe o es incorrecto.

**Solución**:
1. Verifica el nombre exacto en AWS Console: Lambda  Functions
2. Actualiza la variable `LAMBDA_FUNCTION_NAME` con el nombre correcto
3. El nombre debe coincidir con el que definiste en Terraform (`apuntador-api`)

### Error: "AccessDeniedException"

**Problema**: El usuario de AWS no tiene permisos suficientes.

**Solución**:
1. Ve a AWS IAM Console
2. Encuentra el usuario cuyas credenciales están en GitHub Secrets
3. Añade la política de permisos mencionada arriba
4. Espera 1-2 minutos para que se propaguen los cambios

### Error: "ImageNotFoundException"

**Problema**: La imagen Docker no existe en ECR o el tag es incorrecto.

**Solución**:
1. Verifica que el workflow `Inspect, Test and Build` completó exitosamente
2. Verifica en ECR Console que la imagen existe: `670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend`
3. Revisa los logs del workflow anterior para ver qué tag se generó

### Timeout en "Wait for Lambda update to complete"

**Problema**: La actualización de Lambda toma más de 5 minutos.

**Solución**:
1. Verifica el tamaño de tu imagen Docker (debería ser < 10GB)
2. Verifica que Lambda tenga suficiente memoria configurada (actualmente 2048MB)
3. Revisa los logs de Lambda en CloudWatch para errores de inicialización

---

## Resumen de Cambios Realizados

### Cambios en el Workflow

1.  Eliminadas referencias a ECS (Task Definition, Cluster, Service)
2.  Añadido `aws lambda update-function-code` para actualizar la imagen
3.  Añadido loop de espera con verificación de estado cada 5 segundos (máximo 5 minutos)
4.  Añadida verificación de deployment (estado `Active`)
5.  Añadido test opcional del endpoint `/health`
6.  Mejorado manejo de errores con mensajes claros

### Nuevas Variables Necesarias

- `LAMBDA_FUNCTION_NAME` (nueva) = `apuntador-api`

### Variables Reutilizadas

- `AWS_REGION` (existente) = `eu-west-1`
- `AWS_ECR_REGISTRY` (existente) = `670089840758.dkr.ecr.eu-west-1.amazonaws.com`
- `REPOSITORY` (existente) = `apuntador/backend`
- `AWS_ACCESS_KEY_ID` (secret existente)
- `AWS_SECRET_ACCESS_KEY` (secret existente)

---

## Testing Manual

Puedes probar el deployment manualmente con estos comandos:

```bash
# 1. Configurar variables de entorno
export AWS_REGION=eu-west-1
export LAMBDA_FUNCTION_NAME=apuntador-api
export IMAGE_URI=670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:latest

# 2. Actualizar la función Lambda
aws lambda update-function-code \
  --function-name "${LAMBDA_FUNCTION_NAME}" \
  --image-uri "${IMAGE_URI}" \
  --region "${AWS_REGION}"

# 3. Esperar a que complete
aws lambda wait function-updated \
  --function-name "${LAMBDA_FUNCTION_NAME}" \
  --region "${AWS_REGION}"

# 4. Verificar estado
aws lambda get-function-configuration \
  --function-name "${LAMBDA_FUNCTION_NAME}" \
  --region "${AWS_REGION}" \
  --query '{Name: FunctionName, State: State, LastUpdateStatus: LastUpdateStatus}'
```

---

## Próximos Pasos

1.  Configura la variable `LAMBDA_FUNCTION_NAME` en GitHub (Environment `pro`)
2.  Verifica que los secrets de AWS ya existen
3.  Haz un commit en `main` que dispare el workflow `Inspect, Test and Build`
4.  Monitorea que el workflow `Auto Deploy Lambda on PRO` se ejecute automáticamente
5.  Verifica en AWS Lambda Console que la función se actualizó correctamente

---

## Contacto y Soporte

Si encuentras problemas:
1. Revisa los logs del workflow en GitHub Actions
2. Revisa los logs de la función Lambda en CloudWatch
3. Verifica que el nombre de la función Lambda coincide en Terraform y GitHub Actions
