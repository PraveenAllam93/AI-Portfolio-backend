# =============================================================================
# LAMBDA MODULE
# =============================================================================
# Lambda functions for the AI Portfolio pipeline:
# 1. getPresignedUrl      - Generate presigned URLs for uploads
# 2. quarantineValidator  - Validate files in quarantine bucket
# 3. resumeIngestion      - Extract text from validated resumes
# 4. aiProcessing         - Call OpenAI for resume parsing
# 5. portfolioGenerator   - Generate static portfolio HTML
# 6. getPortfolio         - Retrieve portfolio data (API)
# 7. getStatus            - Get processing status (API)
#
# IAM: each Lambda has its OWN execution role with ONLY the permissions
# it actually needs (least-privilege). A compromise of one Lambda cannot
# be used to read secrets or write to buckets that Lambda has no business
# touching.
# =============================================================================

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------------------
# SHARED ASSUME-ROLE POLICY (same for all Lambda roles)
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# ---------------------------------------------------------------------------
# HELPER: reusable CloudWatch Logs policy document
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "cloudwatch_logs" {
  statement {
    sid    = "CloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

# =============================================================================
# 1. GET PRESIGNED URL LAMBDA
# Needs: s3:PutObject on quarantine (to sign the URL), dynamodb:PutItem
# =============================================================================

resource "aws_iam_role" "get_presigned_url" {
  name               = "${var.name_prefix}-presigned-url-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "get_presigned_url_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.get_presigned_url.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "get_presigned_url_s3" {
  name = "s3-presign"
  role = aws_iam_role.get_presigned_url.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "SignPresignedPut"
      Effect = "Allow"
      # PutObject permission is required to generate a presigned PUT URL
      Action   = ["s3:PutObject"]
      Resource = "${var.quarantine_bucket_arn}/*"
    }]
  })
}

resource "aws_iam_role_policy" "get_presigned_url_dynamodb" {
  name = "dynamodb-put"
  role = aws_iam_role.get_presigned_url.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "WriteUploadRecord"
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem", "dynamodb:Query"]
      Resource = [
        var.dynamodb_table_arn,
        "${var.dynamodb_table_arn}/index/*",
      ]
    }]
  })
}

# =============================================================================
# 2. QUARANTINE VALIDATOR LAMBDA
# Needs: read/delete quarantine, write validated + rejected, dynamodb:UpdateItem
# =============================================================================

resource "aws_iam_role" "quarantine_validator" {
  name               = "${var.name_prefix}-quarantine-validator-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "quarantine_validator_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.quarantine_validator.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "quarantine_validator_s3" {
  name = "s3-validate"
  role = aws_iam_role.quarantine_validator.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadDeleteQuarantine"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:DeleteObject"]
        Resource = "${var.quarantine_bucket_arn}/*"
      },
      {
        Sid    = "PromoteToValidated"
        Effect = "Allow"
        Action = ["s3:PutObject"]
        Resource = "${var.validated_bucket_arn}/*"
      },
      {
        Sid    = "MoveToRejected"
        Effect = "Allow"
        Action = ["s3:PutObject"]
        Resource = "${var.rejected_bucket_arn}/*"
      },
    ]
  })
}

resource "aws_iam_role_policy" "quarantine_validator_dynamodb" {
  name = "dynamodb-update"
  role = aws_iam_role.quarantine_validator.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "UpdateUploadStatus"
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

# =============================================================================
# 3. RESUME INGESTION LAMBDA
# Needs: s3:GetObject on validated, sqs:SendMessage, dynamodb:UpdateItem
# =============================================================================

resource "aws_iam_role" "resume_ingestion" {
  name               = "${var.name_prefix}-resume-ingestion-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "resume_ingestion_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.resume_ingestion.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "resume_ingestion_s3" {
  name = "s3-read-validated"
  role = aws_iam_role.resume_ingestion.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      # GetObject covers both GetObject and HeadObject in IAM
      Sid      = "ReadValidatedResume"
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "${var.validated_bucket_arn}/*"
    }]
  })
}

resource "aws_iam_role_policy" "resume_ingestion_sqs" {
  name = "sqs-send"
  role = aws_iam_role.resume_ingestion.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "SendToProcessingQueue"
      Effect   = "Allow"
      Action   = ["sqs:SendMessage", "sqs:GetQueueAttributes"]
      Resource = var.processing_queue_arn
    }]
  })
}

