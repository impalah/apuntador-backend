# Infrastructure as Code (IaC) - Terraform Configuration

## Overview

This directory contains Terraform configurations for deploying the Apuntador backend API to AWS Lambda with API Gateway.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     AWS Cloud                            │
│                                                          │
│  ┌──────────────┐      ┌─────────────┐                 │
│  │ API Gateway  │─────▶│   Lambda    │                 │
│  │              │      │  (Python)   │                 │
│  └──────────────┘      └─────────────┘                 │
│         │                      │                        │
│         │                      ├───────▶ DynamoDB      │
│         │                      │         (Certificates) │
│         │                      │                        │
│         │                      ├───────▶ S3 Bucket     │
│         │                      │         (Storage)      │
│         │                      │                        │
│         │                      └───────▶ Secrets Manager│
│         │                               (OAuth secrets) │
│         │                                               │
│  ┌──────▼──────┐                                       │
│  │   Route53   │                                       │
│  │ api.apuntador.io                                    │
│  └─────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
iac/
├── modules/              # Reusable Terraform modules
│   ├── lambda/          # Lambda function configuration
│   ├── api-gateway/     # API Gateway HTTP API
│   ├── dynamodb/        # DynamoDB table for certificates
│   ├── s3/              # S3 bucket for file storage
│   └── ...
└── stacks/
    └── 01.applications/ # Application stack
        ├── 01.api.tf            # Main API Lambda configuration
        ├── variables.tf          # Input variables
        └── terraform.tfvars.example  # Configuration template
```

## Prerequisites

- Terraform 1.0+
- AWS CLI configured with appropriate credentials
- Docker (for building Lambda container images)
- AWS account with permissions for:
  - Lambda
  - API Gateway
  - DynamoDB
  - S3
  - Secrets Manager
  - IAM
  - CloudWatch Logs

## Configuration

### 1. Copy and configure variables

```bash
cd iac/stacks/01.applications
cp terraform.tfvars.example terraform.tfvars
```

### 2. Edit `terraform.tfvars`

**Required variables:**

```hcl
# Basic Configuration
environment = "production"
project     = "apuntador"
region      = "eu-west-1"

# Application Configuration
secret_key = "generate-a-secure-random-32-char-key"  # IMPORTANT!
allowed_origins = "https://app.apuntador.io,capacitor://localhost,tauri://localhost"

# Cloud Provider Configuration
enabled_cloud_providers = "googledrive,dropbox"  # Comma-separated

# OAuth Credentials
google_client_id     = "your-google-client-id.apps.googleusercontent.com"
google_client_secret = "GOCSPX-your-google-client-secret"
dropbox_client_id    = "your-dropbox-app-key"
dropbox_client_secret = "your-dropbox-app-secret"
```

**Key Configuration Variables:**

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `secret_key` | Secret key for signing tokens (min 32 chars) | - | ✅ Yes |
| `enabled_cloud_providers` | Comma-separated list of providers | `"googledrive,dropbox"` | No |
| `allowed_origins` | CORS origins (comma-separated) | `"*"` | No |
| `debug` | Enable debug mode | `"false"` | No |
| `log_level` | Logging level (DEBUG, INFO, WARNING, ERROR) | `"INFO"` | No |
| `enable_docs` | Enable API documentation (Swagger) | `false` | No |

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

### 1. Initialize Terraform

```bash
cd iac/stacks/01.applications
terraform init
```

### 2. Plan deployment

```bash
terraform plan
```

Review the changes carefully before applying.

### 3. Apply configuration

```bash
terraform apply
```

Type `yes` when prompted to confirm.

### 4. Get outputs

```bash
terraform output
```

Important outputs:
- `api_gateway_id` - API Gateway ID
- API endpoint URL (shown in apply output)

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

3. Lambda function will restart with new configuration
4. Clients will fetch updated config from `/config/providers` endpoint

**No client-side changes required!** Clients automatically adapt to the new configuration.

## Environment Variables

All application configuration is passed as Lambda environment variables. Key variables:

### Application
- `HOST` - Server host (always `0.0.0.0` for Lambda)
- `PORT` - Server port (always `8000` for Lambda)
- `DEBUG` - Debug mode (`true`/`false`)
- `SECRET_KEY` - Secret key for token signing (**sensitive**)
- `ALLOWED_ORIGINS` - CORS allowed origins
- `ENABLE_DOCS` - Enable API documentation (`true`/`false`)

### Logging
- `LOG_LEVEL` - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT` - Log format (`json` for Lambda)

