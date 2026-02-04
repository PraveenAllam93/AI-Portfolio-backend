# =============================================================================
# USER INFO LAMBDA - STANDALONE CONFIGURATION
# =============================================================================
# Creates a Lambda function that extracts user info from Cognito JWT token
# This Lambda is deployed independently and used by API Gateway
# =============================================================================

# Package Lambda function
data "archive_file" "user_info_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambdas/user-info"
  output_path = "${path.module}/../dist/lambdas/user_info.zip"
}

# IAM Role for User Info Lambda
resource "aws_iam_role" "user_info_lambda" {
  name = "${local.name_prefix}-user-info-lambda-role"

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

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-user-info-lambda-role"
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "user_info_lambda_basic" {
  role       = aws_iam_role.user_info_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda Function - Get User Info
resource "aws_lambda_function" "get_user_info" {
  filename         = data.archive_file.user_info_lambda.output_path
  function_name    = "${local.name_prefix}-get-user-info"
  role             = aws_iam_role.user_info_lambda.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.user_info_lambda.output_base64sha256
  runtime          = "python3.12"
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }

  tags = merge(local.common_tags, {
    Name     = "${local.name_prefix}-get-user-info"
    Function = "Get user info from JWT token"
  })
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "user_info_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.get_user_info.function_name}"
  retention_in_days = 7

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-user-info-logs"
  })
}

# Output Lambda ARNs for API Gateway module
output "get_user_info_lambda_arn" {
  description = "ARN of the get user info Lambda"
  value       = aws_lambda_function.get_user_info.arn
}

output "get_user_info_lambda_invoke_arn" {
  description = "Invoke ARN of the get user info Lambda"
  value       = aws_lambda_function.get_user_info.invoke_arn
}

output "get_user_info_lambda_name" {
  description = "Name of the get user info Lambda"
  value       = aws_lambda_function.get_user_info.function_name
}
