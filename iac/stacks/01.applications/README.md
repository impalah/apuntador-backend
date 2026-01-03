# Infrastructure as Code (IaC) - Terraform Configuration

## Overview

This directory contains Terraform configurations for deploying the Apuntador backend API to **AWS ECS Fargate** with **API Gateway HTTP API** and **VPC Link**.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                    │
│                                                                      │
│  Internet                                                           │
│     │                                                               │
│     ▼                                                               │
│  ┌──────────────────┐                                              │
│  │    Route 53      │  DNS: api.apuntador.io                       │
│  └────────┬─────────┘                                              │
│           │                                                         │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │  API Gateway     │  HTTPS, Regional, Custom Domain              │
│  │  (HTTP API)      │  - ACM Certificate (*.apuntador.io)         │
│  └────────┬─────────┘  - CORS handled by FastAPI                  │
│           │                                                         │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │   VPC Link       │  Private connection to VPC                   │
│  └────────┬─────────┘  (~$7/month)                                │
│           │                                                         │
│  ┌────────▼─────────────────────────────────────────────────┐     │
│  │                    VPC (10.0.0.0/16)                      │     │
│  │                                                            │     │
│  │  ┌──────────────────────────────────────────────────┐    │     │
│  │  │ Public Subnets (10.0.1-3.0/24, 3 AZs)           │    │     │
│  │  │ - Internet Gateway                                │    │     │
│  │  │ - Route to 0.0.0.0/0                             │    │     │
│  │  └──────────────────────────────────────────────────┘    │     │
│  │                                                            │     │
│  │  ┌──────────────────────────────────────────────────┐    │     │
│  │  │ Private Subnets (10.0.11-13.0/24, 3 AZs)        │    │     │
│  │  │                                                   │    │     │
│  │  │  ┌─────────────────────────────────────┐        │    │     │
│  │  │  │  Application Load Balancer          │        │    │     │
│  │  │  │  - Internal (private)                │        │    │     │
│  │  │  │  - HTTP listener (port 80)           │        │    │     │
│  │  │  │  - Security Group: VPC traffic only  │        │    │     │
│  │  │  └────────────┬────────────────────────┘        │    │     │
│  │  │               │                                  │    │     │
│  │  │               ▼                                  │    │     │
│  │  │  ┌─────────────────────────────────────┐        │    │     │
│  │  │  │  ECS Fargate Tasks                   │        │    │     │
│  │  │  │  ┌────────────────┐  ┌────────────┐ │        │    │     │
│  │  │  │  │ apuntador-api  │  │ ADOT       │ │        │    │     │
│  │  │  │  │ (FastAPI)      │  │ Collector  │ │        │    │     │
│  │  │  │  │ Port: 8000     │  │ Sidecar    │ │        │    │     │
│  │  │  │  └────────────────┘  └────────────┘ │        │    │     │
│  │  │  │  - CPU: 256, Memory: 512 MB          │        │    │     │
│  │  │  │  - Auto-scaling (1-10 tasks)         │        │    │     │
│  │  │  └────────────┬────────────────────────┘        │    │     │
│  │  │               │                                  │    │     │
│  │  └───────────────┼──────────────────────────────────┘    │     │
│  │                  │                                        │     │
│  │                  ├────────▶ DynamoDB (via Gateway EP)    │     │
│  │                  │          - Certificate storage        │     │
│  │                  │          - On-demand billing          │     │
│  │                  │                                        │     │
│  │                  ├────────▶ S3 (via Gateway EP)          │     │
│  │                  │          - File storage               │     │
│  │                  │          - Free data transfer         │     │
│  │                  │                                        │     │
│  │                  ├────────▶ Secrets Manager (via IF EP)  │     │
│  │                  │          - OAuth credentials          │     │
│  │                  │          - $0.40/secret/month         │     │
│  │                  │                                        │     │
│  │                  ├────────▶ ECR (via Interface EP)       │     │
│  │                  │          - Container images           │     │
│  │                  │          - $14/month for 2 endpoints  │     │
│  │                  │                                        │     │
│  │                  └────────▶ CloudWatch (via IF EP)       │     │
│  │                             - Logs and metrics           │     │
│  │                             - X-Ray tracing              │     │
│  │                                                            │     │
│  │  ┌──────────────────────────────────────────────────┐    │     │
│  │  │ VPC Endpoints (Interface: $7/mo each)            │    │     │
│  │  │ - ecr.api (required for Fargate)                 │    │     │
│  │  │ - ecr.dkr (required for Fargate)                 │    │     │
│  │  │ - logs (CloudWatch Logs)                         │    │     │
│  │  │                                                   │    │     │
│  │  │ VPC Endpoints (Gateway: FREE)                    │    │     │
│  │  │ - DynamoDB                                        │    │     │
│  │  │ - S3                                              │    │     │
│  │  └──────────────────────────────────────────────────┘    │     │
│  └────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Architecture Decisions

