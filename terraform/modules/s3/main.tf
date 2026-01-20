# =============================================================================
# S3 BUCKETS MODULE
# =============================================================================
# Implements the quarantine-first upload pattern:
# - Quarantine: UNTRUSTED uploads land here first
# - Validated: Files promoted after passing security checks
# - Rejected: Failed validation files moved here
# - Portfolio: Generated portfolio websites
# =============================================================================

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
