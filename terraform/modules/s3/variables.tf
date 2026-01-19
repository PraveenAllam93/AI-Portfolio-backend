variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "random_suffix" {
  description = "Random suffix for globally unique bucket names"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "enable_versioning" {
  description = "Enable versioning for buckets"
  type        = bool
  default     = true
}

variable "lifecycle_expiration_days" {
  description = "Days after which objects expire in quarantine/rejected buckets"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
