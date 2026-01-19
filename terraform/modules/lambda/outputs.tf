# Get Presigned URL Lambda
output "get_presigned_url_arn" {
  description = "ARN of the get presigned URL Lambda"
  value       = aws_lambda_function.get_presigned_url.arn
}

output "get_presigned_url_invoke_arn" {
  description = "Invoke ARN of the get presigned URL Lambda"
  value       = aws_lambda_function.get_presigned_url.invoke_arn
}

output "get_presigned_url_name" {
  description = "Name of the get presigned URL Lambda"
  value       = aws_lambda_function.get_presigned_url.function_name
}

# Quarantine Validator Lambda
output "quarantine_validator_arn" {
  description = "ARN of the quarantine validator Lambda"
  value       = aws_lambda_function.quarantine_validator.arn
}

output "quarantine_validator_name" {
  description = "Name of the quarantine validator Lambda"
  value       = aws_lambda_function.quarantine_validator.function_name
}

# Resume Ingestion Lambda
output "resume_ingestion_arn" {
  description = "ARN of the resume ingestion Lambda"
  value       = aws_lambda_function.resume_ingestion.arn
}

output "resume_ingestion_name" {
  description = "Name of the resume ingestion Lambda"
  value       = aws_lambda_function.resume_ingestion.function_name
}

# AI Processing Lambda
output "ai_processing_arn" {
  description = "ARN of the AI processing Lambda"
  value       = aws_lambda_function.ai_processing.arn
}

output "ai_processing_name" {
  description = "Name of the AI processing Lambda"
  value       = aws_lambda_function.ai_processing.function_name
}

# Portfolio Generator Lambda
output "portfolio_generator_arn" {
  description = "ARN of the portfolio generator Lambda"
  value       = aws_lambda_function.portfolio_generator.arn
}

output "portfolio_generator_name" {
  description = "Name of the portfolio generator Lambda"
  value       = aws_lambda_function.portfolio_generator.function_name
}

# Get Portfolio Lambda (API)
output "get_portfolio_arn" {
  description = "ARN of the get portfolio Lambda"
  value       = aws_lambda_function.get_portfolio.arn
}

output "get_portfolio_invoke_arn" {
  description = "Invoke ARN of the get portfolio Lambda"
  value       = aws_lambda_function.get_portfolio.invoke_arn
}

output "get_portfolio_name" {
  description = "Name of the get portfolio Lambda"
  value       = aws_lambda_function.get_portfolio.function_name
}

# Get Status Lambda (API)
output "get_status_arn" {
  description = "ARN of the get status Lambda"
  value       = aws_lambda_function.get_status.arn
}

output "get_status_invoke_arn" {
  description = "Invoke ARN of the get status Lambda"
  value       = aws_lambda_function.get_status.invoke_arn
}

output "get_status_name" {
  description = "Name of the get status Lambda"
  value       = aws_lambda_function.get_status.function_name
}

# IAM Role
output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "lambda_execution_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.name
}