### 🔒 Security-First Design

1. **Private ALB**: Load balancer is **not exposed to internet**, only accessible via VPC Link
2. **Private ECS Tasks**: All containers run in private subnets with **no public IPs**
3. **API Gateway as Edge**: SSL termination at API Gateway, internal traffic unencrypted
4. **VPC Endpoints**: No internet traffic for AWS services (DynamoDB, S3, ECR, CloudWatch)

### 💰 Cost Optimization

- **No NAT Gateway**: Saved ~$96/month by using VPC Endpoints instead ($21/month)
- **Gateway Endpoints**: DynamoDB and S3 access is **FREE** (no data transfer charges)
- **Interface Endpoints**: Only for services that require them (ECR, CloudWatch)
- **Fargate Spot**: Option to use Spot instances for 70% cost reduction (future)

### 📊 Observability

- **AWS Distro for OpenTelemetry (ADOT)**: Sidecar container for tracing
- **X-Ray Integration**: Distributed tracing across all services
- **CloudWatch Logs**: Centralized logging with structured JSON
- **Container Insights**: ECS metrics and performance monitoring

## Directory Structure

```
iac/stacks/01.applications/
├── 00.common.tf              # VPC, subnets, VPC endpoints, log groups
├── 01.api.tf                 # ECS cluster, task definition, service, ALB
├── 02.domain-ssl.tf          # API Gateway, VPC Link, Route53, ACM certificate
├── variables.tf              # All input variables
├── providers.tf              # AWS provider configuration
├── versions.tf               # Terraform version constraints
├── outputs.tf                # Stack outputs
└── README.md                 # This file
```

## Prerequisites

- **Terraform 1.10+** (installed in devcontainer)
- **AWS CLI v2** configured with appropriate credentials
- **Docker** (for building ECS container images)
- **AWS account** with permissions for:
  - ECS (Fargate)
  - EC2 (VPC, subnets, security groups, load balancers)
  - API Gateway v2 (HTTP API)
  - DynamoDB
  - S3
  - Secrets Manager
  - IAM
  - CloudWatch Logs
  - ECR (Elastic Container Registry)
  - Route 53 (optional, for custom domain)
  - ACM (AWS Certificate Manager, optional)

## Configuration

### 1. Copy and configure variables

```bash
cd iac/stacks/01.applications
cp terraform.tfvars.example terraform.tfvars  # Create this file from variables.tf
```

### 2. Edit `terraform.tfvars`

**Required variables:**

```hcl
# Basic Configuration
environment = "production"  # or "dev", "staging"
project     = "apuntador"
region      = "eu-west-1"  # or your preferred AWS region
cost_center = "engineering"

# VPC Configuration (from 00.common.tf)
vpc_cidr             = "10.0.0.0/16"
availability_zones   = ["eu-west-1a", "eu-west-1b", "eu-west-1c"]
public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]

# ECS Configuration
api_image       = "123456789012.dkr.ecr.eu-west-1.amazonaws.com/apuntador:1.0.0"
task_cpu        = "256"   # 0.25 vCPU
task_memory     = "512"   # 512 MB
desired_count   = 2       # Number of tasks (auto-scaling)

# Application Configuration
secret_key      = "generate-a-secure-random-32-char-key-here"  # IMPORTANT!
allowed_origins = "https://app.apuntador.io,capacitor://localhost,tauri://localhost"
debug           = false
enable_docs     = false   # true for development

# Cloud Provider Configuration
enabled_cloud_providers = "googledrive,dropbox"  # Comma-separated

# OAuth Credentials (from Secrets Manager or direct)
google_client_id      = "your-google-client-id.apps.googleusercontent.com"
google_client_secret  = "GOCSPX-your-google-client-secret"
google_redirect_uri   = "https://api.apuntador.io/oauth/callback/googledrive"

dropbox_client_id     = "your-dropbox-app-key"
dropbox_client_secret = "your-dropbox-app-secret"
dropbox_redirect_uri  = "https://api.apuntador.io/oauth/callback/dropbox"

# Infrastructure Resources
dynamodb_table_name   = "apuntador-certificates"
s3_bucket_name        = "apuntador-storage-eu-west-1"
secrets_prefix        = "apuntador"
auto_create_resources = true  # Auto-create DynamoDB/S3 if missing

# Logging
log_level  = "INFO"    # DEBUG, INFO, WARNING, ERROR
log_format = "json"    # json or human

# Domain Configuration (optional)
domain_name      = "api.apuntador.io"          # null to disable
route53_zone_id  = "Z1234567890ABC"            # Route53 hosted zone ID
certificate_arn  = null                         # Use existing cert or auto-create

# CloudWatch
api_gateway_log_retention_days = 7  # Days to retain API Gateway logs
```

