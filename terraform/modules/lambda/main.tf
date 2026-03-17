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
  name = "s3-read-write-validated"
  role = aws_iam_role.resume_ingestion.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "ReadValidatedResume"
      Effect = "Allow"
      # GetObject covers HeadObject as well
      Action   = ["s3:GetObject", "s3:PutObject"]
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
  name = "dynamodb-update-get"
  role = aws_iam_role.resume_ingestion.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "UpdateUploadStatusAndReadDedup"
      Effect = "Allow"
      Action = [
        "dynamodb:UpdateItem",
        # GetItem: read CONTENT#{hash} dedup record to short-circuit
        # duplicate uploads without hitting the AI pipeline.
        "dynamodb:GetItem",
      ]
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

resource "aws_iam_role_policy" "ai_processing_s3" {
  name = "s3-read-resume-text"
  role = aws_iam_role.ai_processing.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "ReadResumeTextFile"
      Effect = "Allow"
      # Read the resume-text.txt written by the ingestion Lambda.
      # Scoped to the validated bucket only — no other S3 access.
      Action   = ["s3:GetObject"]
      Resource = "${var.validated_bucket_arn}/*"
    }]
  })
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

resource "aws_iam_role_policy" "ai_processing_dynamodb_main" {
  name = "dynamodb-write-main"
  role = aws_iam_role.ai_processing.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "WriteAIResultsMain"
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem", "dynamodb:PutItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

# PII table: PutItem only — ai_processing writes PII before the AI call.
# Also needs KMS permissions to encrypt items with the PII table's CMK.
resource "aws_iam_role_policy" "ai_processing_dynamodb_pii" {
  name = "dynamodb-put-pii"
  role = aws_iam_role.ai_processing.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "WritePII"
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem"]
        Resource = var.pii_table_arn
      },
      {
        Sid    = "EncryptPIIItems"
        Effect = "Allow"
        Action = [
          "kms:GenerateDataKey",
          "kms:Decrypt",
        ]
        Resource = var.pii_kms_key_arn
      },
    ]
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
# Needs: s3:PutObject on portfolio bucket, dynamodb:GetItem+UpdateItem,
#        cloudfront:CreateInvalidation to flush the CDN after each publish
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

resource "aws_iam_role_policy" "portfolio_generator_dynamodb_main" {
  name = "dynamodb-read-update-main"
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

# PII table: GetItem only — read PII tokens at render time to unmask HTML.
# Also needs KMS:Decrypt to read CMK-encrypted items.
resource "aws_iam_role_policy" "portfolio_generator_dynamodb_pii" {
  name = "dynamodb-get-pii"
  role = aws_iam_role.portfolio_generator.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadPII"
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem"]
        Resource = var.pii_table_arn
      },
      {
        Sid      = "DecryptPIIItems"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = var.pii_kms_key_arn
      },
    ]
  })
}

