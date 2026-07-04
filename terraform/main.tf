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

  # Access logs bucket (CloudFront view tracking)
  access_logs_bucket_arn  = module.s3.access_logs_bucket_arn
  access_logs_bucket_name = module.s3.access_logs_bucket_name

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
  openai_api_key_secret_name = var.openai_api_key_secret_name

  # CORS: lock to your frontend domain in prod (e.g. https://app.example.com)
  allowed_origin = var.allowed_origin

  # CloudFront: portfolio generator invalidates cache after each regeneration
  cloudfront_distribution_id  = module.cloudfront.distribution_id
  cloudfront_distribution_arn = module.cloudfront.distribution_arn
  cloudfront_domain            = module.cloudfront.domain_name

  tags = local.common_tags
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

  # Lambda integrations — existing
  get_presigned_url_lambda_arn         = module.lambda.get_presigned_url_arn
  get_presigned_url_lambda_invoke_arn  = module.lambda.get_presigned_url_invoke_arn
  get_portfolio_lambda_arn             = module.lambda.get_portfolio_arn
  get_portfolio_lambda_invoke_arn      = module.lambda.get_portfolio_invoke_arn
  get_status_lambda_arn                = module.lambda.get_status_arn
  get_status_lambda_invoke_arn         = module.lambda.get_status_invoke_arn
  start_generation_lambda_arn          = module.lambda.start_generation_arn
  start_generation_lambda_invoke_arn   = module.lambda.start_generation_invoke_arn

  # Lambda integrations — new endpoints
  get_analytics_lambda_arn                   = module.lambda.get_analytics_arn
  get_analytics_lambda_invoke_arn            = module.lambda.get_analytics_invoke_arn
  patch_portfolio_lambda_arn                 = module.lambda.patch_portfolio_arn
  patch_portfolio_lambda_invoke_arn          = module.lambda.patch_portfolio_invoke_arn
  ai_enhance_portfolio_lambda_arn            = module.lambda.ai_enhance_portfolio_arn
  ai_enhance_portfolio_lambda_invoke_arn     = module.lambda.ai_enhance_portfolio_invoke_arn
  add_custom_section_lambda_arn              = module.lambda.add_custom_section_arn
  add_custom_section_lambda_invoke_arn       = module.lambda.add_custom_section_invoke_arn
  publish_portfolio_lambda_arn               = module.lambda.publish_portfolio_arn
  publish_portfolio_lambda_invoke_arn        = module.lambda.publish_portfolio_invoke_arn

  get_image_upload_url_lambda_arn        = module.lambda.get_image_upload_url_arn
  get_image_upload_url_lambda_invoke_arn = module.lambda.get_image_upload_url_invoke_arn

  generate_project_image_lambda_arn        = module.lambda.generate_project_image_arn
  generate_project_image_lambda_invoke_arn = module.lambda.generate_project_image_invoke_arn

  interview_start_lambda_arn         = module.lambda.interview_start_arn
  interview_start_lambda_invoke_arn  = module.lambda.interview_start_invoke_arn
  interview_answer_lambda_arn        = module.lambda.interview_answer_arn
  interview_answer_lambda_invoke_arn = module.lambda.interview_answer_invoke_arn
  interview_exit_lambda_arn          = module.lambda.interview_exit_arn
  interview_exit_lambda_invoke_arn   = module.lambda.interview_exit_invoke_arn
  interview_report_lambda_arn          = module.lambda.interview_report_arn
  interview_report_lambda_invoke_arn   = module.lambda.interview_report_invoke_arn
  interview_sessions_lambda_arn        = module.lambda.interview_sessions_arn
  interview_sessions_lambda_invoke_arn = module.lambda.interview_sessions_invoke_arn

  # Lambda integrations — portfolio versions
  cancel_upload_lambda_arn           = module.lambda.cancel_upload_arn
  cancel_upload_lambda_invoke_arn    = module.lambda.cancel_upload_invoke_arn
  list_versions_lambda_arn           = module.lambda.list_versions_arn
  list_versions_lambda_invoke_arn    = module.lambda.list_versions_invoke_arn
  activate_version_lambda_arn        = module.lambda.activate_version_arn
  activate_version_lambda_invoke_arn = module.lambda.activate_version_invoke_arn
  delete_version_lambda_arn          = module.lambda.delete_version_arn
  delete_version_lambda_invoke_arn   = module.lambda.delete_version_invoke_arn

  list_portfolios_lambda_arn              = module.lambda.list_portfolios_arn
  list_portfolios_lambda_invoke_arn       = module.lambda.list_portfolios_invoke_arn
  toggle_portfolio_live_lambda_arn        = module.lambda.toggle_portfolio_live_arn
  toggle_portfolio_live_lambda_invoke_arn = module.lambda.toggle_portfolio_live_invoke_arn
  delete_portfolio_lambda_arn             = module.lambda.delete_portfolio_arn
  delete_portfolio_lambda_invoke_arn      = module.lambda.delete_portfolio_invoke_arn

  get_portfolio_preview_url_lambda_arn        = module.lambda.get_portfolio_preview_url_arn
  get_portfolio_preview_url_lambda_invoke_arn = module.lambda.get_portfolio_preview_url_invoke_arn

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# PORTFOLIO ACCESS GATE (Lambda@Edge) — MUST be in us-east-1
# -----------------------------------------------------------------------------
# Lambda@Edge requires the function to be created in us-east-1 regardless of
# the primary deployment region. It also does NOT support environment variables,
# so the DynamoDB table name and region are baked in via templatefile().

