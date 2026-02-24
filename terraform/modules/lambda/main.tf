# =============================================================================
# LAMBDA MODULE
# =============================================================================
# Lambda functions for the AI Portfolio pipeline:
# 1. getPresignedUrl - Generate presigned URLs for uploads
# 2. quarantineValidator - Validate files in quarantine bucket
# 3. resumeIngestion - Extract text from validated resumes
# 4. aiProcessing - Call OpenAI for resume parsing
# 5. portfolioGenerator - Generate static portfolio HTML
# 6. getPortfolio - Retrieve portfolio data
# 7. getStatus - Get processing status
# =============================================================================

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# -----------------------------------------------------------------------------
# COMMON IAM ROLE FOR ALL LAMBDAS
# -----------------------------------------------------------------------------

resource "aws_iam_role" "lambda_execution" {
  name = "${var.name_prefix}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Basic Lambda execution policy (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# -----------------------------------------------------------------------------
# S3 ACCESS POLICY
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "s3_access" {
  name = "${var.name_prefix}-lambda-s3-access"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "QuarantineBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.quarantine_bucket_arn,
          "${var.quarantine_bucket_arn}/*"
        ]
      },
      {
        Sid    = "ValidatedBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.validated_bucket_arn,
          "${var.validated_bucket_arn}/*"
        ]
      },
      {
        Sid    = "RejectedBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = [
          var.rejected_bucket_arn,
          "${var.rejected_bucket_arn}/*"
        ]
      },
      {
        Sid    = "PortfolioBucketAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.portfolio_bucket_arn,
          "${var.portfolio_bucket_arn}/*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# DYNAMODB ACCESS POLICY
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "dynamodb_access" {
  name = "${var.name_prefix}-lambda-dynamodb-access"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          var.dynamodb_table_arn,
          "${var.dynamodb_table_arn}/index/*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# SQS ACCESS POLICY
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "sqs_access" {
  name = "${var.name_prefix}-lambda-sqs-access"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SQSAccess"
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = var.processing_queue_arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# SECRETS MANAGER ACCESS POLICY (for OpenAI API key)
# -----------------------------------------------------------------------------

resource "aws_iam_role_policy" "secrets_access" {
  name = "${var.name_prefix}-lambda-secrets-access"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SecretsAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.openai_api_key_secret_name}*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_invoke" {
  name = "${var.name_prefix}-lambda-invoke-access"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokePortfolioGenerator"
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.name_prefix}-portfolio-generator"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# LAMBDA LAYER (shared dependencies)
# -----------------------------------------------------------------------------

# Placeholder for Lambda layer - will be built separately
# resource "aws_lambda_layer_version" "shared" {
#   filename            = "${path.module}/../../../dist/layers/shared.zip"
#   layer_name          = "${var.name_prefix}-shared-layer"
#   compatible_runtimes = ["python3.11", "python3.12"]
#   description         = "Shared dependencies for Lambda functions"
# }

# -----------------------------------------------------------------------------
# 1. GET PRESIGNED URL LAMBDA
# -----------------------------------------------------------------------------

data "archive_file" "get_presigned_url" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/upload"
  output_path = "${path.module}/../../../dist/lambdas/get_presigned_url.zip"
}

resource "aws_lambda_function" "get_presigned_url" {
  filename         = data.archive_file.get_presigned_url.output_path
  function_name    = "${var.name_prefix}-get-presigned-url"
  role             = aws_iam_role.lambda_execution.arn
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
# 2. QUARANTINE VALIDATOR LAMBDA
# -----------------------------------------------------------------------------

data "archive_file" "quarantine_validator" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/validation"
  output_path = "${path.module}/../../../dist/lambdas/quarantine_validator.zip"
}

resource "aws_lambda_function" "quarantine_validator" {
  filename         = data.archive_file.quarantine_validator.output_path
  function_name    = "${var.name_prefix}-quarantine-validator"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.quarantine_validator.output_base64sha256
  runtime          = "python3.12"
  timeout          = 60  # Validation may take longer
  memory_size      = 512 # More memory for file processing

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

# S3 trigger permission for quarantine validator
resource "aws_lambda_permission" "quarantine_s3_trigger" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.quarantine_validator.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.quarantine_bucket_arn
}

# -----------------------------------------------------------------------------
# 3. RESUME INGESTION LAMBDA
# -----------------------------------------------------------------------------

data "archive_file" "resume_ingestion" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/ingestion"
  output_path = "${path.module}/../../../dist/lambdas/resume_ingestion.zip"
}

