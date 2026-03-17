# ---------------------------------------------------------------------------
# MAIN TABLE
# ---------------------------------------------------------------------------

output "table_name" {
  description = "Name of the main DynamoDB table"
  value       = aws_dynamodb_table.main.name
}

output "table_arn" {
  description = "ARN of the main DynamoDB table"
  value       = aws_dynamodb_table.main.arn
}

output "table_id" {
  description = "ID of the main DynamoDB table"
  value       = aws_dynamodb_table.main.id
}

# ---------------------------------------------------------------------------
# PII TABLE
# ---------------------------------------------------------------------------

output "pii_table_name" {
  description = "Name of the PII DynamoDB table"
  value       = aws_dynamodb_table.pii.name
}

output "pii_table_arn" {
  description = "ARN of the PII DynamoDB table"
  value       = aws_dynamodb_table.pii.arn
}

output "pii_kms_key_arn" {
  description = "ARN of the KMS key used to encrypt the PII table"
  value       = aws_kms_key.pii.arn
}

# ---------------------------------------------------------------------------
# ANALYTICS TABLE
# ---------------------------------------------------------------------------

output "analytics_table_name" {
  description = "Name of the analytics DynamoDB table"
  value       = aws_dynamodb_table.analytics.name
}

output "analytics_table_arn" {
  description = "ARN of the analytics DynamoDB table"
  value       = aws_dynamodb_table.analytics.arn
}
