# OpenTelemetry + AWS CloudWatch Deployment Guide

Esta guía explica cómo desplegar apuntador-backend con OpenTelemetry enviando trazas a AWS X-Ray/CloudWatch.

## 📋 Tabla de Contenidos

1. [Arquitectura](#arquitectura)
2. [Deployment en AWS Lambda](#deployment-en-aws-lambda)
3. [Deployment en ECS/Fargate](#deployment-en-ecsfargate)
4. [Verificación en CloudWatch](#verificación-en-cloudwatch)
5. [Troubleshooting](#troubleshooting)

---

## 🏗️ Arquitectura

```
┌─────────────────────┐
│  FastAPI Backend    │
│  (apuntador)        │
│                     │
│  OpenTelemetry SDK  │
└──────────┬──────────┘
           │ OTLP/gRPC
           │ (port 4317)
           ▼
┌─────────────────────┐
│  ADOT Collector     │
│  (AWS Distro for    │
│   OpenTelemetry)    │
└──────────┬──────────┘
           │ AWS X-Ray API
           ▼
┌─────────────────────┐       ┌─────────────────────┐
│   AWS X-Ray         │◄─────►│  AWS CloudWatch     │
│   (Tracing)         │       │  (Logs + Metrics)   │
└─────────────────────┘       └─────────────────────┘
```

**Flujo de datos:**
1. Tu aplicación FastAPI genera spans con OpenTelemetry SDK
2. Spans se exportan vía OTLP a ADOT Collector
3. ADOT Collector transforma y envía a AWS X-Ray
4. AWS X-Ray almacena trazas y las visualiza en CloudWatch

---

## 🚀 Deployment en AWS Lambda

### Opción 1: AWS Lambda Layer (Recomendado)

AWS proporciona un Lambda Layer con ADOT Collector pre-instalado.

**1. Configurar Lambda Function:**

```yaml
# serverless.yml o SAM template
Resources:
  ApuntadorBackendFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: apuntador-backend
      Runtime: python3.12
      Handler: lambda_main.handler
      
      # AWS ADOT Lambda Layer (actualiza ARN según tu región)
      Layers:
        - arn:aws:lambda:eu-west-1:901920570463:layer:aws-otel-python-amd64-ver-1-20-0:2
      
      Environment:
        Variables:
          # OpenTelemetry configuration
          OTEL_SERVICE_NAME: apuntador-backend
          OTEL_RESOURCE_ATTRIBUTES: service.version=1.0.0,deployment.environment=production
          AWS_LAMBDA_EXEC_WRAPPER: /opt/otel-instrument
          OTEL_PROPAGATORS: xray
          OTEL_PYTHON_DISTRO: aws_distro
          OTEL_PYTHON_CONFIGURATOR: aws_configurator
      
      # Permisos para X-Ray
      Policies:
        - AWSXRayDaemonWriteAccess
```

**2. No necesitas cambiar código:** El Layer automáticamente instrumenta FastAPI.

**ARNs del ADOT Lambda Layer por región:**
- `us-east-1`: `arn:aws:lambda:us-east-1:901920570463:layer:aws-otel-python-amd64-ver-1-20-0:2`
- `eu-west-1`: `arn:aws:lambda:eu-west-1:901920570463:layer:aws-otel-python-amd64-ver-1-20-0:2`
- `us-west-2`: `arn:aws:lambda:us-west-2:901920570463:layer:aws-otel-python-amd64-ver-1-20-0:2`

[Lista completa de ARNs](https://aws-otel.github.io/docs/getting-started/lambda/lambda-python)

### Opción 2: Manual (sin Layer)

Si prefieres control total, instala dependencias en tu Lambda:

**1. Añadir a `requirements.txt`:**
```txt
opentelemetry-api
opentelemetry-sdk
opentelemetry-instrumentation-fastapi
opentelemetry-exporter-otlp-proto-grpc
aws-xray-sdk
opentelemetry-sdk-extension-aws
opentelemetry-propagator-aws-xray
```

**2. Configurar IAM Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 🐳 Deployment en ECS/Fargate

### Configuración con ADOT Sidecar

**1. Task Definition con ADOT Collector Sidecar:**

```json
{
  "family": "apuntador-backend-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "containerDefinitions": [
    {
      "name": "apuntador-backend",
      "image": "670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "OTEL_SERVICE_NAME",
          "value": "apuntador-backend"
        },
        {
          "name": "OTEL_EXPORTER_OTLP_ENDPOINT",
          "value": "http://localhost:4317"
        },
        {
          "name": "OTEL_PROPAGATORS",
          "value": "xray"
        },
        {
          "name": "AWS_REGION",
          "value": "eu-west-1"
        }
      ],
      "dependsOn": [
        {
          "containerName": "aws-otel-collector",
          "condition": "START"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/apuntador-backend",
          "awslogs-region": "eu-west-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    },
    {
      "name": "aws-otel-collector",
      "image": "public.ecr.aws/aws-observability/aws-otel-collector:latest",
      "command": ["--config=/etc/ecs/otel-config.yaml"],
      "environment": [
        {
          "name": "AWS_REGION",
          "value": "eu-west-1"
        }
      ],
      "secrets": [
        {
          "name": "AOT_CONFIG_CONTENT",
          "valueFrom": "arn:aws:secretsmanager:eu-west-1:ACCOUNT_ID:secret:otel-collector-config"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/apuntador-backend-otel",
          "awslogs-region": "eu-west-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/apuntador-backend-task-role",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole"
}
```

**2. IAM Task Role (para enviar trazas a X-Ray):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

**3. Terraform Example:**

```hcl
resource "aws_ecs_task_definition" "apuntador_backend" {
  family                   = "apuntador-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  task_role_arn            = aws_iam_role.task_role.arn
  execution_role_arn       = aws_iam_role.execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "apuntador-backend"
      image     = "${var.ecr_repository_url}:latest"
      essential = true
      
      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]
      
      environment = [
        {
          name  = "OTEL_SERVICE_NAME"
          value = "apuntador-backend"
        },
        {
          name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
          value = "http://localhost:4317"
        },
        {
          name  = "OTEL_PROPAGATORS"
          value = "xray"
        }
      ]
      
      dependsOn = [{
        containerName = "aws-otel-collector"
        condition     = "START"
      }]
    },
    {
      name      = "aws-otel-collector"
      image     = "public.ecr.aws/aws-observability/aws-otel-collector:latest"
      essential = true
      
      command = ["--config=/etc/ecs/otel-config.yaml"]
      
      environment = [{
        name  = "AWS_REGION"
        value = var.aws_region
      }]
    }
  ])
}
```

---

## 📊 Verificación en CloudWatch

### 1. Ver Trazas en X-Ray

1. Abre **AWS X-Ray Console**: https://console.aws.amazon.com/xray
2. Selecciona tu región (eu-west-1)
3. Ve a **"Traces"**
4. Filtrar por:
   - **Service name**: `apuntador-backend`
   - **Time range**: Últimos 5 minutos
5. Click en una traza para ver detalles

### 2. Ver Service Map

1. En X-Ray Console, ve a **"Service map"**
2. Verás tu servicio y sus dependencias (httpx calls, etc.)
3. Click en nodos para ver estadísticas (latency, errors, throughput)

### 3. Correlacionar Logs con Trazas

Tus logs en CloudWatch ahora incluyen `trace_id` y `span_id`:

```json
{
  "timestamp": "2025-11-28 10:30:45.123",
  "level": "INFO",
  "trace_id": "1-64f2a3b4-12345678901234567890abcd",
  "span_id": "abcdef1234567890",
  "message": "Processing OAuth request"
}
```

**Para correlacionar:**
1. Copia el `trace_id` del log
2. Ve a X-Ray Console → "Traces"
3. Filtra por: `annotation.trace_id = "1-64f2a3b4-..."`
4. Verás la traza completa relacionada con ese log

### 4. CloudWatch Insights Queries

```sql
-- Buscar logs de una traza específica
fields @timestamp, level, message, trace_id, span_id
| filter trace_id = "1-64f2a3b4-12345678901234567890abcd"
| sort @timestamp desc

-- Ver errores con contexto de traza
fields @timestamp, level, message, trace_id, exception.type
| filter level = "ERROR"
| sort @timestamp desc
| limit 20

-- Performance analysis: logs con traza lenta
fields @timestamp, message, trace_id
| filter message like /slow/
| stats count() by trace_id
```

---

## 🔧 Troubleshooting

### No aparecen trazas en X-Ray

**1. Verificar permisos IAM:**
```bash
# Para Lambda
aws lambda get-function-configuration \
  --function-name apuntador-backend \
  --query 'Role'

# Verificar policy
aws iam get-role-policy \
  --role-name lambda-execution-role \
  --policy-name XRayWriteAccess
```

**2. Verificar ADOT Collector logs:**
```bash
# Para ECS
aws logs tail /ecs/apuntador-backend-otel --follow

# Buscar errores
aws logs filter-log-events \
  --log-group-name /ecs/apuntador-backend-otel \
  --filter-pattern "ERROR"
```

**3. Verificar variables de entorno:**
```bash
# Para Lambda
aws lambda get-function-configuration \
  --function-name apuntador-backend \
  --query 'Environment.Variables'
```

### Trazas incompletas o cortadas

**Causa:** Timeout del exporter

**Solución:** Ajustar configuración del batch processor:
```yaml
# otel-collector-config.yaml
processors:
  batch:
    timeout: 30s              # Aumentar de 10s
    send_batch_size: 100      # Aumentar de 50
    send_batch_max_size: 200  # Aumentar de 100
```

### Alto costo en X-Ray

**Causa:** Sampling 100% de trazas

**Solución:** Reducir sampling rate:
```python
# En telemetry.py
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # Solo 10% de trazas
```

O configurar sampling por ruta:
```python
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio, StaticSampler

# No samplear health checks
def custom_sampler(sampling_rate: float = 0.1):
    return ParentBasedTraceIdRatio(sampling_rate)
```

---

## 📚 Referencias

- [AWS ADOT Documentation](https://aws-otel.github.io/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [AWS X-Ray Developer Guide](https://docs.aws.amazon.com/xray/latest/devguide/)
- [ADOT Collector Configuration](https://aws-otel.github.io/docs/components/otlp-exporter)
- [Lambda Layer ARNs](https://aws-otel.github.io/docs/getting-started/lambda/lambda-python)
