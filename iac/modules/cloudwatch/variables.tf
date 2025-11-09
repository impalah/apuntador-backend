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

variable "log_group_prefix" {
  description = "Log group prefix"
  type        = string
  default     = null
}

variable "log_group_name" {
  description = "Log group name"
  type        = string
  default     = null
}

variable "retention_days" {
  description = "Log retention days"
  type        = number
  default     = 30
}