resource "aws_lambda_function" "resume_ingestion" {
  filename         = data.archive_file.resume_ingestion.output_path
  function_name    = "${var.name_prefix}-resume-ingestion"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.resume_ingestion.output_base64sha256
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 512

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      VALIDATED_BUCKET   = var.validated_bucket_name
      DYNAMODB_TABLE     = var.dynamodb_table_name
      PROCESSING_QUEUE   = var.processing_queue_url
      ENVIRONMENT        = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-resume-ingestion"
    Function = "Resume text extraction"
  })
}

# S3 trigger permission for resume ingestion
resource "aws_lambda_permission" "validated_s3_trigger" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.resume_ingestion.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.validated_bucket_arn
}

# -----------------------------------------------------------------------------
# 4. AI PROCESSING LAMBDA
# -----------------------------------------------------------------------------

data "archive_file" "ai_processing" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/ai_processing"
  output_path = "${path.module}/../../../dist/lambdas/ai_processing.zip"
}

resource "aws_lambda_function" "ai_processing" {
  filename         = data.archive_file.ai_processing.output_path
  function_name    = "${var.name_prefix}-ai-processing"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.ai_processing.output_base64sha256
  runtime          = "python3.12"
  timeout          = 300  # AI calls can be slow
  memory_size      = 512

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      DYNAMODB_TABLE            = var.dynamodb_table_name
      OPENAI_SECRET_NAME        = var.openai_api_key_secret_name
      PORTFOLIO_BUCKET          = var.portfolio_bucket_name
      ENVIRONMENT               = var.environment
      PORTFOLIO_LAMBDA_NAME     = "${var.name_prefix}-portfolio-generator"
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-ai-processing"
    Function = "OpenAI resume parsing"
  })
}

# SQS trigger for AI processing
resource "aws_lambda_event_source_mapping" "ai_processing_sqs" {
  event_source_arn = var.processing_queue_arn
  function_name    = aws_lambda_function.ai_processing.arn
  batch_size       = 1  # Process one at a time for AI calls

  scaling_config {
    maximum_concurrency = 5  # Limit concurrent AI calls
  }
}

# -----------------------------------------------------------------------------
# 5. PORTFOLIO GENERATOR LAMBDA
# -----------------------------------------------------------------------------

data "archive_file" "portfolio_generator" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/portfolio"
  output_path = "${path.module}/../../../dist/lambdas/portfolio_generator.zip"
}

resource "aws_lambda_function" "portfolio_generator" {
  filename         = data.archive_file.portfolio_generator.output_path
  function_name    = "${var.name_prefix}-portfolio-generator"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.portfolio_generator.output_base64sha256
  runtime          = "python3.12"
  timeout          = 60
  memory_size      = 256

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = {
      PORTFOLIO_BUCKET = var.portfolio_bucket_name
      DYNAMODB_TABLE   = var.dynamodb_table_name
      ENVIRONMENT      = var.environment
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.name_prefix}-portfolio-generator"
    Function = "Static portfolio HTML generation"
  })
}

# -----------------------------------------------------------------------------
# 6. GET PORTFOLIO LAMBDA (API)
# -----------------------------------------------------------------------------

data "archive_file" "get_portfolio" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambdas/auth"
  output_path = "${path.module}/../../../dist/lambdas/get_portfolio.zip"
}

resource "aws_lambda_function" "get_portfolio" {
  filename         = data.archive_file.get_portfolio.output_path
  function_name    = "${var.name_prefix}-get-portfolio"
  role             = aws_iam_role.lambda_execution.arn
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
# 7. GET STATUS LAMBDA (API)
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "get_status" {
  filename         = data.archive_file.get_portfolio.output_path  # Reuse same zip
  function_name    = "${var.name_prefix}-get-status"
  role             = aws_iam_role.lambda_execution.arn
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
