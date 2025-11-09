variable "environment" {
  description = "Set environment name"
  type        = string
  default     = ""
}

variable "function_name" {
  description = "Lambda function name"
  type        = string
  default     = null
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

variable "function_memory" {
  description = "Function assigned memory"
  type        = string
  default     = "256"
}

variable "function_storage" {
  description = "Function assigned storage"
  type        = string
  default     = "512"
}

variable "function_timeout" {
  description = "Timeout"
  type        = string
  default     = "300"
}

variable "function_architectures" {
  description = "Architectures"
  type        = list(string)
  default     = ["x86_64"]
}

variable "function_cmd" {
  description = "CMD override"
  type        = string
  default     = ""
}

variable "image" {
  description = "ECR Image"
  type        = string
  default     = null
}

variable "logs_group_arn" {
  description = "Logs group arn"
  type        = string
  default     = null
}

variable "aws_sns_topic_arn" {
  description = "Topic ARN to subscribe the function to"
  type        = string
  default     = null
}

variable "param_SELECTOR_TYPES" {
  description = "SELECTOR_TYPES parameters"
  type        = string
  default     = null
}

variable "param_SQLALCHEMY_DATABASE_URI" {
  description = "SQLALCHEMY_DATABASE_URI parameters"
  type        = string
  default     = null
}

variable "param_LOG_LEVEL" {
  description = "LOG_LEVEL parameters"
  type        = string
  default     = null
}


variable "function_schedule" {
  description = "Schedule for lambda function"
  type        = string
  default     = "rate(24 hours)"
}


variable "vpc_subnets_ids" {
  description = "RDS subnets"
  type        = set(string)
  default     = []
}

variable "vpc_id" {
  description = "ID of the VPC for the function"
  type        = string
  default     = null
}

variable "region" {
  description = "Set the primary region"
  type        = string
  default     = "us-east-1"
}

variable "env_variables" {
  description = "Map of environment variables for the Lambda function"
  type        = map(string)
  default = {
  }
}

variable "ports" {
  description = "A list of ingress open ports"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}