**Key Configuration Variables:**

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `api_image` | ECR image URI for ECS tasks | - | ✅ Yes |
| `secret_key` | Secret key for signing tokens (min 32 chars) | - | ✅ Yes |
| `enabled_cloud_providers` | Comma-separated list of providers | `"googledrive,dropbox"` | No |
| `allowed_origins` | CORS origins (comma-separated) | `"*"` | No |
| `task_cpu` | ECS task CPU (256, 512, 1024, 2048, 4096) | `"256"` | No |
| `task_memory` | ECS task memory in MB | `"512"` | No |
| `desired_count` | Number of ECS tasks to run | `2` | No |
| `debug` | Enable debug mode | `false` | No |
| `log_level` | Logging level | `"INFO"` | No |
| `enable_docs` | Enable API documentation (Swagger) | `false` | No |
| `domain_name` | Custom domain for API Gateway | `null` | No |

### 3. Cloud Provider Configuration

The `enabled_cloud_providers` variable controls which OAuth providers are available to clients:

**Examples:**

```hcl
# Enable Google Drive only
enabled_cloud_providers = "googledrive"

# Enable Dropbox only
enabled_cloud_providers = "dropbox"

# Enable both (default)
enabled_cloud_providers = "googledrive,dropbox"

# Enable all (including OneDrive)
enabled_cloud_providers = "googledrive,dropbox,onedrive"

# Disable all cloud storage
enabled_cloud_providers = ""
```

**Note:** Even if you disable a provider, you still need to provide dummy OAuth credentials in `terraform.tfvars` (Terraform validates all variables). Use placeholder values like `"disabled"` for disabled providers.

## Deployment

### 1. Build and push Docker image to ECR

```bash
# From project root
cd /workspaces/apuntador-backend

# Build Docker image
docker build -t apuntador-backend:latest .

# Login to ECR
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.eu-west-1.amazonaws.com

# Tag and push
docker tag apuntador-backend:latest \
  123456789012.dkr.ecr.eu-west-1.amazonaws.com/apuntador:1.0.0
docker push 123456789012.dkr.ecr.eu-west-1.amazonaws.com/apuntador:1.0.0
```

**Note**: Replace `123456789012` with your AWS account ID.

### 2. Initialize Terraform

```bash
cd iac/stacks/01.applications
terraform init
```

### 3. Plan deployment

```bash
terraform plan -out=tfplan
```

Review the changes carefully before applying. Expected resources:
- **VPC**: 1 VPC, 6 subnets (3 public + 3 private), 1 Internet Gateway
- **VPC Endpoints**: 5 endpoints (DynamoDB, S3, ECR API, ECR DKR, CloudWatch Logs)
- **ECS**: 1 cluster, 1 task definition, 1 service
- **ALB**: 1 internal load balancer, 2 security groups, 1 target group, 1 listener
- **API Gateway**: 1 HTTP API, 1 VPC Link, 1 integration, 2 routes
- **CloudWatch**: 2 log groups (backend + ADOT collector)
- **IAM**: 2 roles (execution + task), 3 policies
- **Route53**: 2 records (A + AAAA) - if domain configured
- **ACM**: 1 certificate - if domain configured and cert doesn't exist

### 4. Apply configuration

```bash
terraform apply tfplan
```

Or with auto-approve (use carefully):
```bash
terraform apply -auto-approve
```

