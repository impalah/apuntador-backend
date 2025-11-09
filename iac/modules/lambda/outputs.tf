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
