# AWS Production Deployment Guide - Apuntador Backend

## Overview

This guide covers deploying the Apuntador Backend to AWS Lambda with full production infrastructure including:

-  Lambda function with container image from ECR
-  API Gateway HTTP API with proxy+ integration
-  Custom domain: `api.apuntador.io`
-  ACM certificate for `*.apuntador.io`
-  Route 53 DNS records (A and AAAA)
-  CloudWatch log groups with retention policies
-  API Gateway access logs
-  IAM policies for DynamoDB, S3, Secrets Manager

## Prerequisites

### Required Tools
- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- Access to AWS account `670089840758`
- Route 53 hosted zone: `Z057297615K0A1393FHLE` (apuntador.io)

### Required Permissions
- Lambda: Create/Update functions
- API Gateway: Create/Update APIs, custom domains, stages
- ACM: Create/Validate certificates
- Route 53: Create/Update DNS records
- CloudWatch: Create log groups
- IAM: Create/Attach policies
- S3: Read/Write access to `press-any-key-devops` bucket (for Terraform state)

### Terraform Backend

The Terraform state is stored in AWS S3 for team collaboration and state integrity.

**Backend Configuration:**
- **S3 Bucket**: `press-any-key-devops` (eu-west-1)
- **State File**: `apuntador.io/backend/terraform.tfstate`
- **Config File**: `iac/stacks/01.applications/application.backend.conf`

The backend is already configured. Terraform will automatically use it during initialization.

## Infrastructure Components

### 1. Lambda Function
- **Name**: `production-apuntador-api`
- **Runtime**: Container (Python 3.12)
- **Image**: `670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:1.0.3`
- **Memory**: 2048 MB
- **Timeout**: 300 seconds
- **Region**: eu-west-1

### 2. API Gateway
- **Type**: HTTP API (API Gateway v2)
- **Integration**: AWS_PROXY to Lambda
- **Stage**: `$default` (auto-deploy)
- **Throttling**: 10,000 requests/sec, burst 5,000

### 3. Custom Domain
- **Domain**: api.apuntador.io
- **Certificate**: ACM `*.apuntador.io` (Regional, TLS 1.2)
- **DNS**: Route 53 A and AAAA records

### 4. Logging
- **Lambda logs**: `/aws/lambda/production-apuntador-api` (7 days retention)
- **API Gateway logs**: `/aws/apigateway/production-apuntador-api` (7 days retention)
- **Format**: JSON with request ID, IP, method, status, errors

## Deployment Steps

### Step 1: Navigate to IAC Directory
```bash
cd /Users/linus/projects/press-any-key/apuntador-backend/iac/stacks/01.applications
```

### Step 2: Review Configuration
Check `configuration.application.tfvars` for correct values:

```hcl
# Domain & SSL Configuration
domain_name            = "api.apuntador.io"
route53_zone_id        = "Z057297615K0A1393FHLE"

# Logging Configuration
lambda_log_retention_days      = 7
api_gateway_log_retention_days = 7
```

### Step 3: Initialize Terraform

Initialize Terraform with the S3 backend configuration:

```bash
terraform init -backend-config=application.backend.conf
```

This command will:
- Download required providers (AWS)
- Configure S3 backend for remote state storage
- Connect to existing state file at `s3://press-any-key-devops/apuntador.io/backend/terraform.tfstate`

**Expected output:**
```
Initializing the backend...

Successfully configured the backend "s3"! Terraform will automatically
use this backend unless the backend configuration changes.

Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 4.0"...
- Installing hashicorp/aws v4.x.x...

Terraform has been successfully initialized!
```

### Step 4: Validate Configuration
```bash
terraform validate
```

### Step 5: Plan Deployment
```bash
terraform plan -var-file=configuration.application.tfvars
```

Review the plan carefully. Expected resources to be created:
- `aws_acm_certificate.api_certificate[0]` - ACM certificate
- `aws_route53_record.certificate_validation[...]` - DNS validation records
- `aws_acm_certificate_validation.api_certificate[0]` - Certificate validation
- `aws_apigatewayv2_domain_name.api_domain[0]` - Custom domain
- `aws_apigatewayv2_stage.default[0]` - API Gateway stage
- `aws_apigatewayv2_api_mapping.api_mapping[0]` - Domain mapping
- `aws_route53_record.api_a_record[0]` - A record
- `aws_route53_record.api_aaaa_record[0]` - AAAA record
- `aws_cloudwatch_log_group.lambda_logs` - Lambda log group
- `aws_cloudwatch_log_group.api_gateway_logs[0]` - API Gateway log group
- Lambda function, IAM policies, API Gateway resources

### Step 6: Apply Configuration
```bash
terraform apply -var-file=configuration.application.tfvars
```

Type `yes` when prompted. Deployment takes approximately **5-10 minutes** due to:
- ACM certificate creation (1 min)
- DNS validation propagation (3-5 min)
- API Gateway configuration (1-2 min)

### Step 7: Verify Outputs
After successful deployment, review outputs:

```bash
terraform output
```

