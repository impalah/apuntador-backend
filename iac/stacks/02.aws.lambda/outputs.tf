################################################################################
# Lambda Function Outputs
################################################################################

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = module.apuntador-api.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = module.apuntador-api.function_arn
}

output "lambda_log_group" {
  description = "CloudWatch log group for Lambda function"
  value       = module.apuntador-api.lambda_log_group_name
}

################################################################################
# Provisioned Concurrency Outputs
################################################################################

output "provisioned_concurrency_enabled" {
  description = "Whether provisioned concurrency is enabled"
  value       = var.enable_provisioned_concurrency
}

output "lambda_autoscaling_enabled" {
  description = "Whether Lambda auto scaling is enabled"
  value       = var.enable_provisioned_concurrency && var.enable_lambda_autoscaling
}

output "lambda_alias_arn" {
  description = "ARN of the Lambda alias (used for provisioned concurrency)"
  value       = module.apuntador-api.lambda_alias_arn
}

output "autoscaling_configuration" {
  description = "Auto scaling configuration summary"
  value = var.enable_provisioned_concurrency && var.enable_lambda_autoscaling ? {
    enabled      = true
    min_capacity = var.lambda_autoscaling_min_capacity
    max_capacity = var.lambda_autoscaling_max_capacity
    target_value = var.lambda_autoscaling_target_value
    estimated_monthly_cost = "$${var.lambda_autoscaling_min_capacity * 11}-${var.lambda_autoscaling_max_capacity * 11}"
  } : {
    enabled                = false
    fixed_instances        = var.enable_provisioned_concurrency ? var.provisioned_concurrent_executions : 0
    estimated_monthly_cost = var.enable_provisioned_concurrency ? "$${var.provisioned_concurrent_executions * 11}" : "$0 (pay per use only)"
  }
}

################################################################################
# API Gateway Outputs
################################################################################

output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = module.api-gateway.apigatewayv2_api_api_endpoint
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = module.api-gateway.apigatewayv2_api_id
}

output "custom_domain_url" {
  description = "Custom domain URL (if configured)"
  value       = var.domain_name != null ? "https://${var.domain_name}" : "Not configured"
}