resource "aws_iam_role_policy" "resume_ingestion_dynamodb" {
  name = "dynamodb-update"
  role = aws_iam_role.resume_ingestion.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "UpdateUploadStatus"
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem", "dynamodb:GetItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

# =============================================================================
# 4. AI PROCESSING LAMBDA
# Needs: secretsmanager:GetSecretValue, dynamodb:UpdateItem+PutItem,
#        sqs:ReceiveMessage+DeleteMessage, lambda:InvokeFunction (portfolio gen)
# =============================================================================

resource "aws_iam_role" "ai_processing" {
  name               = "${var.name_prefix}-ai-processing-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "ai_processing_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.ai_processing.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "ai_processing_secrets" {
  name = "secrets-openai"
  role = aws_iam_role.ai_processing.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "GetOpenAIKey"
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      # Scoped to the exact secret — wildcard (*) is NOT used here
      Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.openai_api_key_secret_name}*"
    }]
  })
}

resource "aws_iam_role_policy" "ai_processing_dynamodb" {
  name = "dynamodb-write"
  role = aws_iam_role.ai_processing.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "WriteAIResults"
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem", "dynamodb:PutItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "ai_processing_sqs" {
  name = "sqs-consume"
  role = aws_iam_role.ai_processing.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "ConsumeProcessingQueue"
      Effect = "Allow"
      Action = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
      ]
      Resource = var.processing_queue_arn
    }]
  })
}

resource "aws_iam_role_policy" "ai_processing_invoke_portfolio" {
  name = "lambda-invoke-portfolio"
  role = aws_iam_role.ai_processing.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "InvokePortfolioGenerator"
      Effect = "Allow"
      Action = ["lambda:InvokeFunction"]
      # Scoped to exactly the portfolio-generator function
      Resource = "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.name_prefix}-portfolio-generator"
    }]
  })
}

# =============================================================================
# 5. PORTFOLIO GENERATOR LAMBDA
# Needs: s3:PutObject on portfolio bucket, dynamodb:GetItem+UpdateItem
# =============================================================================

resource "aws_iam_role" "portfolio_generator" {
  name               = "${var.name_prefix}-portfolio-generator-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "portfolio_generator_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.portfolio_generator.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "portfolio_generator_s3" {
  name = "s3-write-portfolio"
  role = aws_iam_role.portfolio_generator.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "WritePortfolioFiles"
      Effect   = "Allow"
      Action   = ["s3:PutObject"]
      Resource = "${var.portfolio_bucket_arn}/*"
    }]
  })
}

resource "aws_iam_role_policy" "portfolio_generator_dynamodb" {
  name = "dynamodb-read-update"
  role = aws_iam_role.portfolio_generator.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadAndUpdatePortfolio"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "portfolio_generator_cloudfront" {
  name = "cloudfront-invalidate"
  role = aws_iam_role.portfolio_generator.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "InvalidatePortfolioCache"
      Effect = "Allow"
      # Scoped to this specific distribution only — no other CloudFront resource accessible
      Action   = ["cloudfront:CreateInvalidation"]
      Resource = var.cloudfront_distribution_arn
    }]
  })
}

# =============================================================================
# 6 & 7. GET PORTFOLIO + GET STATUS LAMBDAS (API read-only)
# Needs: dynamodb:GetItem only — no write, no S3, no secrets
# =============================================================================

resource "aws_iam_role" "api_read" {
  name               = "${var.name_prefix}-api-read-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "api_read_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.api_read.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "api_read_dynamodb" {
  name = "dynamodb-get-only"
  role = aws_iam_role.api_read.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadOwnRecords"
      Effect   = "Allow"
      # GetItem only — no Scan, no Query, no Write
      Action   = ["dynamodb:GetItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

# =============================================================================
# LAMBDA FUNCTION DEFINITIONS
# =============================================================================

# -----------------------------------------------------------------------------
# 1. GET PRESIGNED URL
# -----------------------------------------------------------------------------

data "archive_file" "get_presigned_url" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/upload"
  output_path = "${path.module}/../../../dist/lambdas/get_presigned_url.zip"
}

resource "aws_lambda_function" "get_presigned_url" {
  filename         = data.archive_file.get_presigned_url.output_path
  function_name    = "${var.name_prefix}-get-presigned-url"
  role             = aws_iam_role.get_presigned_url.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.get_presigned_url.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      QUARANTINE_BUCKET            = var.quarantine_bucket_name
      MAX_UPLOAD_SIZE_MB           = var.max_upload_size_mb
      PRESIGNED_URL_EXPIRY_SECONDS = var.presigned_url_expiry_seconds
      ALLOWED_EXTENSIONS           = join(",", var.allowed_file_extensions)
      ALLOWED_MIME_TYPES           = join(",", var.allowed_mime_types)
      DYNAMODB_TABLE               = var.dynamodb_table_name
      ENVIRONMENT                  = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-get-presigned-url"
    Function = "Upload URL generation"
  })
}