**Deployment time**: ~10-15 minutes
- VPC and subnets: ~2 minutes
- VPC Link: ~5-10 minutes ⏳ (slowest resource)
- ECS service: ~2-3 minutes
- API Gateway: ~1 minute

### 5. Verify deployment

```bash
# Get API endpoint
terraform output api_endpoint

# Test health check
curl https://api.apuntador.io/health

# Expected response:
# {"status": "healthy", "version": "1.0.0"}
```

### 6. Monitor deployment

```bash
# Watch ECS service deployment
aws ecs describe-services \
  --cluster production-apuntador-cluster \
  --services production-apuntador-service \
  --region eu-west-1

# View ECS task logs
aws logs tail /aws/ecs/production-apuntador/backend --follow

# View ADOT collector logs
aws logs tail /aws/ecs/production-apuntador/adot --follow
```

## Updating Configuration

### Changing enabled cloud providers

1. Edit `terraform.tfvars`:
   ```hcl
   enabled_cloud_providers = "googledrive"  # Disable Dropbox
   ```

2. Apply changes:
   ```bash
   terraform apply
   ```

3. ECS service will perform **rolling update** (zero downtime)
4. Clients will fetch updated config from `/config/providers` endpoint

**No client-side changes required!** Clients automatically adapt to the new configuration.

### Scaling ECS tasks

```hcl
# In terraform.tfvars
desired_count = 5  # Scale to 5 tasks
```

Or use AWS CLI:
```bash
aws ecs update-service \
  --cluster production-apuntador-cluster \
  --service production-apuntador-service \
  --desired-count 5 \
  --region eu-west-1
```

### Updating Docker image (new version)

```bash
# 1. Build new image
docker build -t apuntador-backend:1.1.0 .

# 2. Push to ECR
docker tag apuntador-backend:1.1.0 \
  123456789012.dkr.ecr.eu-west-1.amazonaws.com/apuntador:1.1.0
docker push 123456789012.dkr.ecr.eu-west-1.amazonaws.com/apuntador:1.1.0

# 3. Update terraform.tfvars
api_image = "123456789012.dkr.ecr.eu-west-1.amazonaws.com/apuntador:1.1.0"

# 4. Apply
terraform apply
```

ECS will perform rolling update:
- Start new tasks with new image
- Wait for health checks to pass
- Drain connections from old tasks
- Terminate old tasks

**Zero downtime deployment!** ✅

## Environment Variables

All application configuration is passed as ECS task environment variables. Key variables:

### Application
- `HOST` - Server host (always `0.0.0.0` for ECS)
- `PORT` - Server port (always `8000` for ECS)
- `DEBUG` - Debug mode (`true`/`false`)
- `SECRET_KEY` - Secret key for token signing (**sensitive**)
- `ALLOWED_ORIGINS` - CORS allowed origins (comma-separated)
- `ENABLE_DOCS` - Enable API documentation (`true`/`false`)

### OpenTelemetry (ADOT Sidecar)
- `OTEL_ENABLED` - Enable OpenTelemetry (`true`)
- `OTEL_SERVICE_NAME` - Service name (`apuntador-api`)
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OTLP endpoint (`http://localhost:4317`)
- `OTEL_EXPORTER_OTLP_PROTOCOL` - Protocol (`grpc`)
- `OTEL_PROPAGATORS` - Trace propagators (`xray`)
- `OTEL_PYTHON_DISTRO` - Python distribution (`aws_distro`)
- `OTEL_TRACES_SAMPLER` - Sampling strategy (`parentbased_traceidratio`)
- `OTEL_TRACES_SAMPLER_ARG` - Sampling ratio (`0.1` = 10%)

### Logging
- `LOG_LEVEL` - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT` - Log format (`json` for production, `human` for dev)
- `ENABLE_REQUEST_LOGGING` - Log all HTTP requests (`true`)

### Cloud Providers
- `ENABLED_CLOUD_PROVIDERS` - Comma-separated list of enabled providers
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI`
- `DROPBOX_CLIENT_ID` / `DROPBOX_CLIENT_SECRET` / `DROPBOX_REDIRECT_URI`

### Infrastructure (AWS)
- `INFRASTRUCTURE_PROVIDER` - Always `aws` for ECS
- `AWS_REGION` - AWS region (`eu-west-1`)
- `AWS_DYNAMODB_TABLE` - DynamoDB table name for certificates
- `AWS_S3_BUCKET` - S3 bucket name for storage
- `AWS_SECRETS_PREFIX` - Secrets Manager prefix (`apuntador`)
- `AUTO_CREATE_RESOURCES` - Auto-create AWS resources if missing (`true`)

