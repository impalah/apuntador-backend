output "function_arn" {
  value = aws_lambda_function.lambda_function.arn
}

output "function_name" {
  value = aws_lambda_function.lambda_function.function_name
}

output "lambda_role_name" {
  value = aws_iam_role.lambda_exec_role.name
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda_exec_role.arn
}

output "lambda_log_group_name" {
  description = "CloudWatch log group name for Lambda function"
  value       = aws_cloudwatch_log_group.lambda_log_group.name
}

output "lambda_alias_arn" {
  description = "ARN of the Lambda alias (for provisioned concurrency)"
  value       = var.enable_provisioned_concurrency ? aws_lambda_alias.live[0].arn : null
}

output "provisioned_concurrency_enabled" {
  description = "Whether provisioned concurrency is enabled"
  value       = var.enable_provisioned_concurrency
}

output "lambda_autoscaling_enabled" {
  description = "Whether Lambda auto scaling is enabled"
  value       = var.enable_provisioned_concurrency && var.enable_lambda_autoscaling
}