# -----------------------------------------------------------------------------
# 2. QUARANTINE VALIDATOR
# -----------------------------------------------------------------------------

data "archive_file" "quarantine_validator" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/validation"
  output_path = "${path.module}/../../../dist/lambdas/quarantine_validator.zip"
}

resource "aws_lambda_function" "quarantine_validator" {
  filename         = data.archive_file.quarantine_validator.output_path
  function_name    = "${var.name_prefix}-quarantine-validator"
  role             = aws_iam_role.quarantine_validator.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.quarantine_validator.output_base64sha256
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 512

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      QUARANTINE_BUCKET  = var.quarantine_bucket_name
      VALIDATED_BUCKET   = var.validated_bucket_name
      REJECTED_BUCKET    = var.rejected_bucket_name
      DYNAMODB_TABLE     = var.dynamodb_table_name
      ALLOWED_EXTENSIONS = join(",", var.allowed_file_extensions)
      ALLOWED_MIME_TYPES = join(",", var.allowed_mime_types)
      MAX_FILE_SIZE_MB   = var.max_upload_size_mb
      ENVIRONMENT        = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-quarantine-validator"
    Function = "File validation and security checks"
  })
}

resource "aws_lambda_permission" "quarantine_s3_trigger" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.quarantine_validator.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.quarantine_bucket_arn
}

# -----------------------------------------------------------------------------
# LAMBDA LAYER: pdf_processing
# Contains PyPDF2 and python-docx — used by resume_ingestion.
# Keeping dependencies in a Layer means the Lambda source_dir stays clean
# (handler.py only) and the same packages can be shared if needed in future.
# -----------------------------------------------------------------------------

data "archive_file" "pdf_processing_layer" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/layers/pdf_processing"
  output_path = "${path.module}/../../../dist/layers/pdf_processing.zip"
}

resource "aws_lambda_layer_version" "pdf_processing" {
  layer_name          = "${var.name_prefix}-pdf-processing"
  filename            = data.archive_file.pdf_processing_layer.output_path
  source_code_hash    = data.archive_file.pdf_processing_layer.output_base64sha256
  compatible_runtimes = ["python3.12"]
  description         = "PyPDF2 and python-docx for resume text extraction"
}

# -----------------------------------------------------------------------------
# 3. RESUME INGESTION
# -----------------------------------------------------------------------------

data "archive_file" "resume_ingestion" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/ingestion"
  output_path = "${path.module}/../../../dist/lambdas/resume_ingestion.zip"
}

resource "aws_lambda_function" "resume_ingestion" {
  filename         = data.archive_file.resume_ingestion.output_path
  function_name    = "${var.name_prefix}-resume-ingestion"
  role             = aws_iam_role.resume_ingestion.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.resume_ingestion.output_base64sha256
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 512
  layers           = [aws_lambda_layer_version.pdf_processing.arn]

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      VALIDATED_BUCKET = var.validated_bucket_name
      DYNAMODB_TABLE   = var.dynamodb_table_name
      PROCESSING_QUEUE = var.processing_queue_url
      ENVIRONMENT      = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-resume-ingestion"
    Function = "Resume text extraction"
  })
}

resource "aws_lambda_permission" "validated_s3_trigger" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.resume_ingestion.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.validated_bucket_arn
}

# -----------------------------------------------------------------------------
# 4. AI PROCESSING
# -----------------------------------------------------------------------------

data "archive_file" "ai_processing" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/ai_processing"
  output_path = "${path.module}/../../../dist/lambdas/ai_processing.zip"
}

resource "aws_lambda_function" "ai_processing" {
  filename         = data.archive_file.ai_processing.output_path
  function_name    = "${var.name_prefix}-ai-processing"
  role             = aws_iam_role.ai_processing.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.ai_processing.output_base64sha256
  runtime          = "python3.12"
  timeout          = 300
  memory_size      = 512
  layers           = [aws_lambda_layer_version.pdf_processing.arn]

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE        = var.dynamodb_table_name
      OPENAI_SECRET_NAME    = var.openai_api_key_secret_name
      PORTFOLIO_BUCKET      = var.portfolio_bucket_name
      ENVIRONMENT           = var.environment
      PORTFOLIO_LAMBDA_NAME = "${var.name_prefix}-portfolio-generator"
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-ai-processing"
    Function = "OpenAI resume parsing"
  })
}

