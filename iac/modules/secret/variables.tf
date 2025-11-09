
variable "description" {
  description = "Parameter description"
  type        = string
  default     = ""
}

variable "name" {
  description = "Parameter name"
  type        = string
  default     = null
}


variable "value" {
  description = "Parameter value"
  type        = string
  default     = null
}


variable "environment" {
  description = "Set environment name"
  type        = string
  default     = ""
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
