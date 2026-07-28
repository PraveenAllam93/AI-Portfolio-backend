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

  # The public handle. Stored on the STANDARD preferred_username attribute
  # rather than a custom one for two reasons:
  #   1. standard attributes are searchable through ListUsers, which is how the
  #      web app resolves a username to an account at login time (custom
  #      attributes cannot be filtered on)
  #   2. it lands on the ID token automatically, so building a portfolio URL
  #      needs no extra lookup
  # Uniqueness is NOT enforced by Cognito here — the pre_sign_up trigger claims
  # the handle with a conditional DynamoDB write, which is the authority.
  schema {
    name                     = "preferred_username"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 3
      max_length = 30
    }
  }

  # Claims the chosen username atomically with account creation. Raising in
  # this trigger aborts the sign-up, so an account can never exist without a
  # username and two accounts can never share one.
  dynamic "lambda_config" {
    for_each = var.pre_signup_lambda_arn == "" ? [] : [1]
    content {
      pre_sign_up = var.pre_signup_lambda_arn
    }
  }

  # User pool add-ons
  user_pool_add_ons {
    advanced_security_mode = var.environment == "prod" ? "ENFORCED" : "OFF"
  }

  # MFA configuration
  # OPTIONAL lets users choose to enable TOTP MFA; ENFORCED mandates it.
  # OFF in dev/staging — prod exposes TOTP as an option for users.
  # The software_token_mfa_configuration block must NOT be present when
  # mfa_configuration = "OFF" — Cognito rejects that combination.
  mfa_configuration = var.environment == "prod" ? "OPTIONAL" : "OFF"

  dynamic "software_token_mfa_configuration" {
    for_each = var.environment == "prod" ? [1] : []
    content {
      enabled = true
    }
  }

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
  access_token_validity  = 1  # 1 hour
  id_token_validity      = 1  # 1 hour
  refresh_token_validity = 30 # 30 days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Auth flows
  # ALLOW_USER_PASSWORD_AUTH is intentionally excluded: it sends the password
  # to the server in plaintext rather than using SRP (Secure Remote Password),
  # which means the password is exposed to the auth endpoint.
  # SRP proves knowledge of the password without transmitting it.
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  # OAuth settings (for hosted UI)
  supported_identity_providers = ["COGNITO"]

  # Prevent secret generation (for public clients like SPAs)
  generate_secret = false

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"

  # Read/write attributes
  # preferred_username must be writable for SignUp to carry the chosen handle,
  # and readable so it appears as a claim on the ID token.
  read_attributes  = ["email", "name", "email_verified", "preferred_username"]
  write_attributes = ["email", "name", "preferred_username"]
}

# -----------------------------------------------------------------------------
# USER POOL DOMAIN
# -----------------------------------------------------------------------------

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.name_prefix}-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id
}
