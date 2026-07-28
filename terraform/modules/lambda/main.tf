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
      Sid    = "WriteUploadRecord"
      Effect = "Allow"
      Action = ["dynamodb:PutItem", "dynamodb:Query"]
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
        Sid      = "PromoteToValidated"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${var.validated_bucket_arn}/*"
      },
      {
        Sid      = "MoveToRejected"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
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
# Needs: s3:GetObject on validated, sqs:SendMessage, dynamodb:UpdateItem+GetItem,
#        lambda:InvokeFunction (portfolio-generator, dedup fast-path only)
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
      # GetObject covers both GetObject and HeadObject in IAM.
      # PutObject lets ingestion persist the extracted text ({id}.txt) so the
      # paused pipeline can resume without re-extracting.
      Sid      = "ReadWriteValidatedResume"
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject"]
      Resource = "${var.validated_bucket_arn}/*"
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
      Action   = ["dynamodb:UpdateItem", "dynamodb:GetItem", "dynamodb:PutItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "resume_ingestion_invoke_classify" {
  name = "invoke-classify-profession"
  role = aws_iam_role.resume_ingestion.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "InvokeClassifyProfession"
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.name_prefix}-classify-profession"
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
      Action   = ["dynamodb:UpdateItem", "dynamodb:PutItem", "dynamodb:GetItem"]
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
      Sid    = "ReadOwnRecords"
      Effect = "Allow"
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
      STALE_UPLOAD_EXPIRY_HOURS    = tostring(var.stale_upload_expiry_hours)
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
  # 120s: extraction (incl. possible OCR) + synchronous profession classify.
  timeout     = 120
  memory_size = 512
  layers      = [aws_lambda_layer_version.pdf_processing.arn]

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      VALIDATED_BUCKET     = var.validated_bucket_name
      DYNAMODB_TABLE       = var.dynamodb_table_name
      CLASSIFY_LAMBDA_NAME = "${var.name_prefix}-classify-profession"
      ENVIRONMENT          = var.environment
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
# 3b. CLASSIFY PROFESSION
# Invoked synchronously by resume_ingestion. Classifies the resume into a
# profession (advisory). Needs: secretsmanager:GetSecretValue (OpenAI key).
# -----------------------------------------------------------------------------

resource "aws_iam_role" "classify_profession" {
  name               = "${var.name_prefix}-classify-profession-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "classify_profession_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.classify_profession.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "classify_profession_secrets" {
  name = "secrets-openai"
  role = aws_iam_role.classify_profession.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "GetOpenAIKey"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.openai_api_key_secret_name}*"
    }]
  })
}

data "archive_file" "classify_profession" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/classify_profession"
  output_path = "${path.module}/../../../dist/lambdas/classify_profession.zip"
}

resource "aws_lambda_function" "classify_profession" {
  filename         = data.archive_file.classify_profession.output_path
  function_name    = "${var.name_prefix}-classify-profession"
  role             = aws_iam_role.classify_profession.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.classify_profession.output_base64sha256
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 256

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      OPENAI_SECRET_NAME = var.openai_api_key_secret_name
      ENVIRONMENT        = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-classify-profession"
    Function = "Resume profession classification"
  })
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
      SQS_MAX_RECEIVE_COUNT = tostring(var.dlq_max_receive_count)
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
# Node.js Lambda — built by build-portfolio-lambda.sh (esbuild bundle).
# Run: bash build-portfolio-lambda.sh  before terraform apply.
# -----------------------------------------------------------------------------

locals {
  portfolio_generator_zip = "${path.module}/../../../dist/lambdas/portfolio_generator.zip"
  frontend_templates_dir  = "${path.module}/../../../../AI-Portfolio-frontend/src/lib/templates"

  # Fingerprint of every input the generator bundle is built from: the frontend
  # templates (shared with the editor preview), the generator handler, and the
  # build script itself. When any of these changes, the bundle is stale and the
  # PUBLISHED site would diverge from the editor preview until rebuilt.
  portfolio_generator_srchash = sha256(join("", concat(
    [for f in fileset(local.frontend_templates_dir, "*.ts") : filesha256("${local.frontend_templates_dir}/${f}")],
    [
      filesha256("${path.module}/../../../src/lambdas/portfolio/handler.ts"),
      filesha256("${path.module}/../../../build-portfolio-lambda.sh"),
    ],
  )))
}

# Auto-rebuild the generator bundle whenever a template/handler/build-script
# source changes — so `terraform apply` alone keeps the published site in sync
# with the templates. This removes the manual, easy-to-forget step of running
# build-portfolio-lambda.sh before applying (a forgotten rebuild silently shipped
# stale templates: preview looked right, deployed site was old).
resource "terraform_data" "build_portfolio_generator" {
  triggers_replace = local.portfolio_generator_srchash

  provisioner "local-exec" {
    command = "bash '${path.module}/../../../build-portfolio-lambda.sh'"
  }
}

resource "aws_lambda_function" "portfolio_generator" {
  filename      = local.portfolio_generator_zip
  function_name = "${var.name_prefix}-portfolio-generator"
  role          = aws_iam_role.portfolio_generator.arn
  handler       = "index.lambdaHandler"
  # Keyed to the SOURCE fingerprint (not the built zip) so plan detects template
  # changes and deploys the freshly-rebuilt bundle in the SAME apply.
  source_code_hash = local.portfolio_generator_srchash
  depends_on       = [terraform_data.build_portfolio_generator]
  runtime          = "nodejs22.x"
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
# 7b. START GENERATION LAMBDA (API)
# Resumes the paused pipeline after the user confirms profession + template.
# Needs: dynamodb GetItem/UpdateItem (USER#*), s3:GetObject (validated text),
#        sqs:SendMessage (processing queue).
# =============================================================================

resource "aws_iam_role" "start_generation" {
  name               = "${var.name_prefix}-start-generation-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "start_generation_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.start_generation.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "start_generation_dynamodb" {
  name = "dynamodb-read-update"
  role = aws_iam_role.start_generation.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadUpdateOwnUpload"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
      Resource = var.dynamodb_table_arn
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USER#*"]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "start_generation_s3" {
  name = "s3-read-validated-text"
  role = aws_iam_role.start_generation.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadValidatedText"
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "${var.validated_bucket_arn}/*"
    }]
  })
}

resource "aws_iam_role_policy" "start_generation_sqs" {
  name = "sqs-send"
  role = aws_iam_role.start_generation.id
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

resource "aws_lambda_function" "start_generation" {
  # Reuses the same auth/ zip as get_portfolio.
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-start-generation"
  role             = aws_iam_role.start_generation.arn
  handler          = "start_generation.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE     = var.dynamodb_table_name
      VALIDATED_BUCKET   = var.validated_bucket_name
      PROCESSING_QUEUE   = var.processing_queue_url
      ALLOWED_ORIGIN     = var.allowed_origin
      GUEST_EMAIL_DOMAIN = var.guest_email_domain
      ENVIRONMENT        = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-start-generation"
    Function = "Resume pipeline after profession selection"
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
  timeout          = 120 # Log files can contain many records
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
      Sid      = "UpdatePortfolioContent"
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem"]
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
      Sid      = "InvokePortfolioGenerator"
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
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
      Sid      = "ReadPortfolioContent"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem"]
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
      Sid      = "GetOpenAIKey"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
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
  timeout          = 29 # API Gateway max synchronous timeout
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
# 13. ADD CUSTOM SECTION LAMBDA
# POST /portfolio/{userId}/custom-section — AI classifier for custom sections.
# Needs: dynamodb:GetItem on USER#* keys, secretsmanager:GetSecretValue (OpenAI).
# Returns a suggestion only — never writes to DynamoDB (reuses ai_enhance role).
# =============================================================================

resource "aws_lambda_function" "add_custom_section" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-add-custom-section"
  role             = aws_iam_role.ai_enhance.arn
  handler          = "add_custom_section.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = 29 # API Gateway max synchronous timeout
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
    Name     = "${var.name_prefix}-add-custom-section"
    Function = "AI custom section classifier - suggestion only"
  })
}

# =============================================================================
# IMAGE UPLOAD URL LAMBDA
# POST /portfolio/{userId}/image-upload-url
# Needs: s3:PutObject on portfolio bucket assets prefix (to sign presigned PUT)
# =============================================================================

resource "aws_iam_role" "get_image_upload_url" {
  name               = "${var.name_prefix}-image-upload-url-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "get_image_upload_url_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.get_image_upload_url.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "get_image_upload_url_s3" {
  name = "s3-presign-portfolio-assets"
  role = aws_iam_role.get_image_upload_url.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "SignPresignedPutAssets"
      Effect   = "Allow"
      Action   = ["s3:PutObject"]
      Resource = "${var.portfolio_bucket_arn}/*/assets/*"
    }]
  })
}

resource "aws_lambda_function" "get_image_upload_url" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-get-image-upload-url"
  role             = aws_iam_role.get_image_upload_url.arn
  handler          = "get_image_upload_url.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      PORTFOLIO_BUCKET             = var.portfolio_bucket_name
      CLOUDFRONT_DOMAIN            = var.cloudfront_domain
      PRESIGNED_URL_EXPIRY_SECONDS = tostring(var.presigned_url_expiry_seconds)
      ALLOWED_ORIGIN               = var.allowed_origin
      ENVIRONMENT                  = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-get-image-upload-url"
    Function = "Generate presigned URL for portfolio image upload"
  })
}

# =============================================================================
# GENERATE PROJECT IMAGE LAMBDA
# POST /portfolio/{userId}/project-image/generate
# Calls DALL-E 3 to generate a project/experience image, stores it in S3,
# returns the CloudFront URL. Does NOT save to DynamoDB — suggestion only.
# Needs: dynamodb:GetItem (read portfolio) + dynamodb:UpdateItem (rate limit counter)
#        s3:PutObject (portfolio bucket assets) + secretsmanager:GetSecretValue (OpenAI)
# =============================================================================

resource "aws_iam_role" "generate_project_image" {
  name               = "${var.name_prefix}-gen-project-image-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "generate_project_image_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.generate_project_image.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "generate_project_image_dynamodb" {
  name = "dynamodb-portfolio-and-ratelimit"
  role = aws_iam_role.generate_project_image.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadPortfolio"
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem"]
        Resource = var.dynamodb_table_arn
        Condition = {
          "ForAllValues:StringLike" = {
            "dynamodb:LeadingKeys" = ["USER#*"]
          }
        }
      },
      {
        Sid      = "RateLimitCounter"
        Effect   = "Allow"
        Action   = ["dynamodb:UpdateItem"]
        Resource = var.dynamodb_table_arn
        Condition = {
          "ForAllValues:StringLike" = {
            "dynamodb:LeadingKeys" = ["USER#*"]
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "generate_project_image_s3" {
  name = "s3-put-portfolio-assets"
  role = aws_iam_role.generate_project_image.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "PutGeneratedImage"
      Effect   = "Allow"
      Action   = ["s3:PutObject"]
      Resource = "${var.portfolio_bucket_arn}/*/assets/*"
    }]
  })
}

resource "aws_iam_role_policy" "generate_project_image_secrets" {
  name = "secrets-openai"
  role = aws_iam_role.generate_project_image.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "GetOpenAIKey"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.openai_api_key_secret_name}*"
    }]
  })
}

resource "aws_lambda_function" "generate_project_image" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-generate-project-image"
  role             = aws_iam_role.generate_project_image.arn
  handler          = "generate_project_image.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = 60 # DALL-E 3 can take 15-20s + download + S3 upload
  memory_size      = 256

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE         = var.dynamodb_table_name
      PORTFOLIO_BUCKET       = var.portfolio_bucket_name
      CLOUDFRONT_DOMAIN      = var.cloudfront_domain
      OPENAI_SECRET_NAME     = var.openai_api_key_secret_name
      DAILY_GENERATION_LIMIT = "10"
      ALLOWED_ORIGIN         = var.allowed_origin
      ENVIRONMENT            = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-generate-project-image"
    Function = "AI project image generation via DALL-E 3"
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
      Sid      = "ReadOpenAISecret"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
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

resource "aws_lambda_function" "interview_sessions" {
  filename         = data.archive_file.interview.output_path
  function_name    = "${var.name_prefix}-interview-sessions"
  role             = aws_iam_role.interview.arn
  handler          = "sessions.lambda_handler"
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
    Name     = "${var.name_prefix}-interview-sessions"
    Function = "Interview agent - list past sessions"
  })
}

# =============================================================================
# PORTFOLIO VERSIONS — cancel upload + list/activate/delete versions
# =============================================================================

resource "aws_iam_role" "portfolio_versions" {
  name               = "${var.name_prefix}-portfolio-versions-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "portfolio_versions_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.portfolio_versions.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "portfolio_versions_dynamodb" {
  name = "dynamodb-versions"
  role = aws_iam_role.portfolio_versions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "VersionOperations"
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
      ]
      Resource = [var.dynamodb_table_arn]
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USER#*"]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "portfolio_versions_s3" {
  name = "s3-delete-versions"
  role = aws_iam_role.portfolio_versions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "DeleteVersionObjects"
      Effect   = "Allow"
      Action   = ["s3:DeleteObject"]
      Resource = "arn:aws:s3:::${var.portfolio_bucket_name}/*"
    }]
  })
}

resource "aws_iam_role_policy" "portfolio_versions_cloudfront" {
  name = "cloudfront-invalidate"
  role = aws_iam_role.portfolio_versions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "InvalidateCache"
      Effect   = "Allow"
      Action   = ["cloudfront:CreateInvalidation"]
      Resource = "*"
    }]
  })
}

resource "aws_lambda_function" "cancel_upload" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-cancel-upload"
  role             = aws_iam_role.portfolio_versions.arn
  handler          = "cancel_upload.lambda_handler"
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
    Name     = "${var.name_prefix}-cancel-upload"
    Function = "Cancel an in-flight upload"
  })
}

resource "aws_lambda_function" "list_versions" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-list-versions"
  role             = aws_iam_role.portfolio_versions.arn
  handler          = "list_versions.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE = var.dynamodb_table_name
      CLOUDFRONT_URL = "https://${var.cloudfront_domain}"
      ALLOWED_ORIGIN = var.allowed_origin
      ENVIRONMENT    = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-list-versions"
    Function = "List portfolio versions"
  })
}

resource "aws_lambda_function" "activate_version" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-activate-version"
  role             = aws_iam_role.portfolio_versions.arn
  handler          = "activate_version.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE             = var.dynamodb_table_name
      CLOUDFRONT_DISTRIBUTION_ID = var.cloudfront_distribution_id
      ALLOWED_ORIGIN             = var.allowed_origin
      ENVIRONMENT                = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-activate-version"
    Function = "Set a portfolio version as live"
  })
}

resource "aws_lambda_function" "delete_version" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-delete-version"
  role             = aws_iam_role.portfolio_versions.arn
  handler          = "delete_version.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE   = var.dynamodb_table_name
      PORTFOLIO_BUCKET = var.portfolio_bucket_name
      ALLOWED_ORIGIN   = var.allowed_origin
      ENVIRONMENT      = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-delete-version"
    Function = "Delete a portfolio version"
  })
}

# =============================================================================
# LIST PORTFOLIOS
# =============================================================================

resource "aws_iam_role" "list_portfolios" {
  name               = "${var.name_prefix}-list-portfolios-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "list_portfolios_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.list_portfolios.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "list_portfolios_dynamodb" {
  name = "dynamodb-list"
  role = aws_iam_role.list_portfolios.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ListPortfolios"
      Effect   = "Allow"
      Action   = ["dynamodb:Query", "dynamodb:GetItem"]
      Resource = [var.dynamodb_table_arn]
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USER#*"]
        }
      }
    }]
  })
}

resource "aws_lambda_function" "list_portfolios" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-list-portfolios"
  role             = aws_iam_role.list_portfolios.arn
  handler          = "list_portfolios.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE = var.dynamodb_table_name
      CLOUDFRONT_URL = "https://${var.cloudfront_domain}"
      ALLOWED_ORIGIN = var.allowed_origin
      ENVIRONMENT    = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-list-portfolios"
    Function = "List all portfolios for a user"
  })
}

# =============================================================================
# TOGGLE PORTFOLIO LIVE
# =============================================================================

resource "aws_iam_role" "toggle_portfolio_live" {
  name               = "${var.name_prefix}-toggle-portfolio-live-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "toggle_portfolio_live_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.toggle_portfolio_live.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "toggle_portfolio_live_dynamodb" {
  name = "dynamodb-toggle"
  role = aws_iam_role.toggle_portfolio_live.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ToggleLive"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
      Resource = [var.dynamodb_table_arn]
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USER#*"]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "toggle_portfolio_live_cloudfront" {
  name = "cloudfront-invalidate"
  role = aws_iam_role.toggle_portfolio_live.id
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

resource "aws_lambda_function" "toggle_portfolio_live" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-toggle-portfolio-live"
  role             = aws_iam_role.toggle_portfolio_live.arn
  handler          = "toggle_portfolio_live.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE             = var.dynamodb_table_name
      CLOUDFRONT_DISTRIBUTION_ID = var.cloudfront_distribution_id
      ALLOWED_ORIGIN             = var.allowed_origin
      ENVIRONMENT                = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-toggle-portfolio-live"
    Function = "Toggle portfolio isLive flag"
  })
}

# =============================================================================
# GET PORTFOLIO PREVIEW URL
# GET /portfolio/{userId}/{uploadId}/preview?versionId=v3
# Owner-only: generates a short-lived presigned S3 URL for any version.
# Needs: dynamodb:GetItem (verify version ownership), s3:GetObject (sign URL).
# =============================================================================

resource "aws_iam_role" "get_portfolio_preview_url" {
  name               = "${var.name_prefix}-portfolio-preview-url-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "get_portfolio_preview_url_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.get_portfolio_preview_url.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "get_portfolio_preview_url_dynamodb" {
  name = "dynamodb-get-version"
  role = aws_iam_role.get_portfolio_preview_url.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadVersionRecord"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem"]
      Resource = var.dynamodb_table_arn
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USER#*"]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "get_portfolio_preview_url_s3" {
  name = "s3-presign-portfolio-read"
  role = aws_iam_role.get_portfolio_preview_url.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "SignPresignedGetUrl"
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "${var.portfolio_bucket_arn}/*"
    }]
  })
}

resource "aws_lambda_function" "get_portfolio_preview_url" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-get-portfolio-preview-url"
  role             = aws_iam_role.get_portfolio_preview_url.arn
  handler          = "get_portfolio_preview_url.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE          = var.dynamodb_table_name
      PORTFOLIO_BUCKET        = var.portfolio_bucket_name
      PREVIEW_URL_TTL_SECONDS = "3600"
      ALLOWED_ORIGIN          = var.allowed_origin
      ENVIRONMENT             = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-get-portfolio-preview-url"
    Function = "Generate presigned S3 URL for owner portfolio preview"
  })
}

# =============================================================================
# DELETE PORTFOLIO
# =============================================================================

resource "aws_iam_role" "delete_portfolio" {
  name               = "${var.name_prefix}-delete-portfolio-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "delete_portfolio_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.delete_portfolio.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "delete_portfolio_dynamodb" {
  name = "dynamodb-delete-portfolio"
  role = aws_iam_role.delete_portfolio.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "DeletePortfolio"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:DeleteItem", "dynamodb:BatchWriteItem"]
      Resource = [var.dynamodb_table_arn]
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USER#*"]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "delete_portfolio_s3" {
  name = "s3-delete-portfolio"
  role = aws_iam_role.delete_portfolio.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListPortfolioObjects"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = "arn:aws:s3:::${var.portfolio_bucket_name}"
      },
      {
        Sid      = "DeletePortfolioObjects"
        Effect   = "Allow"
        Action   = ["s3:DeleteObject"]
        Resource = "arn:aws:s3:::${var.portfolio_bucket_name}/*"
      }
    ]
  })
}

resource "aws_lambda_function" "delete_portfolio" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-delete-portfolio"
  role             = aws_iam_role.delete_portfolio.arn
  handler          = "delete_portfolio.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE   = var.dynamodb_table_name
      PORTFOLIO_BUCKET = var.portfolio_bucket_name
      ALLOWED_ORIGIN   = var.allowed_origin
      ENVIRONMENT      = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-delete-portfolio"
    Function = "Delete an entire portfolio and all its versions"
  })
}

# =============================================================================
# CLAIM GUEST PORTFOLIO
# POST /guest/claim — migrate an anonymous guest's data onto the real account
# that just signed up, publish the chosen portfolio, and delete the guest.
# This is the ONLY Lambda permitted cross-user DynamoDB access; it gates every
# operation on the guest-domain check performed in code.
# =============================================================================

resource "aws_iam_role" "claim_guest" {
  name               = "${var.name_prefix}-claim-guest-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "claim_guest_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.claim_guest.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "claim_guest_dynamodb" {
  name = "dynamodb-migrate"
  role = aws_iam_role.claim_guest.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      # No LeadingKeys condition: migration copies USER#{guest} -> USER#{real}.
      # Cross-user access is gated in code by the guest-domain ownership check.
      Sid    = "MigrateGuestRecords"
      Effect = "Allow"
      Action = [
        "dynamodb:Query",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
      ]
      Resource = [
        var.dynamodb_table_arn,
        "${var.dynamodb_table_arn}/index/*",
      ]
    }]
  })
}

resource "aws_iam_role_policy" "claim_guest_s3" {
  name = "s3-migrate"
  role = aws_iam_role.claim_guest.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListPipelineBuckets"
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = [
          var.portfolio_bucket_arn,
          var.validated_bucket_arn,
          var.quarantine_bucket_arn,
        ]
      },
      {
        Sid    = "CopyDeletePipelineObjects"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = [
          "${var.portfolio_bucket_arn}/*",
          "${var.validated_bucket_arn}/*",
          "${var.quarantine_bucket_arn}/*",
        ]
      },
    ]
  })
}

resource "aws_iam_role_policy" "claim_guest_invoke" {
  name = "lambda-invoke-portfolio-generator"
  role = aws_iam_role.claim_guest.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "InvokePortfolioGenerator"
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.name_prefix}-portfolio-generator"
    }]
  })
}

resource "aws_iam_role_policy" "claim_guest_cognito" {
  name = "cognito-guest-admin"
  role = aws_iam_role.claim_guest.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "InspectAndDeleteGuest"
      Effect = "Allow"
      # GetUser validates the guest's own access token (proof of session
      # possession) so the claim isn't authorized from an asserted sub.
      Action   = ["cognito-idp:AdminGetUser", "cognito-idp:AdminDeleteUser", "cognito-idp:GetUser"]
      Resource = var.user_pool_arn
    }]
  })
}

resource "aws_lambda_function" "claim_guest" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-claim-guest"
  role             = aws_iam_role.claim_guest.arn
  handler          = "claim_guest.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = 60 # DynamoDB re-key + S3 copy across multiple uploads
  memory_size      = 256

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE        = var.dynamodb_table_name
      PORTFOLIO_BUCKET      = var.portfolio_bucket_name
      VALIDATED_BUCKET      = var.validated_bucket_name
      QUARANTINE_BUCKET     = var.quarantine_bucket_name
      PORTFOLIO_LAMBDA_NAME = "${var.name_prefix}-portfolio-generator"
      USER_POOL_ID          = var.user_pool_id
      GUEST_EMAIL_DOMAIN    = var.guest_email_domain
      ALLOWED_ORIGIN        = var.allowed_origin
      ENVIRONMENT           = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-claim-guest"
    Function = "Migrate guest portfolio to a real account and publish"
  })
}

# =============================================================================
# GUEST REAPER
# Scheduled (EventBridge) deletion of abandoned guest accounts older than the
# guest TTL, along with all their DynamoDB + S3 data.
# =============================================================================

resource "aws_iam_role" "guest_reaper" {
  name               = "${var.name_prefix}-guest-reaper-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "guest_reaper_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.guest_reaper.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "guest_reaper_cognito" {
  name = "cognito-list-delete-guests"
  role = aws_iam_role.guest_reaper.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ListAndDeleteGuests"
      Effect   = "Allow"
      Action   = ["cognito-idp:ListUsers", "cognito-idp:AdminDeleteUser"]
      Resource = var.user_pool_arn
    }]
  })
}

resource "aws_iam_role_policy" "guest_reaper_dynamodb" {
  name = "dynamodb-delete-guest"
  role = aws_iam_role.guest_reaper.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "DeleteGuestRecords"
      Effect   = "Allow"
      Action   = ["dynamodb:Query", "dynamodb:DeleteItem"]
      Resource = var.dynamodb_table_arn
    }]
  })
}

resource "aws_iam_role_policy" "guest_reaper_s3" {
  name = "s3-delete-guest"
  role = aws_iam_role.guest_reaper.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListPipelineBuckets"
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = [
          var.portfolio_bucket_arn,
          var.validated_bucket_arn,
          var.quarantine_bucket_arn,
        ]
      },
      {
        Sid    = "DeletePipelineObjects"
        Effect = "Allow"
        Action = ["s3:DeleteObject"]
        Resource = [
          "${var.portfolio_bucket_arn}/*",
          "${var.validated_bucket_arn}/*",
          "${var.quarantine_bucket_arn}/*",
        ]
      },
    ]
  })
}

data "archive_file" "guest_reaper" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/guest_reaper"
  output_path = "${path.module}/../../../dist/lambdas/guest_reaper.zip"
}

resource "aws_lambda_function" "guest_reaper" {
  filename         = data.archive_file.guest_reaper.output_path
  function_name    = "${var.name_prefix}-guest-reaper"
  role             = aws_iam_role.guest_reaper.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.guest_reaper.output_base64sha256
  runtime          = "python3.12"
  timeout          = 300 # may iterate many stale guests in one run
  memory_size      = 256

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      USER_POOL_ID       = var.user_pool_id
      DYNAMODB_TABLE     = var.dynamodb_table_name
      PORTFOLIO_BUCKET   = var.portfolio_bucket_name
      VALIDATED_BUCKET   = var.validated_bucket_name
      QUARANTINE_BUCKET  = var.quarantine_bucket_name
      GUEST_EMAIL_DOMAIN = var.guest_email_domain
      GUEST_TTL_HOURS    = tostring(var.guest_ttl_hours)
      ENVIRONMENT        = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-guest-reaper"
    Function = "Delete abandoned guest accounts and their data"
  })
}

# Run the reaper hourly. The Lambda itself enforces the TTL grace window.
resource "aws_cloudwatch_event_rule" "guest_reaper" {
  name                = "${var.name_prefix}-guest-reaper-schedule"
  description         = "Periodically delete abandoned guest accounts"
  schedule_expression = "rate(1 hour)"
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "guest_reaper" {
  rule      = aws_cloudwatch_event_rule.guest_reaper.name
  target_id = "guest-reaper"
  arn       = aws_lambda_function.guest_reaper.arn
}

resource "aws_lambda_permission" "guest_reaper_events" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.guest_reaper.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.guest_reaper.arn
}

# =============================================================================
# USERNAME AVAILABILITY CHECK (PUBLIC API)
# =============================================================================
# GET /username/check?username=xyz — no authorizer, because the caller has no
# account yet. Read-only and scoped to USERNAME#* keys, so the worst a scraper
# can learn is which public handles are taken — which the portfolio URLs
# already reveal.
# =============================================================================

resource "aws_iam_role" "check_username" {
  name               = "${var.name_prefix}-check-username-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "check_username_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.check_username.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "check_username_dynamodb" {
  name = "dynamodb-username-read"
  role = aws_iam_role.check_username.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadUsernameIndex"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem"]
      Resource = [var.dynamodb_table_arn]
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USERNAME#*"]
        }
      }
    }]
  })
}

resource "aws_lambda_function" "check_username" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-check-username"
  role             = aws_iam_role.check_username.arn
  handler          = "check_username.lambda_handler"
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
    Name     = "${var.name_prefix}-check-username"
    Function = "Public username availability check"
  })
}

# =============================================================================
# USER PROFILE (GET / PATCH)
# =============================================================================
# Reads and edits the caller's own profile. The rename is a TransactWriteItems
# spanning USERNAME#{new}, USERNAME#{old} and USER#{sub}, so the policy has to
# cover both key prefixes. Cognito write access is limited to
# AdminUpdateUserAttributes, used only to mirror preferred_username.
# =============================================================================

resource "aws_iam_role" "profile" {
  name               = "${var.name_prefix}-profile-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "profile_logs" {
  name   = "cloudwatch-logs"
  role   = aws_iam_role.profile.id
  policy = data.aws_iam_policy_document.cloudwatch_logs.json
}

resource "aws_iam_role_policy" "profile_dynamodb" {
  name = "dynamodb-profile-rw"
  role = aws_iam_role.profile.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "ReadWriteOwnProfileAndUsername"
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
      ]
      Resource = [var.dynamodb_table_arn]
      Condition = {
        "ForAllValues:StringLike" = {
          "dynamodb:LeadingKeys" = ["USER#*", "USERNAME#*"]
        }
      }
      }, {
      # TransactWriteItems is not evaluated against LeadingKeys the same way as
      # single-item writes, so it is granted separately on the same table.
      Sid      = "RenameTransaction"
      Effect   = "Allow"
      Action   = ["dynamodb:TransactWriteItems"]
      Resource = [var.dynamodb_table_arn]
    }]
  })
}

resource "aws_iam_role_policy" "profile_cognito" {
  name = "cognito-mirror-username"
  role = aws_iam_role.profile.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "MirrorPreferredUsername"
      Effect   = "Allow"
      Action   = ["cognito-idp:AdminUpdateUserAttributes"]
      Resource = [var.user_pool_arn]
    }]
  })
}

resource "aws_lambda_function" "profile" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-profile"
  role             = aws_iam_role.profile.arn
  handler          = "profile.lambda_handler"
  source_code_hash = data.archive_file.get_portfolio.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.timeout
  memory_size      = var.memory_size

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE                = var.dynamodb_table_name
      USER_POOL_ID                  = var.user_pool_id
      ALLOWED_ORIGIN                = var.allowed_origin
      USERNAME_CHANGE_COOLDOWN_DAYS = var.username_change_cooldown_days
      ENVIRONMENT                   = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-profile"
    # AWS tag values allow only [letters numbers whitespace _ . : / = + - @].
    # Apostrophes, parentheses and commas fail CreateFunction.
    Function = "Read and edit the callers own profile - username and display name"
  })
}
