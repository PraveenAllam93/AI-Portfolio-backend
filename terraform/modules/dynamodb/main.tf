# =============================================================================
# DYNAMODB MODULE — three-table design
# =============================================================================
#
# main      — pipeline records: uploads, portfolio, dedup
#             PK: USER#{userId}  SK: UPLOAD#{id} | PORTFOLIO#current | CONTENT#{hash}
#             Billing: on-demand  PITR: prod only
#
# pii       — real PII values extracted before AI call
#             PK: USER#{userId}  SK: PII#latest
#             Separate KMS key, PITR always on, no public API touches this table.
#
# analytics — CloudFront view events; high-volume, TTL 90 days
#             PK: PORTFOLIO#{userId}  SK: VIEW#{ts}#{rand8}
#             Billing: on-demand  TTL: ttl attribute
#
# =============================================================================

# ---------------------------------------------------------------------------
# MAIN TABLE
# ---------------------------------------------------------------------------

resource "aws_dynamodb_table" "main" {
  name         = "${var.name_prefix}-main-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # GSI1: query uploads by pipeline status
  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.environment == "prod" ? true : false
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-main-table"
  })
}

# ---------------------------------------------------------------------------
# PII TABLE
# Customer-managed KMS key — rotated annually, independent of main table key.
# PITR always on (GDPR / CCPA right-to-erasure audit trail).
# Only portfolio-generator Lambda has GetItem; only ai-processing has PutItem.
# ---------------------------------------------------------------------------

resource "aws_kms_key" "pii" {
  description             = "CMK for ${var.name_prefix} PII DynamoDB table"
  deletion_window_in_days = 14
  enable_key_rotation     = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-pii-kms-key"
  })
}

resource "aws_kms_alias" "pii" {
  name          = "alias/${var.name_prefix}-pii"
  target_key_id = aws_kms_key.pii.key_id
}

resource "aws_dynamodb_table" "pii" {
  name         = "${var.name_prefix}-pii-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # PITR always on — required for GDPR right-to-erasure verification
  point_in_time_recovery {
    enabled = true
  }

  # Customer-managed key — separate from main table encryption
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.pii.arn
  }

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-pii-table"
    DataClass   = "PII"
    Sensitivity = "HIGH"
  })
}

# ---------------------------------------------------------------------------
# ANALYTICS TABLE
# High-volume CloudFront view events. TTL purges records after 90 days so
# storage stays bounded regardless of traffic volume.
# No GSI — all queries are by PK (PORTFOLIO#{userId}) only.
# ---------------------------------------------------------------------------

resource "aws_dynamodb_table" "analytics" {
  name         = "${var.name_prefix}-analytics-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # TTL attribute — set to epoch seconds (viewedAt + 90 days) at write time
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-analytics-table"
  })
}
