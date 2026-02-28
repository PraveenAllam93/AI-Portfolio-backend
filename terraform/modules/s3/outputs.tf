# Quarantine bucket
output "quarantine_bucket_name" {
  description = "Name of the quarantine bucket"
  value       = aws_s3_bucket.quarantine.bucket
}

output "quarantine_bucket_arn" {
  description = "ARN of the quarantine bucket"
  value       = aws_s3_bucket.quarantine.arn
}

output "quarantine_bucket_id" {
  description = "ID of the quarantine bucket"
  value       = aws_s3_bucket.quarantine.id
}

# Validated bucket
output "validated_bucket_name" {
  description = "Name of the validated bucket"
  value       = aws_s3_bucket.validated.bucket
}

output "validated_bucket_arn" {
  description = "ARN of the validated bucket"
  value       = aws_s3_bucket.validated.arn
}

output "validated_bucket_id" {
  description = "ID of the validated bucket"
  value       = aws_s3_bucket.validated.id
}

# Rejected bucket
output "rejected_bucket_name" {
  description = "Name of the rejected bucket"
  value       = aws_s3_bucket.rejected.bucket
}

output "rejected_bucket_arn" {
  description = "ARN of the rejected bucket"
  value       = aws_s3_bucket.rejected.arn
}

output "rejected_bucket_id" {
  description = "ID of the rejected bucket"
  value       = aws_s3_bucket.rejected.id
}

# Portfolio bucket
output "portfolio_bucket_name" {
  description = "Name of the portfolio bucket"
  value       = aws_s3_bucket.portfolio.bucket
}

output "portfolio_bucket_arn" {
  description = "ARN of the portfolio bucket"
  value       = aws_s3_bucket.portfolio.arn
}

output "portfolio_bucket_id" {
  description = "ID of the portfolio bucket"
  value       = aws_s3_bucket.portfolio.id
}

output "portfolio_bucket_domain" {
  description = "Regional domain name of the portfolio bucket"
  value       = aws_s3_bucket.portfolio.bucket_regional_domain_name
}

# Access logs bucket
output "access_logs_bucket_name" {
  description = "Name of the CloudFront access logs bucket"
  value       = aws_s3_bucket.access_logs.bucket
}

output "access_logs_bucket_arn" {
  description = "ARN of the CloudFront access logs bucket"
  value       = aws_s3_bucket.access_logs.arn
}

output "access_logs_bucket_id" {
  description = "ID of the CloudFront access logs bucket"
  value       = aws_s3_bucket.access_logs.id
}

output "access_logs_bucket_domain" {
  description = "Domain name for use in CloudFront logging_config (must be bucket_domain_name, not regional)"
  value       = aws_s3_bucket.access_logs.bucket_domain_name
  # depends_on ensures CloudFront doesn't attempt to configure logging until
  # the bucket ACL and public-access-block are fully applied.
  depends_on = [
    aws_s3_bucket_acl.access_logs,
    aws_s3_bucket_public_access_block.access_logs,
  ]
}
