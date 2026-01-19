# =============================================================================
# OUTPUTS
# =============================================================================

# -----------------------------------------------------------------------------
# GENERAL
# -----------------------------------------------------------------------------

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "environment" {
  description = "Deployment environment"
  value       = var.environment
}

output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

# -----------------------------------------------------------------------------
# S3 BUCKETS
# -----------------------------------------------------------------------------

output "quarantine_bucket_name" {
  description = "Name of the quarantine bucket (untrusted uploads)"
  value       = module.s3.quarantine_bucket_name
}

output "validated_bucket_name" {
  description = "Name of the validated bucket (trusted files)"
  value       = module.s3.validated_bucket_name
}

output "rejected_bucket_name" {
  description = "Name of the rejected bucket (failed validation)"
  value       = module.s3.rejected_bucket_name
}

output "portfolio_bucket_name" {
  description = "Name of the portfolio bucket (generated sites)"
  value       = module.s3.portfolio_bucket_name
}

# -----------------------------------------------------------------------------
# DYNAMODB
# -----------------------------------------------------------------------------

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = module.dynamodb.table_name
}

# -----------------------------------------------------------------------------
# SQS
# -----------------------------------------------------------------------------

output "processing_queue_url" {
  description = "URL of the resume processing queue"
  value       = module.sqs.processing_queue_url
}

output "dlq_url" {
  description = "URL of the dead letter queue"
  value       = module.sqs.dlq_url
}

# -----------------------------------------------------------------------------
# COGNITO
# -----------------------------------------------------------------------------

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = module.cognito.user_pool_client_id
}

output "cognito_domain" {
  description = "Cognito hosted UI domain"
  value       = module.cognito.domain
}

# -----------------------------------------------------------------------------
# API GATEWAY
# -----------------------------------------------------------------------------

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = module.api_gateway.api_endpoint
}

output "api_id" {
  description = "API Gateway ID"
  value       = module.api_gateway.api_id
}

# -----------------------------------------------------------------------------
# CLOUDFRONT
# -----------------------------------------------------------------------------

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.cloudfront.distribution_id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = module.cloudfront.domain_name
}

output "portfolio_url" {
  description = "Base URL for portfolio websites"
  value       = "https://${module.cloudfront.domain_name}"
}
