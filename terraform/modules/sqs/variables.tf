variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "visibility_timeout" {
  description = "Visibility timeout in seconds"
  type        = number
  default     = 60
}

variable "message_retention_days" {
  description = "Message retention period in days"
  type        = number
  default     = 4
}

variable "dlq_max_receive_count" {
  description = "Max receives before message goes to DLQ"
  type        = number
  default     = 3
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
