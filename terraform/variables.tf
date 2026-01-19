# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-south-1" # Mumbai - Primary region

  validation {
    condition = contains([
      "ap-south-1",     # Mumbai (Primary - cheapest in Asia)
      "ap-southeast-1", # Singapore
      "me-south-1",     # Bahrain (closest to Dubai)
      "us-east-1",      # N. Virginia
      "us-west-2",      # Oregon
    ], var.aws_region)
    error_message = "Region must be one of the approved regions."
  }
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "ai-portfolio"
}

# =============================================================================
# TAGS
# =============================================================================

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

# =============================================================================
# S3 CONFIGURATION
# =============================================================================

variable "enable_s3_versioning" {
  description = "Enable versioning for S3 buckets"
  type        = bool
  default     = true
}

variable "s3_lifecycle_expiration_days" {
  description = "Days after which objects in quarantine/rejected buckets expire"
  type        = number
  default     = 7
}

# =============================================================================
# LAMBDA CONFIGURATION
# =============================================================================

variable "lambda_memory_size" {
  description = "Memory size for Lambda functions (MB)"
  type        = number
  default     = 256

  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions (seconds)"
  type        = number
  default     = 30

  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "lambda_reserved_concurrency" {
  description = "Reserved concurrency for Lambda functions (null for unreserved)"
  type        = number
  default     = null
}

# =============================================================================
# UPLOAD CONFIGURATION
# =============================================================================

variable "max_upload_size_mb" {
  description = "Maximum file upload size in MB"
  type        = number
  default     = 10
}

variable "presigned_url_expiry_seconds" {
  description = "Pre-signed URL expiry time in seconds"
  type        = number
  default     = 300 # 5 minutes
}

variable "allowed_file_extensions" {
  description = "Allowed file extensions for upload"
  type        = list(string)
  default     = [".pdf", ".docx"]
}

variable "allowed_mime_types" {
  description = "Allowed MIME types for upload"
  type        = list(string)
  default = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  ]
}

# =============================================================================
# RATE LIMITING
# =============================================================================

variable "api_rate_limit" {
  description = "API Gateway rate limit (requests per second)"
  type        = number
  default     = 10
}

variable "api_burst_limit" {
  description = "API Gateway burst limit"
  type        = number
  default     = 20
}

# =============================================================================
# SQS CONFIGURATION
# =============================================================================

variable "sqs_visibility_timeout" {
  description = "SQS message visibility timeout (seconds)"
  type        = number
  default     = 60
}

variable "sqs_message_retention_days" {
  description = "SQS message retention period (days)"
  type        = number
  default     = 4
}

variable "dlq_max_receive_count" {
  description = "Max receives before message goes to DLQ"
  type        = number
  default     = 3
}

# =============================================================================
# COGNITO CONFIGURATION
# =============================================================================

variable "cognito_password_min_length" {
  description = "Minimum password length for Cognito users"
  type        = number
  default     = 8
}

variable "cognito_password_require_uppercase" {
  description = "Require uppercase in Cognito passwords"
  type        = bool
  default     = true
}

variable "cognito_password_require_lowercase" {
  description = "Require lowercase in Cognito passwords"
  type        = bool
  default     = true
}

variable "cognito_password_require_numbers" {
  description = "Require numbers in Cognito passwords"
  type        = bool
  default     = true
}

variable "cognito_password_require_symbols" {
  description = "Require symbols in Cognito passwords"
  type        = bool
  default     = false
}

# =============================================================================
# OPENAI CONFIGURATION
# =============================================================================

variable "openai_api_key_secret_name" {
  description = "Name of the Secrets Manager secret containing OpenAI API key"
  type        = string
  default     = "ai-portfolio/openai-api-key"
}
