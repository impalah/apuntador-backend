variable "table_name" {
  description = "Name of the DynamoDB table"
  type        = string
}

variable "billing_mode" {
  description = "Billing mode (PROVISIONED or PAY_PER_REQUEST)"
  type        = string
  default     = "PAY_PER_REQUEST"
}

variable "read_capacity" {
  description = "Read capacity units (only for PROVISIONED mode)"
  type        = number
  default     = 5
}

variable "write_capacity" {
  description = "Write capacity units (only for PROVISIONED mode)"
  type        = number
  default     = 5
}

variable "hash_key" {
  description = "Hash key (partition key)"
  type        = string
}

variable "range_key" {
  description = "Range key (sort key)"
  type        = string
  default     = null
}

variable "attributes" {
  description = "List of attributes (name and type)"
  type = list(object({
    name = string
    type = string # S (string), N (number), B (binary)
  }))
}

variable "global_secondary_indexes" {
  description = "List of global secondary indexes"
  type = list(object({
    name            = string
    hash_key        = string
    range_key       = optional(string)
    projection_type = string # ALL, KEYS_ONLY, INCLUDE
    read_capacity   = optional(number)
    write_capacity  = optional(number)
  }))
  default = []
}

variable "ttl_enabled" {
  description = "Enable TTL for automatic item deletion"
  type        = bool
  default     = false
}

variable "ttl_attribute_name" {
  description = "Name of the TTL attribute"
  type        = string
  default     = "ttl"
}

variable "point_in_time_recovery" {
  description = "Enable point-in-time recovery"
  type        = bool
  default     = true
}

variable "encryption_enabled" {
  description = "Enable server-side encryption"
  type        = bool
  default     = true
}

variable "kms_key_arn" {
  description = "ARN of KMS key for encryption (null = use AWS managed key)"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to the table"
  type        = map(string)
  default     = {}
}
