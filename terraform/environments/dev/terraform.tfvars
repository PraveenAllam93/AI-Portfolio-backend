# =============================================================================
# DEV ENVIRONMENT CONFIGURATION
# =============================================================================

environment  = "dev"
aws_region   = "ap-south-1" # Mumbai
project_name = "ai-portfolio"

# S3 Configuration
enable_s3_versioning         = true
s3_lifecycle_expiration_days = 7 # Clean up old files quickly in dev

# Lambda Configuration
lambda_memory_size          = 256 # Lower memory for dev
lambda_timeout              = 30
lambda_reserved_concurrency = null # No reserved concurrency in dev

# Upload Configuration
max_upload_size_mb           = 10
presigned_url_expiry_seconds = 300 # 5 minutes
allowed_file_extensions      = [".pdf", ".docx"]
allowed_mime_types = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
]

# Rate Limiting (lower for dev)
api_rate_limit  = 10
api_burst_limit = 20

# SQS Configuration
sqs_visibility_timeout     = 360 # Must be >= lambda timeout (300s); 6x recommended
sqs_message_retention_days = 4
dlq_max_receive_count      = 3

# Cognito Configuration
cognito_password_min_length        = 8
cognito_password_require_uppercase = true
cognito_password_require_lowercase = true
cognito_password_require_numbers   = true
cognito_password_require_symbols   = false

# Secrets
openai_api_key_secret_name = "ai-portfolio/dev/openai-api-key"

# Tags
tags = {
  Owner      = "development-team"
  CostCenter = "development"
}

allowed_origin = "https://ai-portfolio-frontend-neon.vercel.app"