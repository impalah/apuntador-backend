variable "vpc_name" {
  description = "Name to be used on all the resources as identifier"
  type        = string
  default     = ""
}

variable "cidr" {
  description = "The CIDR block for the VPC. Default value is a valid CIDR, but not acceptable by AWS and should be overridden"
  type        = string
  default     = "0.0.0.0/0"
}

variable "enable_ipv6" {
  description = "Requests an Amazon-provided IPv6 CIDR block with a /56 prefix length for the VPC. You cannot specify the range of IP addresses, or the size of the CIDR block."
  type        = bool
  default     = false
}

variable "enable_dns_hostnames" {
  description = "Should be true to enable DNS hostnames in the VPC"
  type        = bool
  default     = false
}

variable "enable_dns_support" {
  description = "Should be true to enable DNS support in the VPC"
  type        = bool
  default     = true
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "vpc_tags" {
  description = "Additional tags for the VPC"
  type        = map(string)
  default     = {}
}

variable "instance_tenancy" {
  description = "A tenancy option for instances launched into the VPC"
  type        = string
  default     = "default"
}

variable "enable_network_address_usage_metrics" {
  description = "Enable usage metrics"
  type        = bool
  default     = false
}


variable "subnets_configuration" {
  description = "List of subnet configurations"
  type = list(object({
    name              = string
    cidr_block        = string
    availability_zone = string
    subnet_type       = string
  }))
  default = []
}






variable "az1" {
  description = "Availability zone 1"
  type        = string
  default     = null
}

variable "az2" {
  description = "Availability zone 2"
  type        = string
  default     = null
}

variable "az3" {
  description = "Availability zone 3"
  type        = string
  default     = null
}


variable "subnet_private1_cidr_block" {
  description = "Private subnet 1 CIDR"
  type        = string
  default     = null
}

variable "subnet_private2_cidr_block" {
  description = "Private subnet 2 CIDR"
  type        = string
  default     = null
}

variable "subnet_private3_cidr_block" {
  description = "Private subnet 3 CIDR"
  type        = string
  default     = null
}


variable "subnet_public1_cidr_block" {
  description = "Public subnet 1 CIDR"
  type        = string
  default     = null
}

variable "subnet_public2_cidr_block" {
  description = "Public subnet 2 CIDR"
  type        = string
  default     = null
}

variable "subnet_public3_cidr_block" {
  description = "Public subnet 3 CIDR"
  type        = string
  default     = null
}

