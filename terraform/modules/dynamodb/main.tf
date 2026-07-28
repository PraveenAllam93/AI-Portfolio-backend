# =============================================================================
# DYNAMODB MODULE
# =============================================================================
# Single-table design for AI Portfolio
# PK: USER#{userId}
# SK: ENTITY#{entityId}
# =============================================================================

resource "aws_dynamodb_table" "main" {
  name         = "${var.name_prefix}-main-table"
  billing_mode = "PAY_PER_REQUEST" # On-demand for unpredictable workloads
  hash_key     = "PK"
  range_key    = "SK"

  # Primary key attributes
  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  # GSI for querying by status (e.g., all PENDING resumes)
  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  # GSI1: Query by status
  global_secondary_index {
    name            = "GSI1"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup of temporary data
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery
  point_in_time_recovery {
    enabled = var.environment == "prod" ? true : false
  }

  # Server-side encryption
  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-main-table"
  })
}
