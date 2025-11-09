output "logs_group_name" {
  value = aws_cloudwatch_log_group.LogsLogGroup.name
}

output "logs_group_arn" {
  value = aws_cloudwatch_log_group.LogsLogGroup.arn
}
