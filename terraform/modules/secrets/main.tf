# =============================================================================
# SECRETS MANAGER MODULE
# =============================================================================
# Manages sensitive configuration like OpenAI API keys
# =============================================================================

resource "aws_secretsmanager_secret" "openai_api_key" {
  name        = "${var.name_prefix}-openai-api-key"
  description = "OpenAI API key for AI processing Lambda"

  recovery_window_in_days = 7  # Allow 7 days to recover if accidentally deleted

  tags = var.tags
}

# Placeholder for secret version - actual value set manually via AWS CLI
# To set the value after deployment:
# aws secretsmanager put-secret-value \
#   --secret-id <secret-name> \
#   --secret-string '{"OPENAI_API_KEY":"sk-..."}'

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  secret_id = aws_secretsmanager_secret.openai_api_key.id

  # This is a placeholder - you MUST update this with the real key via AWS CLI
  # after initial deployment, or use a lifecycle ignore to manage it outside Terraform
  secret_string = jsonencode({
    OPENAI_API_KEY = "PLACEHOLDER_UPDATE_VIA_AWS_CLI"
  })

  lifecycle {
    ignore_changes = [secret_string]  # Prevent Terraform from overwriting manual updates
  }
}