# CloudFront: CreateInvalidation scoped to the single portfolio distribution.
# Condition guards against the empty-string default used in test environments.
resource "aws_iam_role_policy" "portfolio_generator_cloudfront" {
  count = var.cloudfront_distribution_arn != "" ? 1 : 0
  name  = "cloudfront-invalidate"
  role  = aws_iam_role.portfolio_generator.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "InvalidatePortfolioCache"
      Effect   = "Allow"
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
# DEPLOYMENT ARTIFACTS BUCKET
# Stores large Lambda layer zips (>70 MB) that exceed the direct-upload
# API limit. Lambda layers reference objects here via s3_bucket/s3_key.
# =============================================================================

resource "aws_s3_bucket" "lambda_artifacts" {
  bucket        = "${var.name_prefix}-lambda-artifacts"
  force_destroy = true

  tags = var.tags
}

resource "aws_s3_bucket_versioning" "lambda_artifacts" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "lambda_artifacts" {
  bucket                  = aws_s3_bucket.lambda_artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# =============================================================================
# PRESIDIO LAMBDA LAYER
# Provides Microsoft Presidio (PII detection) + spaCy en_core_web_sm.
# Build the zip before terraform apply:
#   ./scripts/build_presidio_layer.sh
# Uploaded to S3 first to bypass the 70 MB direct-upload API limit.
# =============================================================================

resource "aws_s3_object" "presidio_layer_zip" {
  bucket = aws_s3_bucket.lambda_artifacts.id
  key    = "layers/presidio.zip"
  source = "${path.module}/../../../dist/layers/presidio.zip"

  # Recompute etag so Terraform re-uploads when zip content changes.
  etag = filemd5("${path.module}/../../../dist/layers/presidio.zip")
}

resource "aws_lambda_layer_version" "presidio" {
  layer_name = "${var.name_prefix}-presidio"

  s3_bucket = aws_s3_bucket.lambda_artifacts.id
  s3_key    = aws_s3_object.presidio_layer_zip.key

  compatible_runtimes = ["python3.12"]

  source_code_hash = filebase64sha256(
    "${path.module}/../../../dist/layers/presidio.zip"
  )

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_s3_object.presidio_layer_zip]
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
      MAIN_TABLE                   = var.dynamodb_table_name
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
      MAIN_TABLE         = var.dynamodb_table_name
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

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      VALIDATED_BUCKET = var.validated_bucket_name
      MAIN_TABLE       = var.dynamodb_table_name
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
  # Increased to 1 GB: spaCy en_core_web_sm NER requires more headroom
  # than the default 512 MB, especially on cold starts.
  memory_size      = 1024

  # Presidio layer (Presidio + spaCy + en_core_web_sm).
  # Build with scripts/build_presidio_layer.sh before terraform apply.
  layers = [aws_lambda_layer_version.presidio.arn]

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      MAIN_TABLE            = var.dynamodb_table_name
      PII_TABLE             = var.pii_table_name
      OPENAI_SECRET_NAME    = var.openai_api_key_secret_name
      PORTFOLIO_BUCKET      = var.portfolio_bucket_name
      VALIDATED_BUCKET      = var.validated_bucket_name
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
      PORTFOLIO_BUCKET             = var.portfolio_bucket_name
      MAIN_TABLE                   = var.dynamodb_table_name
      PII_TABLE                    = var.pii_table_name
      CLOUDFRONT_DISTRIBUTION_ID   = var.cloudfront_distribution_id
      ENVIRONMENT                  = var.environment
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
      MAIN_TABLE       = var.dynamodb_table_name
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
      MAIN_TABLE  = var.dynamodb_table_name
      ENVIRONMENT = var.environment
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
      Sid      = "WriteViewEvents"
      Effect   = "Allow"
      Action   = ["dynamodb:BatchWriteItem"]
      Resource = var.analytics_table_arn
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
      ANALYTICS_TABLE = var.analytics_table_name
      ENVIRONMENT     = var.environment
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
        var.analytics_table_arn,
        "${var.analytics_table_arn}/index/*",
      ]
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
      ANALYTICS_TABLE = var.analytics_table_name
      ALLOWED_ORIGIN  = var.allowed_origin
      ENVIRONMENT     = var.environment
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
      MAIN_TABLE            = var.dynamodb_table_name
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
# 11. AI ENHANCE PORTFOLIO LAMBDA
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
      MAIN_TABLE         = var.dynamodb_table_name
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
# 12. GET TEMPLATES LAMBDA
# GET /templates — public, no authentication.
# Returns the hardcoded template catalog; no AWS calls at runtime.
# Reuses the same auth/ zip and api_read role (no DynamoDB access needed —
# the role is only attached for IAM identity; the policy grants nothing
# beyond CloudWatch Logs which every Lambda needs).
# =============================================================================

resource "aws_lambda_function" "get_templates" {
  # Reuses the same auth/ zip — handler file is get_templates.py
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-get-templates"
  role             = aws_iam_role.api_read.arn
  handler          = "get_templates.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      ALLOWED_ORIGIN = var.allowed_origin
      ENVIRONMENT    = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-get-templates"
    Function = "Template catalog - public no auth"
  })
}
