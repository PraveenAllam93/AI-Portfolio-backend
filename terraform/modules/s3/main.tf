# =============================================================================
# S3 BUCKETS MODULE
# =============================================================================
# Implements the quarantine-first upload pattern:
# - Quarantine: UNTRUSTED uploads land here first
# - Validated: Files promoted after passing security checks
# - Rejected: Failed validation files moved here
# - Portfolio: Generated portfolio websites
# =============================================================================

# Used to set the bucket owner in the access-logs ACL.
data "aws_canonical_user_id" "current" {}

# CloudFront's canonical user ID for log delivery. Using this explicit ID
# (instead of the "log-delivery-write" canned ACL) is the reliable approach
# for granting CloudFront standard logging access to an S3 bucket.
data "aws_cloudfront_log_delivery_canonical_user_id" "cloudfront" {}

# -----------------------------------------------------------------------------
# QUARANTINE BUCKET (UNTRUSTED)
# -----------------------------------------------------------------------------
# All user uploads land here first. Trust level: ZERO
# Files are validated by Lambda before promotion to validated bucket.

resource "aws_s3_bucket" "quarantine" {
  bucket = "${var.name_prefix}-resume-quarantine-${var.random_suffix}"

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-resume-quarantine"
    TrustLevel  = "UNTRUSTED"
    Purpose     = "Initial upload landing zone"
  })
}

resource "aws_s3_bucket_versioning" "quarantine" {
  bucket = aws_s3_bucket.quarantine.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "quarantine" {
  bucket = aws_s3_bucket.quarantine.id

  rule {
    id     = "expire-unprocessed-uploads"
    status = "Enabled"

    filter {}  # Apply to all objects in bucket

    expiration {
      days = var.lifecycle_expiration_days
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "quarantine" {
  bucket = aws_s3_bucket.quarantine.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "quarantine" {
  bucket = aws_s3_bucket.quarantine.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS for presigned URL uploads
resource "aws_s3_bucket_cors_configuration" "quarantine" {
  bucket = aws_s3_bucket.quarantine.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST"]
    allowed_origins = ["*"]  # Restrict in production
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# -----------------------------------------------------------------------------
# VALIDATED BUCKET (TRUSTED)
# -----------------------------------------------------------------------------
# Files that passed all security checks are promoted here.
# Only the validation Lambda can write to this bucket.

resource "aws_s3_bucket" "validated" {
  bucket = "${var.name_prefix}-resume-validated-${var.random_suffix}"

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-resume-validated"
    TrustLevel  = "TRUSTED"
    Purpose     = "Validated resumes ready for processing"
  })
}

resource "aws_s3_bucket_versioning" "validated" {
  bucket = aws_s3_bucket.validated.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "validated" {
  bucket = aws_s3_bucket.validated.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "validated" {
  bucket = aws_s3_bucket.validated.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# REJECTED BUCKET
# -----------------------------------------------------------------------------
# Files that failed validation are moved here for analysis/debugging.

resource "aws_s3_bucket" "rejected" {
  bucket = "${var.name_prefix}-resume-rejected-${var.random_suffix}"

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-resume-rejected"
    TrustLevel  = "REJECTED"
    Purpose     = "Failed validation files"
  })
}

resource "aws_s3_bucket_versioning" "rejected" {
  bucket = aws_s3_bucket.rejected.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "rejected" {
  bucket = aws_s3_bucket.rejected.id

  rule {
    id     = "expire-rejected-files"
    status = "Enabled"

    filter {}  # Apply to all objects in bucket

    expiration {
      days = var.lifecycle_expiration_days
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "rejected" {
  bucket = aws_s3_bucket.rejected.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "rejected" {
  bucket = aws_s3_bucket.rejected.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# PORTFOLIO BUCKET
# -----------------------------------------------------------------------------
# Generated portfolio websites. Served via CloudFront.

resource "aws_s3_bucket" "portfolio" {
  bucket = "${var.name_prefix}-portfolio-${var.random_suffix}"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-portfolio"
    Purpose = "Generated portfolio websites"
  })
}

resource "aws_s3_bucket_versioning" "portfolio" {
  bucket = aws_s3_bucket.portfolio.id
  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "portfolio" {
  bucket = aws_s3_bucket.portfolio.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "portfolio" {
  bucket = aws_s3_bucket.portfolio.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Website configuration for portfolio bucket
resource "aws_s3_bucket_website_configuration" "portfolio" {
  bucket = aws_s3_bucket.portfolio.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

# -----------------------------------------------------------------------------
# ACCESS LOGS BUCKET
# -----------------------------------------------------------------------------
# CloudFront writes compressed access log files here every ~5 minutes.
# A Lambda processes these files to extract portfolio view events.
#
# ACL note: CloudFront standard access logging uses the legacy ACL system.
# The bucket must have ACLs enabled (BucketOwnerPreferred) and be granted
# the "log-delivery-write" canned ACL so CloudFront's log delivery service
# can write objects. block_public_acls must be false to allow this non-public
# ACL to be set — log-delivery-write grants access only to AWS's internal
# LogDelivery group, NOT to the general public. The public bucket policy
# block (block_public_policy + restrict_public_buckets = true) still prevents
# any public HTTP access to the bucket.

resource "aws_s3_bucket" "access_logs" {
  bucket = "${var.name_prefix}-access-logs-${var.random_suffix}"

  tags = merge(var.tags, {
    Name    = "${var.name_prefix}-access-logs"
    Purpose = "CloudFront access logs for portfolio view tracking"
  })
}

# BucketOwnerPreferred is required to enable the log-delivery-write canned ACL.
resource "aws_s3_bucket_ownership_controls" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Grant CloudFront log delivery service FULL_CONTROL using its canonical user
# ID. This is more reliable than the "log-delivery-write" canned ACL because
# it explicitly identifies CloudFront's delivery account rather than relying
# on the legacy LogDelivery group mapping.
resource "aws_s3_bucket_acl" "access_logs" {
  depends_on = [aws_s3_bucket_ownership_controls.access_logs]
  bucket     = aws_s3_bucket.access_logs.id

  access_control_policy {
    grant {
      grantee {
        type = "CanonicalUser"
        id   = data.aws_cloudfront_log_delivery_canonical_user_id.cloudfront.id
      }
      permission = "FULL_CONTROL"
    }

    owner {
      id = data.aws_canonical_user_id.current.id
    }
  }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  depends_on = [aws_s3_bucket_acl.access_logs]
  bucket     = aws_s3_bucket.access_logs.id

  # false: required for the canonical-user ACL grant to function
  block_public_acls   = false
  ignore_public_acls  = false
  # true: no public bucket policy permitted — keeps HTTP access private
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Retain logs for 90 days — sufficient for trend analysis, then auto-expire.
resource "aws_s3_bucket_lifecycle_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    id     = "expire-access-logs"
    status = "Enabled"

    filter {}

    expiration {
      days = 90
    }
  }
}
