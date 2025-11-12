# ####################################################################
# # Application configuration
# ####################################################################

module "apuntador-api" {
  source           = "../../modules/lambda"
  environment      = var.environment
  project          = var.project
  function_name    = "apuntador-api"
  function_memory  = "2048"
  function_storage = "512"
  function_timeout = "300"
  image            = var.api_image
  log_retention_days = var.lambda_log_retention_days
  env_variables = {
    # Application Configuration
    HOST                     = "0.0.0.0"
    PORT                     = "8000"
    DEBUG                    = var.debug
    SECRET_KEY               = var.secret_key
    ALLOWED_ORIGINS          = var.allowed_origins
    ENABLE_DOCS              = var.enable_docs
    
    # Logging Configuration
    LOG_LEVEL                = var.log_level
    LOG_FORMAT               = "json"
    ENABLE_REQUEST_LOGGING   = "true"
    
    # Cloud Provider Configuration
    ENABLED_CLOUD_PROVIDERS  = var.enabled_cloud_providers
    
    # Infrastructure Provider (AWS for Lambda)
    INFRASTRUCTURE_PROVIDER  = "aws"
    # AWS_REGION              = var.aws_region
    AWS_DYNAMODB_TABLE      = var.dynamodb_table_name
    AWS_S3_BUCKET           = var.s3_bucket_name
    AWS_SECRETS_PREFIX      = var.secrets_prefix
    AUTO_CREATE_RESOURCES   = var.auto_create_resources
    
    # Google Drive OAuth
    GOOGLE_CLIENT_ID        = var.google_client_id
    GOOGLE_CLIENT_SECRET    = var.google_client_secret
    GOOGLE_REDIRECT_URI     = var.google_redirect_uri
    
    # Dropbox OAuth
    DROPBOX_CLIENT_ID       = var.dropbox_client_id
    DROPBOX_CLIENT_SECRET   = var.dropbox_client_secret
    DROPBOX_REDIRECT_URI    = var.dropbox_redirect_uri
  }

  #   vpc_id          = module.vpc.vpc_id
  #   vpc_subnets_ids = values(module.vpc.private_subnet_ids)

  # depends_on = [
  #   module.cognito
  # ]

}



####################################################################
# IAM Policies for Lambda
####################################################################

# Policy for DynamoDB access
data "aws_iam_policy_document" "lambda_dynamodb_policy" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:DescribeTable",
      "dynamodb:CreateTable"
    ]
    resources = [
      "arn:aws:dynamodb:${var.aws_region}:*:table/${var.dynamodb_table_name}"
    ]
  }
}

resource "aws_iam_role_policy" "lambda_dynamodb_policy" {
  name   = "${var.environment}-${var.project}-lambda-dynamodb"
  role   = module.apuntador-api.lambda_role_name
  policy = data.aws_iam_policy_document.lambda_dynamodb_policy.json
}

# Policy for S3 access
data "aws_iam_policy_document" "lambda_s3_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::${var.s3_bucket_name}",
      "arn:aws:s3:::${var.s3_bucket_name}/*"
    ]
  }
}

resource "aws_iam_role_policy" "lambda_s3_policy" {
  name   = "${var.environment}-${var.project}-lambda-s3"
  role   = module.apuntador-api.lambda_role_name
  policy = data.aws_iam_policy_document.lambda_s3_policy.json
}

# Policy for Secrets Manager access
data "aws_iam_policy_document" "lambda_secrets_policy" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret",
      "secretsmanager:ListSecrets"
    ]
    resources = [
      "arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.secrets_prefix}/*"
    ]
  }
}

resource "aws_iam_role_policy" "lambda_secrets_policy" {
  name   = "${var.environment}-${var.project}-lambda-secrets"
  role   = module.apuntador-api.lambda_role_name
  policy = data.aws_iam_policy_document.lambda_secrets_policy.json
}


####################################################################
# API Gateway
####################################################################

module "api_gateway" {
  source               = "../../modules/api-gateway"
  environment          = var.environment
  project              = var.project
  lambda_function_arn  = module.apuntador-api.function_arn
  lambda_function_name = module.apuntador-api.function_name
  # vpc_id          = var.vpc_id
  # vpc_subnets_ids = var.vpc_private_subnets_ids

  # aws_lb_listener_arn = aws_lb_listener.api_service_listener_rule.arn


  depends_on = [
    module.apuntador-api
  ]

}


# After that, initialize manually the api gateway stage
# Create stage

# aws --profile my_profile apigatewayv2 create-stage --region eu-west-1 --auto-deploy --api-id API_ID --stage-name '$default'




# ####################################################################
# # Outputs
# ####################################################################

output "api_gateway_id" {
  value = module.api_gateway.api_gateway_id
}


