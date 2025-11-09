output "api_gateway_id" {
  value = aws_apigatewayv2_api.api.id
}

output "api_gateway_endpoint" {
  description = "API Gateway default endpoint URL"
  value       = aws_apigatewayv2_api.api.api_endpoint
}

output "api_gateway_execution_arn" {
  description = "API Gateway execution ARN"
  value       = aws_apigatewayv2_api.api.execution_arn
}
