# =============================================================================
# AI PORTFOLIO BACKEND - MAIN TERRAFORM CONFIGURATION
# =============================================================================
# Architecture: Serverless, Event-driven, Security-first
# Primary Region: ap-south-1 (Mumbai)
# =============================================================================

# -----------------------------------------------------------------------------
# PROVIDER CONFIGURATION
# -----------------------------------------------------------------------------

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      {
        Project     = var.project_name
        Environment = var.environment
        ManagedBy   = "terraform"
      },
      var.tags
    )
  }
}

# Provider for CloudFront (must be us-east-1 for ACM certificates)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = merge(
      {
        Project     = var.project_name
        Environment = var.environment
        ManagedBy   = "terraform"
      },
      var.tags
    )
  }
}

# -----------------------------------------------------------------------------
# LOCAL VALUES
# -----------------------------------------------------------------------------

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  # Common tags
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# RANDOM SUFFIX FOR GLOBALLY UNIQUE NAMES
# -----------------------------------------------------------------------------

resource "random_id" "suffix" {
  byte_length = 4
}

# -----------------------------------------------------------------------------
# DATA SOURCES
# -----------------------------------------------------------------------------

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# S3 BUCKETS MODULE
# -----------------------------------------------------------------------------

module "s3" {
  source = "./modules/s3"

  name_prefix                  = local.name_prefix
  random_suffix                = random_id.suffix.hex
  environment                  = var.environment
  enable_versioning            = var.enable_s3_versioning
  lifecycle_expiration_days    = var.s3_lifecycle_expiration_days
  tags                         = local.common_tags
}

# -----------------------------------------------------------------------------
# DYNAMODB MODULE
# -----------------------------------------------------------------------------

module "dynamodb" {
  source = "./modules/dynamodb"

  name_prefix = local.name_prefix
  environment = var.environment
  tags        = local.common_tags
}

# -----------------------------------------------------------------------------
# SQS MODULE
# -----------------------------------------------------------------------------

module "sqs" {
  source = "./modules/sqs"

  name_prefix             = local.name_prefix
  environment             = var.environment
  visibility_timeout      = var.sqs_visibility_timeout
  message_retention_days  = var.sqs_message_retention_days
  dlq_max_receive_count   = var.dlq_max_receive_count
  tags                    = local.common_tags
}

# -----------------------------------------------------------------------------
# COGNITO MODULE
# -----------------------------------------------------------------------------

module "cognito" {
  source = "./modules/cognito"

  name_prefix                = local.name_prefix
  environment                = var.environment
  password_min_length        = var.cognito_password_min_length
  password_require_uppercase = var.cognito_password_require_uppercase
  password_require_lowercase = var.cognito_password_require_lowercase
  password_require_numbers   = var.cognito_password_require_numbers
  password_require_symbols   = var.cognito_password_require_symbols
  tags                       = local.common_tags
}

# -----------------------------------------------------------------------------
# SECRETS MANAGER MODULE
# -----------------------------------------------------------------------------

module "secrets" {
  source = "./modules/secrets"

  name_prefix = local.name_prefix
  tags        = local.common_tags
}

# -----------------------------------------------------------------------------
# LAMBDA MODULE
# -----------------------------------------------------------------------------

module "lambda" {
  source = "./modules/lambda"

  name_prefix             = local.name_prefix
  environment             = var.environment
  memory_size             = var.lambda_memory_size
  timeout                 = var.lambda_timeout
  reserved_concurrency    = var.lambda_reserved_concurrency

  # Bucket ARNs
  quarantine_bucket_arn   = module.s3.quarantine_bucket_arn
  quarantine_bucket_name  = module.s3.quarantine_bucket_name
  validated_bucket_arn    = module.s3.validated_bucket_arn
  validated_bucket_name   = module.s3.validated_bucket_name
  rejected_bucket_arn     = module.s3.rejected_bucket_arn
  rejected_bucket_name    = module.s3.rejected_bucket_name
  portfolio_bucket_arn    = module.s3.portfolio_bucket_arn
  portfolio_bucket_name   = module.s3.portfolio_bucket_name

  # DynamoDB
  dynamodb_table_arn      = module.dynamodb.table_arn
  dynamodb_table_name     = module.dynamodb.table_name

  # SQS
  processing_queue_arn    = module.sqs.processing_queue_arn
  processing_queue_url    = module.sqs.processing_queue_url

  # Cognito
  user_pool_arn           = module.cognito.user_pool_arn
  user_pool_id            = module.cognito.user_pool_id

  # Upload config
  max_upload_size_mb           = var.max_upload_size_mb
  presigned_url_expiry_seconds = var.presigned_url_expiry_seconds
  allowed_file_extensions      = var.allowed_file_extensions
  allowed_mime_types           = var.allowed_mime_types

  # Secrets
  openai_api_key_secret_name = module.secrets.openai_secret_name

  tags = local.common_tags

  depends_on = [module.secrets]
}

# -----------------------------------------------------------------------------
# API GATEWAY MODULE
# -----------------------------------------------------------------------------

module "api_gateway" {
  source = "./modules/api-gateway"

  name_prefix   = local.name_prefix
  environment   = var.environment
  rate_limit    = var.api_rate_limit
  burst_limit   = var.api_burst_limit

  # Cognito
  user_pool_arn = module.cognito.user_pool_arn

  # Lambda integrations
  get_presigned_url_lambda_arn         = module.lambda.get_presigned_url_arn
  get_presigned_url_lambda_invoke_arn  = module.lambda.get_presigned_url_invoke_arn
  get_portfolio_lambda_arn             = module.lambda.get_portfolio_arn
  get_portfolio_lambda_invoke_arn      = module.lambda.get_portfolio_invoke_arn
  get_status_lambda_arn                = module.lambda.get_status_arn
  get_status_lambda_invoke_arn         = module.lambda.get_status_invoke_arn

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# CLOUDFRONT MODULE
# -----------------------------------------------------------------------------

module "cloudfront" {
  source = "./modules/cloudfront"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  name_prefix              = local.name_prefix
  environment              = var.environment
  portfolio_bucket_arn     = module.s3.portfolio_bucket_arn
  portfolio_bucket_id      = module.s3.portfolio_bucket_id
  portfolio_bucket_domain  = module.s3.portfolio_bucket_domain
  tags                     = local.common_tags
}

# -----------------------------------------------------------------------------
# S3 EVENT NOTIFICATIONS (after Lambda is created)
# -----------------------------------------------------------------------------

# Trigger validation Lambda when file is uploaded to quarantine bucket
resource "aws_s3_bucket_notification" "quarantine_notification" {
  bucket = module.s3.quarantine_bucket_id

  lambda_function {
    lambda_function_arn = module.lambda.quarantine_validator_arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [module.lambda]
}

# Trigger ingestion Lambda when file is moved to validated bucket
resource "aws_s3_bucket_notification" "validated_notification" {
  bucket = module.s3.validated_bucket_id

  lambda_function {
    lambda_function_arn = module.lambda.resume_ingestion_arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [module.lambda]
}
