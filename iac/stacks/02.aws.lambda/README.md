# Infrastructure as Code (IaC) - AWS Lambda + API Gateway

## Overview

This directory contains Terraform configurations for deploying the Apuntador backend API to **AWS Lambda** (container image) with **API Gateway HTTP API**.

## Architecture

```
                         AWS Cloud                                            
                                                                              
  Internet                                                                   
                                                        
      Route 53        DNS: api.apuntador.io                               
                                                        
                                                                            
                                                        
    API Gateway       HTTPS, Regional, Custom Domain                      
    (HTTP API)        - ACM Certificate (*.apuntador.io)                 
                      - CORS configuration                          
                      - Lambda proxy integration                          
                                                                            
                                                        
                                                        
    Lambda Function   Container Image                           
    (apuntador-api)   - Python 3.14                                
                      - 2048 MB memory                                
                      - 300s timeout                                
                      - OpenTelemetry auto-instrumentation                                
                      - X-Ray tracing (PassThrough mode)                                
                                                                            
                                                        
                      External APIs (via Internet)               
                      - Dropbox OAuth                                
                      - Google Drive OAuth                                
                                                                       
                                                                         
                     DynamoDB (on-demand)                 
                     - Certificate storage                     
                     - No VPC required                       
                                                                         
                     S3                       
                     - File storage                            
                     - Public access                      
                                                                         
                     Secrets Manager               
                     - OAuth credentials                       
                     - CA private key                      
                                                                         
                     ECR (Elastic Container Registry)                    
                     - Lambda container images                        
                                                                          
                     CloudWatch                    
                     - Lambda logs                        
                     - X-Ray traces                           
                                                                          
```

## Key Architecture Decisions

### Serverless-First Design

1. **Lambda Container Image**: Uses custom Dockerfile for full control over dependencies
2. **No VPC Required**: Lambda accesses AWS services via AWS network (no NAT needed)
3. **API Gateway as Edge**: SSL termination, throttling, CORS, request validation
4. **IAM Permissions**: Least-privilege policies for DynamoDB, S3, Secrets Manager, X-Ray

### Cost Optimization

- **Lambda on-demand**: Pay only for requests and compute time (no idle costs)
- **No VPC infrastructure**: No NAT Gateway, VPC endpoints, or load balancers
- **DynamoDB on-demand**: Pay per request (no provisioned capacity)
- **Estimated monthly cost** (10M requests, 1GB-sec per request):
  - Lambda compute: ~$20
  - API Gateway: ~$35
  - DynamoDB: ~$2.50
  - CloudWatch Logs (1GB): ~$0.50
  - **Total: ~$58/month** (vs ~$73/month for ECS Fargate)

### Observability

- **OpenTelemetry**: Auto-instrumentation via `aws-opentelemetry-distro` in container
- **X-Ray Integration**: Distributed tracing with PassThrough mode (low overhead)
- **CloudWatch Logs**: Structured JSON logging via Loguru
- **Lambda Insights**: Performance metrics and profiling (optional)

## Directory Structure

```
iac/stacks/02.aws.lambda/
├── 01.api.tf                 # Lambda function, IAM policies, API Gateway
├── variables.tf              # Input variables
├── configuration.application.tfvars  # Variable values
├── providers.tf              # AWS provider configuration
├── versions.tf               # Terraform version constraints
├── outputs.tf                # Stack outputs
└── README.md                 # This file
```

## Prerequisites

- **Terraform 1.10+** (installed in devcontainer)
- **AWS CLI v2** configured with appropriate credentials
- **Docker** (for building Lambda container images)
- **AWS account** with permissions for:
  - Lambda
  - API Gateway v2 (HTTP API)
  - DynamoDB
  - S3
  - Secrets Manager
  - IAM
  - CloudWatch Logs
  - ECR (Elastic Container Registry)
  - Route 53 (for custom domain)
  - ACM (AWS Certificate Manager)
  - X-Ray

## Configuration