## Security Best Practices

### Secret Management

**DO:**
- ✅ Use AWS Secrets Manager for OAuth secrets (future enhancement)
- ✅ Generate strong `secret_key` (min 32 chars, random)
- ✅ Rotate `secret_key` regularly
- ✅ Use different `secret_key` per environment
- ✅ Store `terraform.tfvars` in secure location (not in Git)

**DON'T:**
- ❌ Commit `terraform.tfvars` to Git
- ❌ Use simple passwords like "password123"
- ❌ Share `secret_key` across environments
- ❌ Expose `secret_key` in logs

### CORS Configuration

Configure `allowed_origins` to only include your actual domains:

```hcl
# Production
allowed_origins = "https://app.apuntador.io"

# Development
allowed_origins = "http://localhost:3000,capacitor://localhost,tauri://localhost"

# Both
allowed_origins = "https://app.apuntador.io,http://localhost:3000,capacitor://localhost,tauri://localhost"
```

**Never use `*` in production!**

## Troubleshooting

### ECS tasks fail to start

Check CloudWatch Logs:
```bash
# Backend logs
aws logs tail /aws/ecs/production-apuntador/backend --follow

# ADOT collector logs
aws logs tail /aws/ecs/production-apuntador/adot --follow
```

Common issues:
- **Missing environment variables**: Check task definition in AWS console
- **Invalid OAuth credentials**: Verify credentials in `terraform.tfvars`
- **DynamoDB table doesn't exist**: Set `auto_create_resources = true`
- **ECR image pull failed**: Verify `api_image` URI and ECR permissions
- **Task CPU/memory insufficient**: Increase `task_cpu` / `task_memory`

### VPC Link shows "PENDING" status

VPC Link creation takes **5-10 minutes**. Check status:
```bash
aws apigatewayv2 get-vpc-link \
  --vpc-link-id <vpc-link-id> \
  --region eu-west-1
```

Status lifecycle:
1. `PENDING` - Creating (~5-10 min)
2. `AVAILABLE` - Ready to use ✅
3. `FAILED` - Check subnet/security group configuration

### API Gateway returns 503 Service Unavailable

Possible causes:
1. **VPC Link not ready**: Wait for `AVAILABLE` status
2. **ALB target group unhealthy**: Check ECS task health
3. **Security group blocking traffic**: Verify ALB SG allows VPC traffic
4. **No healthy ECS tasks**: Check ECS service events

Debug steps:
```bash
# Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn> \
  --region eu-west-1

# Check ECS service events
aws ecs describe-services \
  --cluster production-apuntador-cluster \
  --services production-apuntador-service \
  --region eu-west-1 \
  --query 'services[0].events[0:5]'
```

### OAuth not working

1. Verify OAuth credentials in `terraform.tfvars`
2. Check redirect URIs match in OAuth console:
   - Google: https://console.cloud.google.com/apis/credentials
   - Dropbox: https://www.dropbox.com/developers/apps
3. Verify `ALLOWED_ORIGINS` includes client origin
4. Check FastAPI logs for OAuth errors

### Config endpoint returns empty providers

Check ECS task logs for:
```
Enabled providers: []
```

Verify `enabled_cloud_providers` in `terraform.tfvars`:
```hcl
enabled_cloud_providers = "googledrive,dropbox"
```

Then redeploy:
```bash
terraform apply
```

### Certificate validation fails

If using custom domain, ensure:
1. **Route53 hosted zone** exists and is correct
2. **DNS validation records** are created (auto-created by Terraform)
3. **Certificate status** is `ISSUED` (can take 5-30 minutes)

Check certificate status:
```bash
aws acm describe-certificate \
  --certificate-arn <cert-arn> \
  --region eu-west-1
```

## Monitoring

### CloudWatch Logs

View logs:
```bash
# Backend application logs
aws logs tail /aws/ecs/production-apuntador/backend --follow

# ADOT collector logs
aws logs tail /aws/ecs/production-apuntador/adot --follow

# API Gateway access logs (if domain configured)
aws logs tail /aws/apigateway/production-apuntador-api --follow

# Filter by error level
aws logs tail /aws/ecs/production-apuntador/backend \
  --filter-pattern "ERROR" \
  --follow
```

