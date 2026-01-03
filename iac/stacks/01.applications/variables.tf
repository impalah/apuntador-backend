
# The home of the variables
variable "tags" {
  description = "External tags map"
  type        = map(string)
  default     = {}
}

variable "region" {
  description = "Set the primary region"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Set environment name"
  type        = string
  default     = ""
}

variable "customer" {
  description = "Set customer name"
  type        = string
  default     = ""
}

variable "cost_center" {
  description = "Cost center associated with the project"
  type        = string
  default     = ""
}

variable "project" {
  description = "Project name"
  type        = string
  default     = ""
}

variable "organization" {
  description = "Organization name (internal)"
  type        = string
  default     = ""
}

variable "map-migrated" {
  description = "Map migrated"
  type        = string
  default     = ""
}

variable "bu-code" {
  description = "Business unit code"
  type        = string
  default     = ""
}

variable "owner" {
  description = "Owner name (internal)"
  type        = string
  default     = ""
}


variable "shared_services_account" {
  description = "Shared services account"
  type        = string
  default     = null
}


# variable "aws_kms_ssm_default_key" {
#   description = "Default key that protects my SSM parameters when no other key is defined (aws kms describe-key --key-id alias/aws/ssm --region region )"
#   type        = string
#   default     = null
# }

variable "vpc_id" {
  description = "Id for the VPC"
  type        = string
  default     = ""
}

variable "vpc_public_subnets_ids" {
  description = "Public subnets"
  type        = set(string)
  default     = []
}

variable "vpc_private_subnets_ids" {
  description = "Private subnets"
  type        = set(string)
  default     = []
}

variable "vpc_db_private_subnets_ids" {
  description = "Private DB subnets"
  type        = set(string)
  default     = []
}

variable "cors_allowed_origins" {
  description = "List of allowed CORS origins for API Gateway"
  type        = list(string)
  default = [
    "https://app.apuntador.io",
    "http://localhost:3000",
    "http://localhost:5173",
    "capacitor://localhost",
    "ionic://localhost",
    "tauri://localhost"
  ]
}

variable "cors_allowed_methods" {
  description = "List of allowed HTTP methods for CORS"
  type        = list(string)
  default     = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
}

variable "cors_allowed_headers" {
  description = "List of allowed headers for CORS"
  type        = list(string)
  default = [
    "content-type",
    "x-amz-date",
    "authorization",
    "x-api-key",
    "x-amz-security-token",
    "x-amz-user-agent",
    "x-client-cert",
    "x-device-id"
  ]
}

variable "cors_expose_headers" {
  description = "List of headers to expose in CORS responses"
  type        = list(string)
  default     = ["content-type", "x-amz-date"]
}

variable "cors_max_age" {
  description = "Maximum age (in seconds) for CORS preflight cache"
  type        = number
  default     = 86400
}

variable "cors_allow_credentials" {
  description = "Whether credentials are allowed in CORS requests"
  type        = bool
  default     = true  # Necesario para Authorization header
}



variable "api_service_name" {
  description = "Service name"
  type        = string
  default     = null
}





variable "namespace_id" {
  description = "Namespace ID"
  type        = string
  default     = null
}

variable "namespace_name" {
  description = "Namespace name"
  type        = string
  default     = null
}

variable "subdomain_name" {
  description = "Subdomain name"
  type        = string
  default     = null
}






variable "api_image" {
  description = "API container image"
  type        = string
  default     = null
}

variable "log_group_prefix" {
  description = "Service Log group prefix"
  type        = string
  default     = null
}

variable "log_group_name" {
  description = "Service Log group name"
  type        = string
  default     = null
}

# ========================================
# Apuntador Backend Configuration
# ========================================

variable "debug" {
  description = "Enable debug mode"
  type        = string
  default     = "false"
}

variable "secret_key" {
  description = "Secret key for signing tokens (min 32 chars)"
  type        = string
  sensitive   = true
}

variable "allowed_origins" {
  description = "Comma-separated list of allowed CORS origins"
  type        = string
  default     = "*"
}

variable "log_level" {
  description = "Logging level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"
}

variable "aws_region" {
  description = "AWS region for infrastructure"
  type        = string
  default     = "eu-west-1"
}

variable "enable_docs" {
  description = "Indicate if the bucket will have documentation enabled"
  type        = bool
  default     = false
}



variable "dynamodb_table_name" {
  description = "DynamoDB table name for certificates"
  type        = string
  default     = "apuntador-certificates"
}

variable "s3_bucket_name" {
  description = "S3 bucket name for storage"
  type        = string
  default     = "apuntador-storage"
}

variable "secrets_prefix" {
  description = "AWS Secrets Manager prefix"
  type        = string
  default     = "apuntador"
}

variable "auto_create_resources" {
  description = "Auto-create AWS resources if they don't exist"
  type        = string
  default     = "true"
}

# Cloud Provider Configuration
variable "enabled_cloud_providers" {
  description = "Comma-separated list of enabled cloud providers (googledrive, dropbox, onedrive)"
  type        = string
  default     = "googledrive,dropbox"
}

# Google Drive OAuth Configuration
variable "google_client_id" {
  description = "Google OAuth client ID"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
}

variable "google_redirect_uri" {
  description = "Google OAuth redirect URI"
  type        = string
}

# Dropbox OAuth Configuration
variable "dropbox_client_id" {
  description = "Dropbox OAuth client ID"
  type        = string
  sensitive   = true
}

variable "dropbox_client_secret" {
  description = "Dropbox OAuth client secret"
  type        = string
  sensitive   = true
}

variable "dropbox_redirect_uri" {
  description = "Dropbox OAuth redirect URI"
  type        = string
}

# ========================================
# Domain & SSL Configuration
# ========================================

variable "domain_name" {
  description = "Custom domain name for API (e.g., api.apuntador.io)"
  type        = string
  default     = null
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID for the domain"
  type        = string
  default     = null
}

variable "certificate_arn" {
  description = "ACM certificate ARN for the domain (optional, will be created if not provided)"
  type        = string
  default     = null
}

# ========================================
# Logging Configuration
# ========================================

variable "lambda_log_retention_days" {
  description = "CloudWatch log retention in days for Lambda"
  type        = number
  default     = 7
}

variable "api_gateway_log_retention_days" {
  description = "CloudWatch log retention in days for API Gateway"
  type        = number
  default     = 7
}


variable "log_format" {
  description = "Log format (json or human)"
  type        = string
  default     = "human"
}

####################################################################
# ECS Configuration
####################################################################

variable "desired_count" {
  description = "Number of ECS tasks to run"
  type        = number
  default     = 2
}

variable "task_cpu" {
  description = "ECS task CPU units (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "256"
}

variable "task_memory" {
  description = "ECS task memory in MB"
  type        = string
  default     = "512"
}

variable "adot_image" {
  description = "Docker image URI for AWS ADOT Collector (ECR private)"
  type        = string
  default     = "670089840758.dkr.ecr.eu-west-1.amazonaws.com/aws-otel-collector:latest"
}
