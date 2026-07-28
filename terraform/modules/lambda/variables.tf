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

variable "stale_upload_expiry_hours" {
  description = "Hours after which a paused/pre-AI upload (PENDING_UPLOAD, AWAITING_SELECTION) is treated as abandoned and stops counting toward the per-user active-upload quota"
  type        = number
  default     = 24
}

variable "allowed_file_extensions" {
  description = "Allowed file extensions"
  type        = list(string)
  default     = [".pdf", ".docx"]
}

variable "allowed_mime_types" {
  description = "Allowed MIME types"
  type        = list(string)
  default = [
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

variable "cloudfront_domain" {
  description = "Domain name of the CloudFront distribution (e.g. dxxxxxxx.cloudfront.net) used to construct public image URLs"
  type        = string
}

variable "dlq_max_receive_count" {
  description = "Max SQS receive count before a message goes to the DLQ (used as SQS_MAX_RECEIVE_COUNT env var)"
  type        = number
  default     = 3
}

# CORS
variable "allowed_origin" {
  description = "CORS allowed origin for API responses (e.g. https://app.example.com)"
  type        = string
  default     = "*"
}

# Anonymous "Try for free" guests
variable "guest_email_domain" {
  description = "Reserved, non-routable email domain used for anonymous guest Cognito users (guest-<uuid>@<domain>). Must match the frontend GUEST_EMAIL_DOMAIN."
  type        = string
  default     = "guest.aifolio.internal"
}

variable "guest_ttl_hours" {
  description = "Hours after which an abandoned (never-converted) guest account is deleted by the reaper"
  type        = number
  default     = 72
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "username_change_cooldown_days" {
  description = "Minimum days between username changes. Portfolio URLs embed the username, so every change breaks links already shared."
  type        = string
  default     = "30"
}