Expected outputs:
- `api_endpoint`: `https://api.apuntador.io`
- `certificate_arn`: ARN of ACM certificate
- `api_domain_name`: `api.apuntador.io`
- `cloudwatch_log_group_lambda`: `/aws/lambda/production-apuntador-api`
- `cloudwatch_log_group_api_gateway`: `/aws/apigateway/production-apuntador-api`

## Post-Deployment Verification

### 1. Test Health Endpoint
```bash
curl https://api.apuntador.io/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.3"
}
```

### 2. Test OAuth Authorization (Google Drive)
```bash
curl -X POST https://api.apuntador.io/oauth/authorize/googledrive \
  -H "Content-Type: application/json" \
  -H "X-Client-Cert: [BASE64_ENCODED_CERTIFICATE]" \
  -d '{
    "redirect_uri": "https://apuntador.app/oauth-callback",
    "state": "test-state"
  }'
```

### 3. Check CloudWatch Logs
```bash
# Lambda logs
aws logs tail /aws/lambda/production-apuntador-api --follow --region eu-west-1

# API Gateway logs
aws logs tail /aws/apigateway/production-apuntador-api --follow --region eu-west-1
```

### 4. Verify DNS Resolution
```bash
# Should resolve to API Gateway
dig api.apuntador.io

# IPv6
dig api.apuntador.io AAAA
```

### 5. Test SSL Certificate
```bash
openssl s_client -connect api.apuntador.io:443 -servername api.apuntador.io < /dev/null
```

Certificate should show:
- Issuer: Amazon
- Subject: `*.apuntador.io`
- Valid dates within expected range

## Configuration Files Modified

### New Files Created
1. **`02.domain-ssl.tf`** (240 lines)
   - ACM certificate with DNS validation
   - API Gateway custom domain configuration
   - Route 53 A and AAAA records
   - CloudWatch log groups
   - API Gateway stage with access logs

### Modified Files
1. **`variables.tf`**
   - Added `domain_name` variable
   - Added `route53_zone_id` variable
   - Added `certificate_arn` variable (optional)
   - Added logging retention variables

2. **`configuration.application.tfvars`**
   - Set `domain_name = "api.apuntador.io"`
   - Set `route53_zone_id = "Z057297615K0A1393FHLE"`
   - Set logging retention to 7 days

3. **`outputs.tf`**
   - Added active outputs section with domain and logging info

4. **`modules/api-gateway/outputs.tf`**
   - Added `api_gateway_endpoint` output
   - Added `api_gateway_execution_arn` output

## Architecture Diagram

```

                         Route 53                            
              Zone: apuntador.io (Z057297615...)             
                                                             
  A Record: api.apuntador.io  API Gateway                  
  AAAA Record: api.apuntador.io  API Gateway (IPv6)        

                       
                        DNS Resolution
                       

                    ACM Certificate                          
                   *.apuntador.io                            
                   (TLS 1.2, Regional)                       

                       
                        SSL/TLS
                       

              API Gateway HTTP API (v2)                      
                                                             
  Custom Domain: api.apuntador.io                           
  Stage: $default (auto-deploy)                             
  Integration: AWS_PROXY                                    
  Throttling: 10,000 req/s, burst 5,000                     
                                                             
  Access Logs  CloudWatch                                  

                       
                        Proxy+
                       

                  Lambda Function                            
            production-apuntador-api                         
                                                             
  Runtime: Container (Python 3.12)                          
  Memory: 2048 MB                                           
  Timeout: 300s                                             
  Image: ECR (1.0.3)                                        
                                                             
  Logs  CloudWatch (7 days retention)                      
                                                             
  Environment:                                              
  - OAuth credentials (Google Drive, Dropbox)               
  - AWS resources (DynamoDB, S3, Secrets)                   
  - mTLS configuration                                      

                       
                        IAM Policies
                       

                  AWS Resources                              
                                                             
  DynamoDB: apuntador-tls-certificates                      
  S3: apuntador.io-tls-cert-storage                         
  Secrets Manager: apuntador/*                              

```

## Environment Variables

The Lambda function has access to the following environment variables:

### Application Configuration
- `HOST`: 0.0.0.0
- `PORT`: 8000
- `DEBUG`: false
- `SECRET_KEY`: [from tfvars]
- `ALLOWED_ORIGINS`: https://apuntador.app,capacitor://localhost,tauri://localhost
- `LOG_LEVEL`: INFO
- `LOG_FORMAT`: json
- `ENABLE_REQUEST_LOGGING`: true

### Infrastructure Configuration
- `INFRASTRUCTURE_PROVIDER`: aws
- `AWS_REGION`: eu-west-1
- `AWS_DYNAMODB_TABLE`: apuntador-tls-certificates
- `AWS_S3_BUCKET`: apuntador.io-tls-cert-storage
- `AWS_SECRETS_PREFIX`: apuntador
- `AUTO_CREATE_RESOURCES`: true