data "archive_file" "portfolio_access_gate" {
  type = "zip"
  source {
    content = templatefile("${path.root}/../src/lambdas/portfolio_access_gate/handler.py", {
      dynamodb_table  = module.dynamodb.table_name
      dynamodb_region = var.aws_region
    })
    filename = "handler.py"
  }
  output_path = "${path.root}/../dist/lambdas/portfolio_access_gate.zip"
}

resource "aws_iam_role" "portfolio_access_gate" {
  provider = aws.us_east_1
  name     = "${local.name_prefix}-portfolio-access-gate-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = ["lambda.amazonaws.com", "edgelambda.amazonaws.com"] }
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "portfolio_access_gate_logs" {
  provider = aws.us_east_1
  name     = "cloudwatch-logs"
  role     = aws_iam_role.portfolio_access_gate.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "arn:aws:logs:*:*:*"
    }]
  })
}

resource "aws_iam_role_policy" "portfolio_access_gate_dynamodb" {
  provider = aws.us_east_1
  name     = "dynamodb-get-portfolio-live"
  role     = aws_iam_role.portfolio_access_gate.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "CheckPortfolioAccess"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem"]
      Resource = module.dynamodb.table_arn
    }]
  })
}

resource "aws_lambda_function" "portfolio_access_gate" {
  provider         = aws.us_east_1
  filename         = data.archive_file.portfolio_access_gate.output_path
  function_name    = "${local.name_prefix}-portfolio-access-gate"
  role             = aws_iam_role.portfolio_access_gate.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.portfolio_access_gate.output_base64sha256
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128
  publish          = true # versioned ARN required by CloudFront Lambda@Edge

  # No environment block — Lambda@Edge does not support environment variables.

  tags = merge(local.common_tags, {
    Function = "CloudFront Origin Request access gate for portfolio visibility"
  })
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

  name_prefix               = local.name_prefix
  environment               = var.environment
  portfolio_bucket_arn      = module.s3.portfolio_bucket_arn
  portfolio_bucket_id       = module.s3.portfolio_bucket_id
  portfolio_bucket_domain   = module.s3.portfolio_bucket_domain
  # Access logs bucket — CloudFront writes compressed logs here every ~5 min.
  # Must use bucket_domain_name (not regional) per CloudFront logging requirement.
  access_logs_bucket_domain        = module.s3.access_logs_bucket_domain
  portfolio_access_gate_lambda_arn = aws_lambda_function.portfolio_access_gate.qualified_arn
  tags                             = local.common_tags
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

# Trigger access log processor when CloudFront delivers a new log file.
# CloudFront writes to the prefix "cloudfront/" so we filter on that.
resource "aws_s3_bucket_notification" "access_logs_notification" {
  bucket = module.s3.access_logs_bucket_id

  lambda_function {
    lambda_function_arn = module.lambda.process_access_logs_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "cloudfront/"
    filter_suffix       = ".gz"
  }

  depends_on = [module.lambda]
}
