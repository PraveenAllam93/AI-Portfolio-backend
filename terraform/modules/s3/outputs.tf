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
