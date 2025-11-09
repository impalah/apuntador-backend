output "secret_parameter_arn" {
  value = aws_secretsmanager_secret.custom_secret.arn
}

output "secret_id" {
  value = aws_secretsmanager_secret.custom_secret.id
}