### Cloud Providers
- `ENABLED_CLOUD_PROVIDERS` - Comma-separated list of enabled providers
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - Google OAuth credentials
- `DROPBOX_CLIENT_ID` / `DROPBOX_CLIENT_SECRET` - Dropbox OAuth credentials

### Infrastructure
- `INFRASTRUCTURE_PROVIDER` - Always `aws` for Lambda
- `AWS_DYNAMODB_TABLE` - DynamoDB table name for certificates
- `AWS_S3_BUCKET` - S3 bucket name for storage
- `AWS_SECRETS_PREFIX` - Secrets Manager prefix
- `AUTO_CREATE_RESOURCES` - Auto-create AWS resources if missing

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

### Lambda function fails to start

Check CloudWatch Logs:
```bash
aws logs tail /aws/lambda/production-apuntador-api --follow
```

Common issues:
- Missing environment variables
- Invalid OAuth credentials
- DynamoDB table doesn't exist (set `auto_create_resources = "true"`)

### OAuth not working

1. Verify OAuth credentials in `terraform.tfvars`
2. Check redirect URIs match in OAuth console:
   - Google: https://console.cloud.google.com/apis/credentials
   - Dropbox: https://www.dropbox.com/developers/apps
3. Verify `ALLOWED_ORIGINS` includes client origin

### Config endpoint returns empty providers

Check Lambda logs for:
```
Enabled providers: []
```

Verify `enabled_cloud_providers` in `terraform.tfvars`:
```hcl
enabled_cloud_providers = "googledrive,dropbox"
```

## Monitoring

### CloudWatch Logs

View logs:
```bash
# Recent logs
aws logs tail /aws/lambda/production-apuntador-api

# Follow logs in real-time
aws logs tail /aws/lambda/production-apuntador-api --follow

# Filter by error level
aws logs tail /aws/lambda/production-apuntador-api --filter-pattern "ERROR"
```

### Metrics

Key metrics to monitor:
- Lambda invocations
- Lambda errors
- API Gateway 4xx/5xx errors
- DynamoDB read/write capacity
- Lambda duration

Access via CloudWatch dashboard or:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=production-apuntador-api \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

## Cost Estimation

**Monthly costs (approximate):**

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 1M requests, 512MB, 5s avg | $1.00 |
| API Gateway | 1M requests | $1.00 |
| DynamoDB | On-demand, 1GB storage | $0.25 |
| S3 | 10GB storage, 1k requests | $0.25 |
| Secrets Manager | 2 secrets | $0.80 |
| CloudWatch Logs | 5GB, 7-day retention | $2.50 |
| **Total** | | **~$6/month** |

**Notes:**
- Free tier applies for first 12 months (Lambda: 1M requests/month free)
- Costs scale with usage
- Add CloudWatch alarms for budget alerts

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning:** This will delete:
- Lambda function
- API Gateway
- DynamoDB table (and all data)
- S3 bucket (and all data)
- CloudWatch logs

## Related Documentation

- [Backend Configuration](../../../docs/CONFIGURATION.md)
- [Cloud Provider Configuration](../../../docs/CLOUD_PROVIDER_CONFIGURATION.md)
- [AWS Deployment Guide](../../../docs/AWS_DEPLOYMENT_GUIDE.md)
- [Certificate Lifecycle](../../../docs/CERTIFICATE_LIFECYCLE.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/impalah/apuntador/issues
- Documentation: https://github.com/impalah/apuntador/docs
