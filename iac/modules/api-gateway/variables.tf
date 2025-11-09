variable "environment" {
  description = "Set environment name"
  type        = string
  default     = ""
}

variable "project" {
  description = "Project name"
  type        = string
  default     = ""
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "protocol_type" {
  description = "Protocol type"
  type        = string
  default     = "HTTP"
}

variable "vpc_id" {
  description = "ID of the VPC for the RDS instance"
  type        = string
  default     = null
}

variable "vpc_subnets_ids" {
  description = "Subnets"
  type        = set(string)
  default     = []
}

variable "aws_lb_listener_arn" {
  description = "Public subnet 2 CIDR"
  type        = string
  default     = null
}

variable "lambda_function_arn" {
  description = "Lambda function ARN"
  type        = string
  default     = null
}

variable "lambda_function_name" {
  description = "Lambda function name"
  type        = string
  default     = null
}


