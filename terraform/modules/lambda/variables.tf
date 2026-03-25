variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "memory_size" {
  description = "Default memory size for Lambda functions"
  type        = number
  default     = 256
}

variable "timeout" {
  description = "Default timeout for Lambda functions"
  type        = number
  default     = 30
}

variable "reserved_concurrency" {
  description = "Reserved concurrency for Lambda functions"
  type        = number
  default     = null
}

# S3 Buckets
variable "quarantine_bucket_arn" {
  description = "ARN of the quarantine bucket"
  type        = string
}

variable "quarantine_bucket_name" {
  description = "Name of the quarantine bucket"
  type        = string
}

variable "validated_bucket_arn" {
  description = "ARN of the validated bucket"
  type        = string
}

variable "validated_bucket_name" {
  description = "Name of the validated bucket"
  type        = string
}

variable "rejected_bucket_arn" {
  description = "ARN of the rejected bucket"
  type        = string
}

variable "rejected_bucket_name" {
  description = "Name of the rejected bucket"
  type        = string
}

variable "portfolio_bucket_arn" {
  description = "ARN of the portfolio bucket"
  type        = string
}

variable "portfolio_bucket_name" {
  description = "Name of the portfolio bucket"
  type        = string
}

# DynamoDB
variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  type        = string
}

# SQS
variable "processing_queue_arn" {
  description = "ARN of the processing queue"
  type        = string
}

variable "processing_queue_url" {
  description = "URL of the processing queue"
  type        = string
}

# Cognito
variable "user_pool_arn" {
  description = "ARN of the Cognito user pool"
  type        = string
}

variable "user_pool_id" {
  description = "ID of the Cognito user pool"
  type        = string
}

# Upload config
variable "max_upload_size_mb" {
  description = "Maximum upload size in MB"
  type        = number
  default     = 10
}

variable "presigned_url_expiry_seconds" {
  description = "Presigned URL expiry in seconds"
  type        = number
  default     = 300
}

variable "allowed_file_extensions" {
  description = "Allowed file extensions"
  type        = list(string)
  default     = [".pdf", ".docx"]
}

variable "allowed_mime_types" {
  description = "Allowed MIME types"
  type        = list(string)
  default     = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  ]
}

# Secrets
variable "openai_api_key_secret_name" {
  description = "Name of the OpenAI API key secret"
  type        = string
}

# Access logs bucket (for CloudFront log processing)
variable "access_logs_bucket_arn" {
  description = "ARN of the CloudFront access logs S3 bucket"
  type        = string
}

variable "access_logs_bucket_name" {
  description = "Name of the CloudFront access logs S3 bucket"
  type        = string
}

# CloudFront — used by portfolio generator for cache invalidation
variable "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution for portfolio cache invalidation"
  type        = string
}

variable "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution for portfolio cache invalidation IAM policy"
  type        = string
}

# CORS
variable "allowed_origin" {
  description = "CORS allowed origin for API responses (e.g. https://app.example.com)"
  type        = string
  default     = "*"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
