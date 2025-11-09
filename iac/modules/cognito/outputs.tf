output "aws_cognito_user_pool-userpool_id" {
  value = aws_cognito_user_pool.userpool.id
}

output "aws_cognito_user_pool-userpool_arn" {
  value = aws_cognito_user_pool.userpool.arn
}

output "aws_cognito_user_pool_client_ids" {
  value = { for k, v in aws_cognito_user_pool_client.api_client : k => v.id }
}

output "aws_cognito_user_pool_client_secrets" {
  value = { for k, v in aws_cognito_user_pool_client.api_client : k => v.client_secret }
}

output "aws_cognito_user_pool-user_client_id" {
  value = aws_cognito_user_pool_client.public_client.id
}

output "aws_cognito_user_pool-domain" {
  value = aws_cognito_user_pool_domain.cognito-domain.domain
}

output "url_base" {
  value = aws_cognito_user_pool.userpool.endpoint
}

