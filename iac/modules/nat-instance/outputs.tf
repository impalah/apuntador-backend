output "nat_instance_ids" {
  description = "IDs of NAT instances"
  value       = aws_autoscaling_group.nat_instance.*.id
}

output "nat_instance_security_group_id" {
  description = "Security group ID for NAT instances"
  value       = aws_security_group.nat_instance.id
}

output "autoscaling_group_name" {
  description = "Auto Scaling Group name"
  value       = aws_autoscaling_group.nat_instance.name
}
