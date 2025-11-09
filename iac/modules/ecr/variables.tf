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

variable "name" {
  description = "Repository name"
  type        = string
  default     = null
}

variable "encryption_type" {
  description = "Repository encryption type"
  type        = string
  default     = "AES256"
}

variable "scan_on_push" {
  description = "Repository scan on push"
  type        = bool
  default     = false
}

variable "image_tag_mutability" {
  description = "Repository image tag mutability"
  type        = string
  default     = "MUTABLE"
}


variable "public" {
  description = "Allow all pulls for any AWS account"
  type        = bool
  default     = false
}

variable "policy" {
  description = "Repository policy"
  type        = string
  default     = null
}

variable "lifecycle_policy" {
  description = "Repository lifecycle policy"
  type        = string
  default     = null
}

