variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "portfolio_bucket_arn" {
  description = "ARN of the portfolio S3 bucket"
  type        = string
}

variable "portfolio_bucket_id" {
  description = "ID of the portfolio S3 bucket"
  type        = string
}

variable "portfolio_bucket_domain" {
  description = "Regional domain name of the portfolio bucket"
  type        = string
}

variable "access_logs_bucket_domain" {
  description = "Domain name of the S3 bucket for CloudFront access logs (must be bucket_domain_name, not regional)"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "portfolio_access_gate_lambda_arn" {
  description = "Versioned ARN of the Lambda@Edge portfolio access gate function"
  type        = string
}
