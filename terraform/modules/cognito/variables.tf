variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "password_min_length" {
  description = "Minimum password length"
  type        = number
  default     = 8
}

variable "password_require_uppercase" {
  description = "Require uppercase in passwords"
  type        = bool
  default     = true
}

variable "password_require_lowercase" {
  description = "Require lowercase in passwords"
  type        = bool
  default     = true
}

variable "password_require_numbers" {
  description = "Require numbers in passwords"
  type        = bool
  default     = true
}

variable "password_require_symbols" {
  description = "Require symbols in passwords"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