### X-Ray Tracing

View distributed traces in AWS X-Ray console:
```bash
# Open X-Ray service map
aws xray get-service-graph \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --region eu-west-1
```

Trace data includes:
- API Gateway → VPC Link → ALB → ECS request flow
- DynamoDB queries
- S3 operations
- External HTTP calls (OAuth providers)

### Container Insights

View ECS metrics in CloudWatch:
- **Container CPU/Memory utilization**
- **Network traffic**
- **Task count**
- **ALB request/response metrics**

Access via CloudWatch Console → Container Insights → ECS Clusters

### Metrics

Key metrics to monitor:

| Metric | Namespace | Description |
|--------|-----------|-------------|
| `TaskCount` | `AWS/ECS` | Number of running tasks |
| `CPUUtilization` | `AWS/ECS` | Container CPU usage |
| `MemoryUtilization` | `AWS/ECS` | Container memory usage |
| `TargetResponseTime` | `AWS/ApplicationELB` | ALB response time |
| `HealthyHostCount` | `AWS/ApplicationELB` | Number of healthy targets |
| `RequestCount` | `AWS/ApplicationELB` | Number of requests |
| `HTTPCode_Target_2XX_Count` | `AWS/ApplicationELB` | Successful responses |
| `HTTPCode_Target_5XX_Count` | `AWS/ApplicationELB` | Server errors |
| `4XXError` | `AWS/ApiGateway` | Client errors |
| `5XXError` | `AWS/ApiGateway` | Server errors |
| `IntegrationLatency` | `AWS/ApiGateway` | Backend latency |

Query metrics with AWS CLI:
```bash
# ECS CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=production-apuntador-service \
               Name=ClusterName,Value=production-apuntador-cluster \
  --start-time $(date -u -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date -u --iso-8601=seconds) \
  --period 300 \
  --statistics Average \
  --region eu-west-1

# ALB request count
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=app/production-apuntador-alb/<id> \
  --start-time $(date -u -d '1 hour ago' --iso-8601=seconds) \
  --end-time $(date -u --iso-8601=seconds) \
  --period 300 \
  --statistics Sum \
  --region eu-west-1
```

### Alarms (recommended)

Create CloudWatch alarms for critical metrics:

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name production-apuntador-high-cpu \
  --alarm-description "Alert when ECS CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=ServiceName,Value=production-apuntador-service \
               Name=ClusterName,Value=production-apuntador-cluster \
  --region eu-west-1

# No healthy targets alarm
aws cloudwatch put-metric-alarm \
  --alarm-name production-apuntador-no-healthy-targets \
  --alarm-description "Alert when no healthy ECS tasks" \
  --metric-name HealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=TargetGroup,Value=targetgroup/production-apuntador-tg/<id> \
  --region eu-west-1
```

## Cost Estimation

**Monthly costs (approximate, EU West 1):**

| Service | Configuration | Usage Pattern | Monthly Cost |
|---------|--------------|---------------|--------------|
| **ECS Fargate** | 2 tasks × 0.25 vCPU, 512 MB | 24/7 | ~$14.00 |
| **Application Load Balancer** | 1 internal ALB | 1M requests, 1 GB/hour data | ~$18.00 |
| **VPC Link** | 1 VPC Link | Always on | ~$7.20 |
| **API Gateway HTTP** | Regional API | 1M requests | ~$1.00 |
| **VPC Endpoints (Interface)** | 3 endpoints (ECR API, ECR DKR, Logs) | 24/7, 1 GB transfer | ~$21.00 |
| **VPC Endpoints (Gateway)** | 2 endpoints (DynamoDB, S3) | Unlimited | **FREE** |
| **DynamoDB** | On-demand | 1 GB storage, 100K R/W | ~$1.50 |
| **S3** | Standard | 10 GB storage, 1K requests | ~$0.25 |
| **ECR** | Private registry | 5 GB images | ~$0.50 |
| **CloudWatch Logs** | 2 log groups | 5 GB ingestion, 7-day retention | ~$2.50 |
| **CloudWatch Metrics** | Custom metrics | Container Insights enabled | ~$3.00 |
| **Data Transfer** | VPC → Internet | 10 GB outbound (API responses) | ~$0.90 |
| **Route 53** | Hosted zone + queries | 1 hosted zone, 1M queries | ~$0.50 |
| **ACM Certificate** | Regional cert | *.apuntador.io | **FREE** |
| **X-Ray** | Distributed tracing | 100K traces/month | **FREE** (within free tier) |
| | | | |
| **Total (Development)** | 1 task, minimal traffic | ~100K requests/month | **~$35/month** |
| **Total (Production)** | 2 tasks, moderate traffic | ~1M requests/month | **~$70/month** |
| **Total (High Traffic)** | 5 tasks, high traffic | ~10M requests/month | **~$150/month** |

### Cost Breakdown by Category

```
Infrastructure (always-on): ~$60/month
├── ECS Fargate (2 tasks):        $14
├── ALB:                           $18
├── VPC Link:                      $7
└── VPC Endpoints (3 × $7):       $21

