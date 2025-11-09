resource "aws_secretsmanager_secret" "custom_secret" {
  name        = var.name
  description = var.description

  tags = merge(
    { "Name" = var.name },
    var.tags,
  )
}

resource "aws_secretsmanager_secret_version" "custom_secret_version" {
  count         = var.value != null ? 1 : 0
  secret_id     = aws_secretsmanager_secret.custom_secret.id
  secret_string = var.value
}

