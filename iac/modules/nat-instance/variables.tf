variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where NAT instance will be deployed"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs where NAT instance can run"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "List of private subnet CIDRs that will route through NAT"
  type        = list(string)
}

variable "instance_type" {
  description = "EC2 instance type for NAT instance"
  type        = string
  default     = "t4g.nano" # ARM64, cheapest option (~$3.50/month)
}

variable "enable_high_availability" {
  description = "Enable multiple NAT instances across AZs (increases cost)"
  type        = bool
  default     = false # Single instance by default (cost optimization)
}

variable "enable_cloudwatch_metrics" {
  description = "Enable CloudWatch metrics collection"
  type        = bool
  default     = true
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed EC2 monitoring (1-min intervals, extra cost)"
  type        = bool
  default     = false
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed to SSH to NAT instance (empty = disabled)"
  type        = string
  default     = "" # No SSH by default, use SSM Session Manager
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
