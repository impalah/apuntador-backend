################################################################################
# Logging configuration
################################################################################


resource "aws_cloudwatch_log_group" "LogsLogGroup" {
  name              = format("/%s/%s", var.log_group_prefix, var.log_group_name)
  retention_in_days = var.retention_days
  tags = merge(
    { "Name" = format("/%s/%s", var.log_group_prefix, var.log_group_name) },
    var.tags,
  )
}