resource "aws_lambda_event_source_mapping" "ai_processing_sqs" {
  event_source_arn = var.processing_queue_arn
  function_name    = aws_lambda_function.ai_processing.arn
  batch_size       = 1

  scaling_config {
    maximum_concurrency = 5
  }
}

# -----------------------------------------------------------------------------
# 5. PORTFOLIO GENERATOR
# -----------------------------------------------------------------------------

data "archive_file" "portfolio_generator" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/portfolio"
  output_path = "${path.module}/../../../dist/lambdas/portfolio_generator.zip"
}

resource "aws_lambda_function" "portfolio_generator" {
  filename         = data.archive_file.portfolio_generator.output_path
  function_name    = "${var.name_prefix}-portfolio-generator"
  role             = aws_iam_role.portfolio_generator.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.portfolio_generator.output_base64sha256
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 256

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      PORTFOLIO_BUCKET           = var.portfolio_bucket_name
      DYNAMODB_TABLE             = var.dynamodb_table_name
      CLOUDFRONT_DISTRIBUTION_ID = var.cloudfront_distribution_id
      ENVIRONMENT                = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-portfolio-generator"
    Function = "Static portfolio HTML generation"
  })
}

# -----------------------------------------------------------------------------
# 6. GET PORTFOLIO (API)
# -----------------------------------------------------------------------------

data "archive_file" "get_portfolio" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/auth"
  output_path = "${path.module}/../../../dist/lambdas/get_portfolio.zip"
}

resource "aws_lambda_function" "get_portfolio" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-get-portfolio"
  role             = aws_iam_role.api_read.arn
  handler          = "get_portfolio.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE   = var.dynamodb_table_name
      PORTFOLIO_BUCKET = var.portfolio_bucket_name
      ENVIRONMENT      = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-get-portfolio"
    Function = "Retrieve portfolio data"
  })
}

# -----------------------------------------------------------------------------
# 7. GET STATUS (API)
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "get_status" {
  # Reuses the same auth/ zip as get_portfolio
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-get-status"
  role             = aws_iam_role.api_read.arn
  handler          = "get_status.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE = var.dynamodb_table_name
      ENVIRONMENT    = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-get-status"
    Function = "Get processing status"
  })
}

# =============================================================================
# 8. PROCESS ACCESS LOGS LAMBDA
# Triggered by S3:ObjectCreated on the access-logs bucket.
# Needs: s3:GetObject on access-logs, dynamodb:PutItem on PORTFOLIO#* keys.
# =============================================================================

resource "aws_iam_role" "process_access_logs" {
  name               = "${var.name_prefix}-process-access-logs-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "process_access_logs_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.process_access_logs.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "process_access_logs_s3" {
  name = "s3-read-access-logs"
  role = aws_iam_role.process_access_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadCloudFrontLogs"
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "${var.access_logs_bucket_arn}/*"
    }]
  })
}

resource "aws_iam_role_policy" "process_access_logs_dynamodb" {
  name = "dynamodb-put-views"
  role = aws_iam_role.process_access_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "WriteViewEvents"
      Effect = "Allow"
      Action = ["dynamodb:BatchWriteItem"]
      # Scoped to the table only; LeadingKeys condition enforced in Lambda code.
      Resource = var.dynamodb_table_arn
    }]
  })
}

data "archive_file" "process_access_logs" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/process_access_logs"
  output_path = "${path.module}/../../../dist/lambdas/process_access_logs.zip"
}

resource "aws_lambda_function" "process_access_logs" {
  filename         = data.archive_file.process_access_logs.output_path
  function_name    = "${var.name_prefix}-process-access-logs"
  role             = aws_iam_role.process_access_logs.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.process_access_logs.output_base64sha256
  runtime          = "python3.12"
  timeout          = 120  # Log files can contain many records
  memory_size      = 256

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE = var.dynamodb_table_name
      ENVIRONMENT    = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-process-access-logs"
    Function = "CloudFront access log processor"
  })
}

resource "aws_lambda_permission" "access_logs_s3_trigger" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.process_access_logs.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.access_logs_bucket_arn
}

# =============================================================================
# 9. GET ANALYTICS LAMBDA
# GET /portfolio/{userId}/analytics — owner-only analytics.
# Needs: dynamodb:Query on PORTFOLIO#* keys.
# =============================================================================

