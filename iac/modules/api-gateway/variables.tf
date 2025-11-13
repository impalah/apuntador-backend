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

variable "cors_allowed_origins" {
  description = "List of allowed CORS origins for API Gateway"
  type        = list(string)
  default = [
    "https://app.apuntador.io",
    "http://localhost:3000",
    "http://localhost:5173"
  ]
}

variable "cors_allowed_methods" {
  description = "List of allowed HTTP methods for CORS"
  type        = list(string)
  default     = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
}

variable "cors_allowed_headers" {
  description = "List of allowed headers for CORS"
  type        = list(string)
  default = [
    "content-type",
    "x-amz-date",
    "authorization",
    "x-api-key",
    "x-amz-security-token",
    "x-amz-user-agent"
  ]
}

variable "cors_expose_headers" {
  description = "List of headers to expose in CORS responses"
  type        = list(string)
  default     = ["content-type", "x-amz-date"]
}

variable "cors_max_age" {
  description = "Maximum age (in seconds) for CORS preflight cache"
  type        = number
  default     = 86400
}

variable "cors_allow_credentials" {
  description = "Whether credentials are allowed in CORS requests"
  type        = bool
  default     = false
}