### 1. Build and push Lambda container image

```bash
# Build Lambda container
docker build -f Dockerfile.lambda -t apuntador-lambda:latest .

# Tag for ECR
docker tag apuntador-lambda:latest 670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:latest

# Login to ECR
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin 670089840758.dkr.ecr.eu-west-1.amazonaws.com

# Push to ECR
docker push 670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:latest
```

### 2. Configure Terraform variables

Edit `configuration.application.tfvars`:

```hcl
# Basic Configuration
environment = "production"  # or "dev", "staging"
project     = "apuntador"
region      = "eu-west-1"
cost_center = "engineering"

# Lambda Configuration
lambda_memory_size      = 2048   # MB (128-10240)
lambda_timeout          = 300    # seconds (max 900 for HTTP API)
lambda_ephemeral_storage = 512   # MB (512-10240)

# Container Image
api_image = "670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:latest"

# Application Configuration
secret_key      = "generate-a-secure-random-32-char-key-here"  # REQUIRED
allowed_origins = "https://app.apuntador.io,capacitor://localhost,tauri://localhost"
debug           = false
enable_docs     = false   # true for development

# Cloud Provider Configuration
enabled_cloud_providers = "googledrive,dropbox"  # Comma-separated

# API Gateway Configuration
enable_custom_domain = true
domain_name          = "api.apuntador.io"
zone_id              = "Z123456789ABCDEFGHIJ"  # Route 53 zone

# OpenTelemetry Configuration
enable_otel          = true
otel_service_name    = "apuntador-api"
otel_log_level       = "INFO"
```

### 3. Initialize Terraform

```bash
cd iac/stacks/02.aws.lambda
terraform init
```

### 4. Plan and apply

```bash
# Review changes
terraform plan -var-file=configuration.application.tfvars

# Apply infrastructure
terraform apply -var-file=configuration.application.tfvars
```

## Lambda Function Configuration

### Container Image Requirements

The Lambda function uses a custom container image built from `Dockerfile.lambda`:

```dockerfile
FROM public.ecr.aws/lambda/python:3.14

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && \
    uv pip install --system -r pyproject.toml

# Install OpenTelemetry auto-instrumentation
RUN pip install opentelemetry-instrumentation && \
    opentelemetry-bootstrap --action=install

# Copy application code
COPY src/ ${LAMBDA_TASK_ROOT}/

# Set Lambda handler
CMD ["apuntador.lambda_main.handler"]
```

### Environment Variables (configured in Terraform)

```bash
# Application
SECRET_KEY              # Random 32+ char string for signing tokens
ALLOWED_ORIGINS         # CORS origins (comma-separated)
DEBUG                   # true/false
ENABLE_DOCS             # true/false (Swagger UI)
ENABLED_CLOUD_PROVIDERS # googledrive,dropbox,onedrive

# Infrastructure
INFRASTRUCTURE_PROVIDER = "aws"
SECRETS_PROVIDER        = "aws"
CERTIFICATE_DB_PROVIDER = "aws"
STORAGE_PROVIDER        = "aws"

# AWS Resources (auto-populated by Terraform)
AWS_ACCOUNT_ID
AWS_REGION
DYNAMODB_TABLE_NAME
S3_BUCKET_NAME
SECRETS_ARN_PREFIX

# OpenTelemetry (optional)
OTEL_SERVICE_NAME           = "apuntador-api"
OTEL_PROPAGATORS            = "tracecontext,xray"
OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED = "true"
OTEL_EXPORTER_OTLP_PROTOCOL = "http/protobuf"
OTEL_TRACES_EXPORTER        = "otlp"
OTEL_METRICS_EXPORTER       = "none"
OTEL_LOGS_EXPORTER          = "none"
```

### IAM Permissions