resource "aws_iam_role" "analytics" {
  name               = "${var.name_prefix}-analytics-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "analytics_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.analytics.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "analytics_dynamodb" {
  name = "dynamodb-query-views"
  role = aws_iam_role.analytics.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "QueryViewEvents"
      Effect = "Allow"
      Action = ["dynamodb:Query"]
      Resource = [
        var.dynamodb_table_arn,
        "${var.dynamodb_table_arn}/index/*",
      ]
      # Belt-and-suspenders: restrict to PORTFOLIO#* partition keys even at IAM level.
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["PORTFOLIO#*"]
        }
      }
    }]
  })
}

resource "aws_lambda_function" "get_analytics" {
  # Bundled in the same auth/ zip — handler file is get_analytics.py
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-get-analytics"
  role             = aws_iam_role.analytics.arn
  handler          = "get_analytics.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE = var.dynamodb_table_name
      ALLOWED_ORIGIN = var.allowed_origin
      ENVIRONMENT    = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-get-analytics"
    Function = "Portfolio view analytics"
  })
}

# =============================================================================
# 10. PATCH PORTFOLIO LAMBDA
# PATCH /portfolio/{userId}/content — manual field edit + rebuild trigger.
# Needs: dynamodb:UpdateItem on USER#* keys, lambda:InvokeFunction (portfolio gen).
# =============================================================================

resource "aws_iam_role" "portfolio_edit" {
  name               = "${var.name_prefix}-portfolio-edit-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "portfolio_edit_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.portfolio_edit.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "portfolio_edit_dynamodb" {
  name = "dynamodb-update-portfolio"
  role = aws_iam_role.portfolio_edit.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "UpdatePortfolioContent"
      Effect = "Allow"
      Action = ["dynamodb:UpdateItem"]
      Resource = var.dynamodb_table_arn
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USER#*"]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "portfolio_edit_invoke" {
  name = "lambda-invoke-portfolio-generator"
  role = aws_iam_role.portfolio_edit.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "InvokePortfolioGenerator"
      Effect = "Allow"
      Action = ["lambda:InvokeFunction"]
      Resource = "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.name_prefix}-portfolio-generator"
    }]
  })
}

resource "aws_lambda_function" "patch_portfolio" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-patch-portfolio"
  role             = aws_iam_role.portfolio_edit.arn
  handler          = "patch_portfolio.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE        = var.dynamodb_table_name
      PORTFOLIO_LAMBDA_NAME = "${var.name_prefix}-portfolio-generator"
      ALLOWED_ORIGIN        = var.allowed_origin
      ENVIRONMENT           = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-patch-portfolio"
    Function = "Manual portfolio content edit"
  })
}

# =============================================================================
# 11. PUBLISH PORTFOLIO LAMBDA
# POST /portfolio/{userId}/publish — triggers live (published) rebuild.
# Reuses the portfolio_edit IAM role — same DynamoDB + Lambda invoke permissions.
# =============================================================================

resource "aws_lambda_function" "publish_portfolio" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-publish-portfolio"
  role             = aws_iam_role.portfolio_edit.arn
  handler          = "publish_portfolio.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      PORTFOLIO_LAMBDA_NAME = "${var.name_prefix}-portfolio-generator"
      ALLOWED_ORIGIN        = var.allowed_origin
      ENVIRONMENT           = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-publish-portfolio"
    Function = "Publish portfolio draft to live"
  })
}

# =============================================================================
# 12. AI ENHANCE PORTFOLIO LAMBDA
# POST /portfolio/{userId}/ai-enhance — returns AI-generated field suggestion.
# Needs: dynamodb:GetItem on USER#* keys, secretsmanager:GetSecretValue (OpenAI).
# Does NOT write to DynamoDB or invoke portfolio generator — suggestion only.
# =============================================================================

resource "aws_iam_role" "ai_enhance" {
  name               = "${var.name_prefix}-ai-enhance-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "ai_enhance_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.ai_enhance.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "ai_enhance_dynamodb" {
  name = "dynamodb-get-portfolio"
  role = aws_iam_role.ai_enhance.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "ReadPortfolioContent"
      Effect = "Allow"
      Action = ["dynamodb:GetItem"]
      Resource = var.dynamodb_table_arn
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USER#*"]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "ai_enhance_secrets" {
  name = "secrets-openai"
  role = aws_iam_role.ai_enhance.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "GetOpenAIKey"
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.openai_api_key_secret_name}*"
    }]
  })
}

