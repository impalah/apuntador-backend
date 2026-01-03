####################################################################
# ECS Service Auto Scaling
####################################################################

# Auto Scaling Target
resource "aws_appautoscaling_target" "ecs_target" {
  count              = var.enable_autoscaling ? 1 : 0
  max_capacity       = var.autoscaling_max_capacity
  min_capacity       = var.autoscaling_min_capacity
  resource_id        = "service/${aws_ecs_cluster.apuntador.name}/${aws_ecs_service.apuntador.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.apuntador]
}

####################################################################
# CPU-based Auto Scaling Policy
####################################################################

resource "aws_appautoscaling_policy" "ecs_cpu" {
  count              = var.enable_autoscaling ? 1 : 0
  name               = "${var.environment}-${var.project}-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    target_value       = var.autoscaling_cpu_target
    scale_in_cooldown  = var.autoscaling_scale_in_cooldown
    scale_out_cooldown = var.autoscaling_scale_out_cooldown
  }
}

####################################################################
# Memory-based Auto Scaling Policy
####################################################################

resource "aws_appautoscaling_policy" "ecs_memory" {
  count              = var.enable_autoscaling ? 1 : 0
  name               = "${var.environment}-${var.project}-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }

    target_value       = var.autoscaling_memory_target
    scale_in_cooldown  = var.autoscaling_scale_in_cooldown
    scale_out_cooldown = var.autoscaling_scale_out_cooldown
  }
}

####################################################################
# ALB Request Count Per Target Auto Scaling Policy
####################################################################

resource "aws_appautoscaling_policy" "ecs_request_count" {
  count              = var.enable_autoscaling ? 1 : 0
  name               = "${var.environment}-${var.project}-request-count-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.apuntador.arn_suffix}/${aws_lb_target_group.apuntador.arn_suffix}"
    }

    target_value       = var.autoscaling_request_count_target
    scale_in_cooldown  = var.autoscaling_scale_in_cooldown
    scale_out_cooldown = var.autoscaling_scale_out_cooldown
  }
}

####################################################################
# Outputs
####################################################################

output "autoscaling_enabled" {
  description = "Whether auto scaling is enabled"
  value       = var.enable_autoscaling
}

output "autoscaling_min_capacity" {
  description = "Minimum number of tasks"
  value       = var.enable_autoscaling ? var.autoscaling_min_capacity : null
}

output "autoscaling_max_capacity" {
  description = "Maximum number of tasks"
  value       = var.enable_autoscaling ? var.autoscaling_max_capacity : null
}

output "autoscaling_target_arn" {
  description = "ARN of the auto scaling target"
  value       = var.enable_autoscaling ? aws_appautoscaling_target.ecs_target[0].arn : null
}