The Lambda execution role has permissions for:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:eu-west-1:*:table/apuntador-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::apuntador-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:eu-west-1:*:secret:apuntador/*"
    },
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

## API Gateway Configuration

### HTTP API vs REST API

This stack uses **API Gateway HTTP API** (not REST API) for:

- Lower cost: $1.00/million vs $3.50/million
- Native Lambda proxy integration
- Built-in CORS support
- Lower latency (p99 ~5ms vs ~10ms)

### Custom Domain Setup

```hcl
# Terraform automatically creates:
# 1. ACM certificate for *.apuntador.io
# 2. API Gateway domain name (api.apuntador.io)
# 3. Route 53 A record -> API Gateway
# 4. API Gateway stage mapping (default -> Lambda)
```

### Request Flow

```
Client Request
  -> DNS (Route 53): api.apuntador.io
  -> API Gateway: HTTPS termination, CORS headers
  -> Lambda: Mangum converts ASGI to Lambda event
  -> FastAPI: Routes to endpoint handler
  -> Response: JSON with CORS headers
```

## OpenTelemetry Configuration

### Auto-Instrumentation without Lambda Layers

Since container images cannot use Lambda layers, OpenTelemetry is installed directly:

```bash
# In Dockerfile.lambda
RUN pip install aws-opentelemetry-distro[otlp]
RUN pip install opentelemetry-instrumentation
RUN opentelemetry-bootstrap --action=install
```

This automatically instruments:
- FastAPI requests/responses
- HTTP client calls (httpx)
- Python logging (Loguru)

### X-Ray Integration

```python
# src/apuntador/core/telemetry.py
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# Lambda sends traces directly to X-Ray via OTLP
exporter = OTLPSpanExporter(
    endpoint="https://xray.eu-west-1.amazonaws.com",
    headers={"Content-Type": "application/x-protobuf"}
)

provider.add_span_processor(BatchSpanProcessor(exporter))
```

### Viewing Traces

```bash
# AWS X-Ray Console
# -> Service Map: Visual graph of service dependencies
# -> Traces: Individual request traces with timing
# -> Analytics: Query traces by status code, latency, etc.

# Or use AWS CLI
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s)
```

## Deployment Workflow

### Initial Deployment

```bash
# 1. Build and push container image
docker build -f Dockerfile.lambda -t apuntador-lambda .
docker tag apuntador-lambda:latest 670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:latest
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin 670089840758.dkr.ecr.eu-west-1.amazonaws.com
docker push 670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:latest

# 2. Deploy infrastructure
cd iac/stacks/02.aws.lambda
terraform init
terraform plan -var-file=configuration.application.tfvars
terraform apply -var-file=configuration.application.tfvars

# 3. Test API
curl https://api.apuntador.io/health
# Expected: {"status": "healthy", "version": "1.0.0"}
```

### Code Updates (without infrastructure changes)

```bash
# 1. Rebuild and push new image
docker build -f Dockerfile.lambda -t apuntador-lambda .
docker tag apuntador-lambda:latest 670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:$(git rev-parse --short HEAD)
docker push 670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:$(git rev-parse --short HEAD)

# 2. Update Lambda function code
aws lambda update-function-code \
  --function-name apuntador3-api \
  --image-uri 670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:$(git rev-parse --short HEAD)

# 3. Wait for update to complete
aws lambda wait function-updated --function-name apuntador3-api

# 4. Test
curl https://api.apuntador.io/health
```

## Monitoring and Troubleshooting

### CloudWatch Logs

```bash
# View recent logs
aws logs tail /aws/lambda/apuntador3-api --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/apuntador3-api \
  --filter-pattern "ERROR"

# Query with Insights
aws logs start-query \
  --log-group-name /aws/lambda/apuntador3-api \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /500/ | sort @timestamp desc | limit 20'
```

### Lambda Metrics

Key metrics in CloudWatch:

- **Invocations**: Total requests
- **Duration**: Average execution time
- **Errors**: Failed invocations
- **Throttles**: Requests rejected due to concurrency limits
- **ConcurrentExecutions**: Number of simultaneous invocations
- **ProvisionedConcurrency**: Reserved capacity (if configured)

### Performance Tuning

```hcl
# Increase memory for better CPU performance
lambda_memory_size = 3008  # 2 vCPUs at 1769 MB, max 6 vCPUs at 10240 MB

# Reduce cold starts with provisioned concurrency
resource "aws_lambda_provisioned_concurrency_config" "api" {
  function_name = aws_lambda_function.api.function_name
  provisioned_concurrent_executions = 5  # Keeps 5 instances warm
}

# Increase ephemeral storage for large uploads
lambda_ephemeral_storage = 10240  # 10 GB
```

### Common Issues

#### Issue: Lambda timeout (504 Gateway Timeout)

**Symptoms**: API returns 504 after 30 seconds (API Gateway limit) or 300 seconds (Lambda timeout)

**Solution**:
```hcl
# Increase Lambda timeout
lambda_timeout = 900  # Max for HTTP API integration

# Or reduce timeout for faster failures
lambda_timeout = 30  # Fail fast if slow
```

#### Issue: High memory usage or OOM errors

**Symptoms**: Lambda crashes with "Task timed out after X seconds" or memory errors

**Solution**:
```hcl
# Increase memory (also increases CPU)
lambda_memory_size = 4096  # 4 GB

# Check memory usage in logs
# Look for: "Max Memory Used: X MB"
```

#### Issue: Cold start latency (>1s response time)

**Symptoms**: First request after idle takes 5-10 seconds

**Solutions**:
1. Reduce container size (optimize Dockerfile)
2. Use provisioned concurrency (keeps instances warm)
3. Increase memory (faster initialization)

```hcl
# Provisioned concurrency (costs ~$0.015/hour per instance)
resource "aws_lambda_provisioned_concurrency_config" "api" {
  function_name = aws_lambda_function.api.function_name
  provisioned_concurrent_executions = 2
}
```

#### Issue: OTEL traces not appearing in X-Ray

**Symptoms**: No traces in X-Ray console despite OTEL enabled

**Diagnostics**:
```bash
# Check Lambda logs for OTEL output
aws logs tail /aws/lambda/apuntador3-api --follow | grep -i otel

# Verify environment variables
aws lambda get-function-configuration --function-name apuntador3-api | jq '.Environment.Variables | with_entries(select(.key | startswith("OTEL")))'
```

**Solution**:
```hcl
# Ensure X-Ray tracing is enabled
tracing_config {
  mode = "PassThrough"  # Or "Active" for X-Ray SDK
}

# Verify OTEL env vars in Terraform
environment {
  variables = {
    OTEL_SERVICE_NAME    = "apuntador-api"
    OTEL_PROPAGATORS     = "tracecontext,xray"
    OTEL_TRACES_EXPORTER = "otlp"
  }
}
```

## Cost Analysis

### Monthly Cost Estimate (Production)

**Assumptions**:
- 10 million requests/month
- Average 500ms execution time
- 2048 MB memory
- 1 GB CloudWatch Logs
- No provisioned concurrency

**Breakdown**:
- **Lambda compute**: 10M * 1 GB-sec * $0.0000166667 = $20.00
- **Lambda requests**: 10M * $0.20/million = $2.00
- **API Gateway**: 10M * $1.00/million = $10.00
- **DynamoDB**: 1M reads/writes * $0.25/million = $0.50
- **S3**: 100 GB * $0.023/GB = $2.30
- **CloudWatch Logs**: 1 GB * $0.50/GB = $0.50
- **Secrets Manager**: 5 secrets * $0.40 = $2.00
- **X-Ray**: 10M traces * $5.00/million = $50.00 (first 100K free)
  - **Note**: Disable X-Ray or use sampling to reduce costs

**Total (without X-Ray)**: ~$37.30/month
**Total (with X-Ray)**: ~$87.30/month

### Cost Optimization Tips

1. **Reduce X-Ray costs**: Use sampling (1 in 100 traces)
   ```hcl
   environment {
     variables = {
       AWS_XRAY_SAMPLING_RATE = "0.01"  # 1% of requests
     }
   }
   ```

2. **Right-size memory**: Monitor "Max Memory Used" in logs
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/apuntador3-api \
     --filter-pattern "Max Memory Used"
   ```

3. **Use S3 Intelligent-Tiering**: Automatic cost optimization for storage

4. **Enable DynamoDB Auto Scaling**: Pay only for what you use

5. **CloudWatch Logs retention**: Reduce from indefinite to 30 days
   ```hcl
   resource "aws_cloudwatch_log_group" "lambda" {
     retention_in_days = 30  # vs never (indefinite)
   }
   ```

## Comparison: Lambda vs ECS Fargate

| Feature | Lambda (this stack) | ECS Fargate (01.applications) |
|---------|---------------------|-------------------------------|
| **Cost/month** | ~$37-87 | ~$58-73 |
| **Cold start** | 1-5s (container) | None (always running) |
| **Scalability** | 1-1000 concurrent | Manual scaling |
| **Idle cost** | $0 | ~$25 (min 1 task) |
| **VPC required** | No | Yes |
| **NAT cost** | $0 | $3.50 (NAT instance) |
| **Maintenance** | Minimal | Medium (ECS updates) |
| **Best for** | Variable traffic | Consistent traffic |

**When to use Lambda**:
- Unpredictable traffic patterns
- Low request volume (<100 req/sec)
- Cost optimization priority
- Minimal infrastructure maintenance

**When to use ECS Fargate**:
- Consistent high traffic
- Sub-second response time requirements
- Complex networking (VPN, VPC peering)
- Long-running background tasks

## Security Best Practices

1. **Secrets Management**: Never hardcode credentials in environment variables
   ```hcl
   # Store in Secrets Manager
   resource "aws_secretsmanager_secret" "oauth_google" {
     name = "apuntador/oauth/google"
   }
   
   # Reference in Lambda
   environment {
     variables = {
       GOOGLE_CLIENT_SECRET_ARN = aws_secretsmanager_secret.oauth_google.arn
     }
   }
   ```

2. **IAM Least Privilege**: Grant only required permissions
   ```hcl
   # Bad: Grant all DynamoDB permissions
   # "dynamodb:*"
   
   # Good: Grant specific actions on specific tables
   "dynamodb:GetItem",
   "dynamodb:PutItem",
   "dynamodb:UpdateItem"
   ```

3. **API Gateway Throttling**: Prevent abuse
   ```hcl
   resource "aws_api_gateway_stage" "prod" {
     throttle_settings {
       burst_limit = 5000   # Max concurrent requests
       rate_limit  = 10000  # Max requests per second
     }
   }
   ```

4. **CORS Configuration**: Restrict allowed origins
   ```hcl
   allowed_origins = "https://app.apuntador.io"  # Production domain only
   # NOT: "*" (allows any origin)
   ```

5. **CloudWatch Logs Encryption**: Enable KMS encryption
   ```hcl
   resource "aws_cloudwatch_log_group" "lambda" {
     kms_key_id = aws_kms_key.logs.arn
   }
   ```

## Outputs

After successful deployment, Terraform outputs:

```hcl
api_url                = "https://api.apuntador.io"
lambda_function_name   = "apuntador3-api"
lambda_function_arn    = "arn:aws:lambda:eu-west-1:670089840758:function:apuntador3-api"
api_gateway_id         = "abcd123456"
dynamodb_table_name    = "apuntador-certificates"
s3_bucket_name         = "apuntador-storage-prod"
cloudwatch_log_group   = "/aws/lambda/apuntador3-api"
```

Use these for CI/CD pipelines, monitoring, or manual debugging.

## Next Steps

1. **Set up CI/CD**: Automate container builds and Lambda updates
2. **Configure monitoring**: CloudWatch alarms for errors, latency, throttling
3. **Enable WAF**: Add AWS WAF to API Gateway for DDoS protection
4. **Implement caching**: Add CloudFront CDN for static responses
5. **Load testing**: Use k6 or Locust to validate scalability
6. **Cost optimization**: Review AWS Cost Explorer monthly

## References

- [AWS Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [API Gateway HTTP API](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [OpenTelemetry for Lambda](https://aws-otel.github.io/docs/getting-started/lambda)
- [Mangum (ASGI adapter)](https://mangum.io/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/docker/)


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
2. `AVAILABLE` - Ready to use 
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

### ECS tasks can't reach external APIs (Dropbox, Google, etc.)

**Symptom**: Timeout errors when calling `www.dropbox.com`, `accounts.google.com`, etc.

**Cause**: Private subnets need internet access via NAT Instance.

**Debug**:
```bash
# 1. Verify NAT instance is running
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names prod-apuntador-nat-instance-* \
  --region eu-west-1

# 2. Check NAT instance health
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names prod-apuntador-nat-instance-* \
  --query 'AutoScalingGroups[0].Instances[0].InstanceId' \
  --output text)

aws ec2 describe-instance-status \
  --instance-ids $INSTANCE_ID \
  --region eu-west-1

# 3. Verify source/dest check is disabled
aws ec2 describe-instance-attribute \
  --instance-id $INSTANCE_ID \
  --attribute sourceDestCheck \
  --region eu-west-1
# Should return: "SourceDestCheck": {"Value": false}

# 4. Check private subnet route tables have route to NAT
aws ec2 describe-route-tables \
  --filters "Name=tag:Name,Values=*private*" \
  --region eu-west-1 \
  --query 'RouteTables[*].Routes'
# Should show route: 0.0.0.0/0  eni-xxxxx (NAT instance ENI)

# 5. Test from ECS task (via SSM Session Manager to NAT instance)
aws ssm start-session --target $INSTANCE_ID
# Inside instance:
curl -I https://www.dropbox.com  # Should return 200
```

**Fix** if routes are missing:
```bash
# Get NAT instance ENI
NAT_ENI=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId' \
  --output text)

# Add route to each private route table
for RT_ID in $(aws ec2 describe-route-tables \
  --filters "Name=tag:Name,Values=*private*" \
  --query 'RouteTables[*].RouteTableId' \
  --output text); do
  aws ec2 create-route \
    --route-table-id $RT_ID \
    --destination-cidr-block 0.0.0.0/0 \
    --network-interface-id $NAT_ENI \
    --region eu-west-1
done
```

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
- API Gateway  VPC Link  ALB  ECS request flow
- DynamoDB queries
- S3 operations
- External HTTP calls (OAuth providers)

### Container Insights

View ECS metrics in CloudWatch:
- **Container CPU/Memory utilization**
- **Network traffic**
- **Task count**
- **ALB request/response metrics**

Access via CloudWatch Console  Container Insights  ECS Clusters

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
| **NAT Instance** | t4g.nano EC2 | 24/7 | ~$3.50 |
| **NAT Data Transfer** | Outbound internet | 10 GB (OAuth APIs) | ~$0.10 |
| **API Gateway HTTP** | Regional API | 1M requests | ~$1.00 |
| **VPC Endpoints (Interface)** | 3 endpoints (ECR API, ECR DKR, Logs) | 24/7, 1 GB transfer | ~$21.00 |
| **VPC Endpoints (Gateway)** | 2 endpoints (DynamoDB, S3) | Unlimited | **FREE** |
| **DynamoDB** | On-demand | 1 GB storage, 100K R/W | ~$1.50 |
| **S3** | Standard | 10 GB storage, 1K requests | ~$0.25 |
| **ECR** | Private registry | 5 GB images | ~$0.50 |
| **CloudWatch Logs** | 2 log groups | 5 GB ingestion, 7-day retention | ~$2.50 |
| **CloudWatch Metrics** | Custom metrics | Container Insights enabled | ~$3.00 |
| **Data Transfer** | VPC  Internet | 10 GB outbound (API responses) | ~$0.90 |
| **Route 53** | Hosted zone + queries | 1 hosted zone, 1M queries | ~$0.50 |
| **ACM Certificate** | Regional cert | *.apuntador.io | **FREE** |
| **X-Ray** | Distributed tracing | 100K traces/month | **FREE** (within free tier) |
| | | | |
| **Total (Development)** | 1 task, minimal traffic | ~100K requests/month | **~$36/month** |
| **Total (Production)** | 2 tasks, moderate traffic | ~1M requests/month | **~$73/month** |
| **Total (High Traffic)** | 5 tasks, high traffic | ~10M requests/month | **~$155/month** |

### Cost Breakdown by Category

```
Infrastructure (always-on): ~$63/month
 ECS Fargate (2 tasks):        $14
 ALB:                           $18
 VPC Link:                      $7
 NAT Instance (t4g.nano):       $3.50
 VPC Endpoints (3 × $7):       $21

Variable costs: ~$10/month (1M requests)
 API Gateway:                   $1
 DynamoDB:                      $1.50
 CloudWatch Logs:               $2.50
 CloudWatch Metrics:            $3
 Data Transfer:                 $1.00
 S3:                            $0.25
 ECR:                           $0.50
 Route 53:                      $0.50
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
| **Cold starts** |  Never |  Yes (1-3s) |
| **Max timeout** |  Unlimited | 15 minutes |
| **Concurrent requests** | ~200 per task | 1000 default limit |
| **WebSocket support** |  Yes |  No (need API Gateway WS) |
| **Total (1M req/mo)** | ~$70/month | ~$6/month |
| **Total (10M req/mo)** | ~$150/month | ~$15/month |

**When ECS is worth it:**
-  High traffic (>10M requests/month)
-  Long-running requests (>15 minutes)
-  WebSocket connections
-  No cold start tolerance
-  Consistent performance requirements

**When Lambda is better:**
-  Low/sporadic traffic (<1M requests/month)
-  Short requests (<15 minutes)
-  Cold starts acceptable (1-3s)
-  Cost is primary concern

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
1.  ALB never exposed to internet
2.  SSL/TLS termination at API Gateway (managed certificates)
3.  DDoS protection via AWS Shield (API Gateway)
4.  WAF integration available (API Gateway)
5.  Throttling and rate limiting (API Gateway)

**Cost trade-off:**
- Additional ~$7/month for VPC Link
- But enables future WAF rules, API caching, usage plans

### Why private subnets + VPC Endpoints instead of NAT Gateway?

**Cost savings:**
- NAT Gateway: ~$96/month (3 AZ × $32/mo)
- VPC Endpoints: ~$21/month (3 interfaces × $7/mo)
- **Savings: $75/month = $900/year**

**Performance:**
-  Lower latency (direct connection to AWS services)
-  No bandwidth bottleneck (NAT Gateway throughput limits)
-  Higher reliability (no single point of failure)

### Why ECS Fargate instead of Lambda?

**For Apuntador specifically:**
-  High traffic expected (OAuth flows)
-  Cold starts unacceptable for user experience
-  Predictable costs (flat rate vs pay-per-invocation)
-  Future WebSocket support
-  Longer request timeout (OAuth redirects)

**If traffic is low (<1M requests/month), Lambda is more cost-effective.**

### Why ADOT sidecar instead of Lambda Layer?

**Advantages:**
1.  More granular control over OpenTelemetry configuration
2.  Separate logs for telemetry vs application
3.  Better resource isolation
4.  Future: custom OTEL collector config
5.  Compatible with X-Ray, CloudWatch, and third-party APM

**Cost:** Minimal overhead (~20 MB memory, negligible CPU)

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/impalah/apuntador-backend/issues
- **Documentation**: https://github.com/impalah/apuntador-backend/docs
- **AWS Support**: For infrastructure-related issues

## License

This infrastructure code is part of the Apuntador project. See [LICENSE](../../../LICENSE) for details.