### OAuth Configuration
- `GOOGLE_CLIENT_ID`: [from tfvars]
- `GOOGLE_CLIENT_SECRET`: [from tfvars]
- `GOOGLE_REDIRECT_URI`: https://api.apuntador.app/oauth/callback/googledrive
- `DROPBOX_CLIENT_ID`: [from tfvars]
- `DROPBOX_CLIENT_SECRET`: [from tfvars]
- `DROPBOX_REDIRECT_URI`: apuntador://oauth-callback

## Troubleshooting

### Certificate Validation Stuck
**Issue**: ACM certificate validation takes > 10 minutes

**Solution**:
1. Check Route 53 records are created:
   ```bash
   aws route53 list-resource-record-sets --hosted-zone-id Z057297615K0A1393FHLE
   ```
2. Verify DNS propagation:
   ```bash
   dig _<hash>.apuntador.io CNAME
   ```
3. Wait up to 30 minutes for full propagation

### API Gateway 502 Bad Gateway
**Issue**: Requests return 502 error

**Solution**:
1. Check Lambda function logs:
   ```bash
   aws logs tail /aws/lambda/production-apuntador-api --since 5m
   ```
2. Verify Lambda has correct IAM permissions
3. Test Lambda directly:
   ```bash
   aws lambda invoke --function-name production-apuntador-api response.json
   ```

### Custom Domain Not Working
**Issue**: `api.apuntador.io` doesn't resolve or returns certificate error

**Solution**:
1. Verify API mapping:
   ```bash
   aws apigatewayv2 get-api-mappings --domain-name api.apuntador.io
   ```
2. Check certificate is attached:
   ```bash
   aws apigatewayv2 get-domain-name --domain-name api.apuntador.io
   ```
3. Verify Route 53 A record points to correct target

### CloudWatch Logs Not Appearing
**Issue**: No logs in CloudWatch log groups

**Solution**:
1. Check log group exists:
   ```bash
   aws logs describe-log-groups --log-group-name-prefix /aws/lambda/production-apuntador-api
   ```
2. Verify Lambda has CloudWatch Logs permissions (auto-created by Lambda module)
3. Wait 1-2 minutes for first logs to appear

## Rollback Procedure

If deployment fails or causes issues:

```bash
# Destroy only the new resources (careful with this)
terraform destroy -target=aws_acm_certificate.api_certificate -var-file=configuration.application.tfvars

# Or rollback everything
terraform destroy -var-file=configuration.application.tfvars
```

**Note**: This will NOT delete:
- DynamoDB table (apuntador-tls-certificates)
- S3 bucket (apuntador.io-tls-cert-storage)
- Secrets Manager secrets
- ECR repository

## Cost Estimate

Monthly costs for production deployment (eu-west-1):

- **Lambda**: ~$0.20/GB-hour  ~$10/month (2GB, moderate usage)
- **API Gateway**: $1.00/million requests  ~$5/month (5M requests)
- **CloudWatch Logs**: $0.50/GB ingested  ~$2/month (4GB/month)
- **Route 53**: $0.50/hosted zone + $0.40/million queries  ~$1/month
- **ACM Certificate**: Free (for AWS resources)
- **Data Transfer**: $0.09/GB out  Variable (depends on usage)

**Estimated Total**: $18-25/month for moderate production usage

## Maintenance

### Update Lambda Function
```bash
# Update container image tag in configuration.application.tfvars
api_image = "670089840758.dkr.ecr.eu-west-1.amazonaws.com/apuntador/backend:1.0.4"

# Apply changes
terraform apply -var-file=configuration.application.tfvars
```

### Rotate OAuth Credentials
```bash
# Update credentials in configuration.application.tfvars
# Apply changes
terraform apply -var-file=configuration.application.tfvars
```

### Adjust Log Retention
```bash
# Update retention days in configuration.application.tfvars
lambda_log_retention_days      = 14
api_gateway_log_retention_days = 14

# Apply changes
terraform apply -var-file=configuration.application.tfvars
```

### Renew Certificate
ACM certificates auto-renew 60 days before expiration. No manual intervention needed.

## Security Considerations

1. **mTLS Authentication**: Client certificates validated via `X-Client-Cert` header
2. **CORS**: Restricted to `https://apuntador.app`, Capacitor, Tauri
3. **Secrets**: OAuth credentials stored in Terraform state (encrypt state backend)
4. **Logging**: PII and sensitive data filtered in CloudWatch logs
5. **IAM**: Least privilege policies for Lambda function
6. **TLS**: Minimum TLS 1.2 enforced on API Gateway
7. **Throttling**: Rate limiting enabled (10,000 req/s)

## Next Steps

1.  Deploy infrastructure with Terraform
2.  Update frontend redirect URIs to use `api.apuntador.io`
3.  Update mobile app OAuth configuration
4.  Set up monitoring and alarms in CloudWatch
5.  Configure backup and disaster recovery
6.  Implement CI/CD pipeline for automated deployments

## Support

For issues or questions:
- Check CloudWatch logs first
- Review Terraform plan/apply output
- Consult AWS documentation for service-specific issues
- Check backend application logs for application errors

## References

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [API Gateway v2 Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [ACM Certificate Validation](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
