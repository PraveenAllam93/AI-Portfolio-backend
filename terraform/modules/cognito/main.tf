# =============================================================================
# COGNITO MODULE
# =============================================================================
# User authentication with AWS Cognito
# Issues JWTs for API Gateway authorization
# =============================================================================

# -----------------------------------------------------------------------------
# USER POOL
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool" "main" {
  name = "${var.name_prefix}-user-pool"

  # Username configuration
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Password policy
  password_policy {
    minimum_length                   = var.password_min_length
    require_uppercase                = var.password_require_uppercase
    require_lowercase                = var.password_require_lowercase
    require_numbers                  = var.password_require_numbers
    require_symbols                  = var.password_require_symbols
    temporary_password_validity_days = 7
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration (using Cognito default)
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Schema attributes
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 5
      max_length = 256
    }
  }

  schema {
    name                     = "name"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # User pool add-ons
  user_pool_add_ons {
    advanced_security_mode = var.environment == "prod" ? "ENFORCED" : "OFF"
  }

  # MFA configuration
  mfa_configuration = "OFF"  # Enable in production if needed

  # Verification message
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "AI Portfolio - Verify your email"
    email_message        = "Your verification code is {####}"
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-user-pool"
  })
}

# -----------------------------------------------------------------------------
# USER POOL CLIENT
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.name_prefix}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # Token validity
  access_token_validity  = 1   # 1 hour
  id_token_validity      = 1   # 1 hour
  refresh_token_validity = 30  # 30 days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Auth flows
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # OAuth settings (for hosted UI)
  supported_identity_providers = ["COGNITO"]

  # Prevent secret generation (for public clients like SPAs)
  generate_secret = false

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"

  # Read/write attributes
  read_attributes  = ["email", "name", "email_verified"]
  write_attributes = ["email", "name"]
}

# -----------------------------------------------------------------------------
# USER POOL DOMAIN
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.name_prefix}-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id
}