resource "aws_lambda_function" "ai_enhance_portfolio" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-ai-enhance-portfolio"
  role             = aws_iam_role.ai_enhance.arn
  handler          = "ai_enhance_portfolio.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = 29  # API Gateway max synchronous timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE     = var.dynamodb_table_name
      OPENAI_SECRET_NAME = var.openai_api_key_secret_name
      ALLOWED_ORIGIN     = var.allowed_origin
      ENVIRONMENT        = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-ai-enhance-portfolio"
    Function = "AI portfolio field enhancement - suggestion only"
  })
}

# =============================================================================
# INTERVIEW AGENT LAMBDAS
# POST /interview/start   — create session, generate first question
# POST /interview/answer  — evaluate answer, return feedback + next question
# POST /interview/exit    — stop session, generate report
# GET  /interview/{sessionId}/report — fetch final report
# Needs: dynamodb:Query+GetItem+PutItem+UpdateItem on USER#* keys,
#        secretsmanager:GetSecretValue (OpenAI)
# =============================================================================

resource "aws_iam_role" "interview" {
  name               = "${var.name_prefix}-interview-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "interview_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.interview.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "interview_dynamodb" {
  name = "dynamodb-interview-sessions"
  role = aws_iam_role.interview.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "InterviewSessionOps"
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
      ]
      Resource = [
        var.dynamodb_table_arn,
        "${var.dynamodb_table_arn}/index/*",
      ]
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USER#*"]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "interview_secrets" {
  name = "secrets-openai"
  role = aws_iam_role.interview.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "ReadOpenAISecret"
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.openai_api_key_secret_name}*"
    }]
  })
}

data "archive_file" "interview" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/interview"
  output_path = "${path.module}/../../../dist/lambdas/interview.zip"
}

resource "aws_lambda_function" "interview_start" {
  filename         = data.archive_file.interview.output_path
  function_name    = "${var.name_prefix}-interview-start"
  role             = aws_iam_role.interview.arn
  handler          = "start.lambda_handler"
  source_code_hash = data.archive_file.interview.output_base64sha256
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 512
  layers           = [aws_lambda_layer_version.pdf_processing.arn]

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE     = var.dynamodb_table_name
      OPENAI_SECRET_NAME = var.openai_api_key_secret_name
      ALLOWED_ORIGIN     = var.allowed_origin
      ENVIRONMENT        = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-interview-start"
    Function = "Interview agent - start session"
  })
}

resource "aws_lambda_function" "interview_answer" {
  filename         = data.archive_file.interview.output_path
  function_name    = "${var.name_prefix}-interview-answer"
  role             = aws_iam_role.interview.arn
  handler          = "answer.lambda_handler"
  source_code_hash = data.archive_file.interview.output_base64sha256
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 512
  layers           = [aws_lambda_layer_version.pdf_processing.arn]

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE     = var.dynamodb_table_name
      OPENAI_SECRET_NAME = var.openai_api_key_secret_name
      ALLOWED_ORIGIN     = var.allowed_origin
      ENVIRONMENT        = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-interview-answer"
    Function = "Interview agent - evaluate answer"
  })
}

resource "aws_lambda_function" "interview_exit" {
  filename         = data.archive_file.interview.output_path
  function_name    = "${var.name_prefix}-interview-exit"
  role             = aws_iam_role.interview.arn
  handler          = "exit.lambda_handler"
  source_code_hash = data.archive_file.interview.output_base64sha256
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 256
  layers           = [aws_lambda_layer_version.pdf_processing.arn]

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE     = var.dynamodb_table_name
      OPENAI_SECRET_NAME = var.openai_api_key_secret_name
      ALLOWED_ORIGIN     = var.allowed_origin
      ENVIRONMENT        = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-interview-exit"
    Function = "Interview agent - exit session and generate report"
  })
}

resource "aws_lambda_function" "interview_report" {
  filename         = data.archive_file.interview.output_path
  function_name    = "${var.name_prefix}-interview-report"
  role             = aws_iam_role.interview.arn
  handler          = "report.lambda_handler"
  source_code_hash = data.archive_file.interview.output_base64sha256
  runtime          = "python3.12"
  timeout          = 10
  memory_size      = 256
  layers           = [aws_lambda_layer_version.pdf_processing.arn]

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE     = var.dynamodb_table_name
      OPENAI_SECRET_NAME = var.openai_api_key_secret_name
      ALLOWED_ORIGIN     = var.allowed_origin
      ENVIRONMENT        = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-interview-report"
    Function = "Interview agent - fetch final report"
  })
}