Variable costs: ~$10/month (1M requests)
├── API Gateway:                   $1
├── DynamoDB:                      $1.50
├── CloudWatch Logs:               $2.50
├── CloudWatch Metrics:            $3
├── Data Transfer:                 $0.90
├── S3:                            $0.25
├── ECR:                           $0.50
└── Route 53:                      $0.50
```

### Cost Optimization Tips

1. **Use Fargate Spot** (70% savings on compute):
   ```hcl
   capacity_provider_strategy {
     capacity_provider = "FARGATE_SPOT"
     weight            = 100
   }
   ```
   Savings: ~$10/month per task

2. **Reduce VPC Endpoint count**:
   - Keep only ECR DKR ($7/mo) if pulling images infrequently
   - Remove CloudWatch Logs endpoint, use Internet Gateway for logs
   - Savings: ~$14/month

3. **Use ALB access logs selectively**:
   - Disable in development
   - Enable only for production debugging
   - Savings: ~$1-2/month

4. **Auto-scaling** based on traffic:
   ```hcl
   # Scale down during off-peak hours
   min_capacity = 1
   max_capacity = 10
   target_cpu   = 70
   ```
   Savings: ~$7/month (1 task instead of 2 at night)

5. **CloudWatch Logs retention**:
   ```hcl
   retention_in_days = 3  # Instead of 7
   ```
   Savings: ~$1/month

### Comparison: ECS Fargate vs Lambda

| Aspect | ECS Fargate (Current) | Lambda (Previous) |
|--------|----------------------|-------------------|
| **Base cost** | $14/mo (2 tasks 24/7) | $0 (pay per invocation) |
| **Request cost** | Included | $0.20 per 1M requests |
| **ALB** | $18/mo | N/A (uses API Gateway) |
| **VPC Link** | $7/mo | N/A |
| **VPC Endpoints** | $21/mo | N/A |
| **Cold starts** | ❌ Never | ✅ Yes (1-3s) |
| **Max timeout** | ∞ Unlimited | 15 minutes |
| **Concurrent requests** | ~200 per task | 1000 default limit |
| **WebSocket support** | ✅ Yes | ❌ No (need API Gateway WS) |
| **Total (1M req/mo)** | ~$70/month | ~$6/month |
| **Total (10M req/mo)** | ~$150/month | ~$15/month |

**When ECS is worth it:**
- ✅ High traffic (>10M requests/month)
- ✅ Long-running requests (>15 minutes)
- ✅ WebSocket connections
- ✅ No cold start tolerance
- ✅ Consistent performance requirements

**When Lambda is better:**
- ✅ Low/sporadic traffic (<1M requests/month)
- ✅ Short requests (<15 minutes)
- ✅ Cold starts acceptable (1-3s)
- ✅ Cost is primary concern

### Free Tier Benefits (First 12 months)

AWS Free Tier includes:
- **Fargate**: 50 GB-hours compute + 25 GB storage (limited)
- **ALB**: 750 hours/month
- **API Gateway**: 1M requests/month
- **CloudWatch**: 10 custom metrics, 5 GB logs
- **DynamoDB**: 25 GB storage, 25 WCU/RCU
- **S3**: 5 GB storage, 20K GET, 2K PUT
- **Data Transfer**: 100 GB outbound

**Estimated first-year savings**: ~$40/month = **$480/year**

## Cleanup

To destroy all resources:

```bash
cd iac/stacks/01.applications
terraform destroy
```

**Warning:** This will delete:
- ECS cluster, service, and task definition
- Application Load Balancer and target groups
- API Gateway HTTP API and VPC Link
- VPC, subnets, Internet Gateway, and VPC endpoints
- DynamoDB table (and all certificate data)
- S3 bucket (and all file storage)
- CloudWatch log groups (and all logs)
- Route 53 records (if custom domain configured)
- IAM roles and policies

**Data loss is permanent!** Ensure you have backups of:
- DynamoDB certificates table
- S3 bucket contents
- CloudWatch logs (export if needed)

### Partial Cleanup

To keep VPC but remove application:

```bash
# Comment out ECS, ALB, API Gateway resources in .tf files
# Then run:
terraform destroy -target=aws_ecs_service.apuntador \
                  -target=aws_ecs_cluster.apuntador \
                  -target=aws_lb.apuntador \
                  -target=aws_apigatewayv2_api.apuntador
```

### Export data before cleanup

```bash
# Export DynamoDB table
aws dynamodb scan \
  --table-name apuntador-certificates \
  --region eu-west-1 > dynamodb-backup.json

# Sync S3 bucket
aws s3 sync s3://apuntador-storage-eu-west-1 ./s3-backup/

# Export CloudWatch logs
aws logs create-export-task \
  --log-group-name /aws/ecs/production-apuntador/backend \
  --from $(date -d '7 days ago' +%s)000 \
  --to $(date +%s)000 \
  --destination apuntador-logs-backup \
  --region eu-west-1
```

## Related Documentation

- [AWS Deployment Guide](../../../docs/AWS_DEPLOYMENT_GUIDE.md) - Detailed AWS setup guide
- [OpenTelemetry AWS Deployment](../../../docs/OPENTELEMETRY_AWS_DEPLOYMENT.md) - ADOT configuration
- [Certificate Lifecycle](../../../docs/CERTIFICATE_LIFECYCLE.md) - mTLS certificate management
- [Infrastructure Abstraction](../../../docs/INFRASTRUCTURE_ABSTRACTION.md) - Repository pattern
- [Client Integration](../../../CLIENT_INTEGRATION.md) - Client-side OAuth flow
- [Testing Guide](../../../TESTING_GUIDE.md) - Unit and integration tests
- [GitHub Actions Lambda Config](../../../docs/GITHUB_ACTIONS_LAMBDA_CONFIG.md) - CI/CD setup

## Architecture Decisions

### Why API Gateway + VPC Link instead of public ALB?

**Security benefits:**
1. ✅ ALB never exposed to internet
2. ✅ SSL/TLS termination at API Gateway (managed certificates)
3. ✅ DDoS protection via AWS Shield (API Gateway)
4. ✅ WAF integration available (API Gateway)
5. ✅ Throttling and rate limiting (API Gateway)

**Cost trade-off:**
- Additional ~$7/month for VPC Link
- But enables future WAF rules, API caching, usage plans

### Why private subnets + VPC Endpoints instead of NAT Gateway?

**Cost savings:**
- NAT Gateway: ~$96/month (3 AZ × $32/mo)
- VPC Endpoints: ~$21/month (3 interfaces × $7/mo)
- **Savings: $75/month = $900/year**

**Performance:**
- ✅ Lower latency (direct connection to AWS services)
- ✅ No bandwidth bottleneck (NAT Gateway throughput limits)
- ✅ Higher reliability (no single point of failure)

### Why ECS Fargate instead of Lambda?

**For Apuntador specifically:**
- ❌ High traffic expected (OAuth flows)
- ❌ Cold starts unacceptable for user experience
- ✅ Predictable costs (flat rate vs pay-per-invocation)
- ✅ Future WebSocket support
- ✅ Longer request timeout (OAuth redirects)

**If traffic is low (<1M requests/month), Lambda is more cost-effective.**

### Why ADOT sidecar instead of Lambda Layer?

**Advantages:**
1. ✅ More granular control over OpenTelemetry configuration
2. ✅ Separate logs for telemetry vs application
3. ✅ Better resource isolation
4. ✅ Future: custom OTEL collector config
5. ✅ Compatible with X-Ray, CloudWatch, and third-party APM

**Cost:** Minimal overhead (~20 MB memory, negligible CPU)

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/impalah/apuntador-backend/issues
- **Documentation**: https://github.com/impalah/apuntador-backend/docs
- **AWS Support**: For infrastructure-related issues

## License

This infrastructure code is part of the Apuntador project. See [LICENSE](../../../LICENSE) for details.
