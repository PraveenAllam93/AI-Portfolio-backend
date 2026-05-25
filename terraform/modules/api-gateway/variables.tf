variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "rate_limit" {
  description = "API rate limit (requests per second)"
  type        = number
  default     = 10
}

variable "burst_limit" {
  description = "API burst limit"
  type        = number
  default     = 20
}

# Cognito
variable "user_pool_arn" {
  description = "ARN of the Cognito user pool"
  type        = string
}

# Lambda functions
variable "get_presigned_url_lambda_arn" {
  description = "ARN of the get presigned URL Lambda"
  type        = string
}

variable "get_presigned_url_lambda_invoke_arn" {
  description = "Invoke ARN of the get presigned URL Lambda"
  type        = string
}

variable "get_portfolio_lambda_arn" {
  description = "ARN of the get portfolio Lambda"
  type        = string
}

variable "get_portfolio_lambda_invoke_arn" {
  description = "Invoke ARN of the get portfolio Lambda"
  type        = string
}

variable "get_status_lambda_arn" {
  description = "ARN of the get status Lambda"
  type        = string
}

variable "get_status_lambda_invoke_arn" {
  description = "Invoke ARN of the get status Lambda"
  type        = string
}

variable "get_analytics_lambda_arn" {
  description = "ARN of the get analytics Lambda"
  type        = string
}

variable "get_analytics_lambda_invoke_arn" {
  description = "Invoke ARN of the get analytics Lambda"
  type        = string
}

variable "patch_portfolio_lambda_arn" {
  description = "ARN of the patch portfolio Lambda"
  type        = string
}

variable "patch_portfolio_lambda_invoke_arn" {
  description = "Invoke ARN of the patch portfolio Lambda"
  type        = string
}

variable "ai_enhance_portfolio_lambda_arn" {
  description = "ARN of the AI enhance portfolio Lambda"
  type        = string
}

variable "ai_enhance_portfolio_lambda_invoke_arn" {
  description = "Invoke ARN of the AI enhance portfolio Lambda"
  type        = string
}

variable "add_custom_section_lambda_arn" {
  description = "ARN of the add custom section Lambda"
  type        = string
}

variable "add_custom_section_lambda_invoke_arn" {
  description = "Invoke ARN of the add custom section Lambda"
  type        = string
}

variable "interview_start_lambda_arn" {
  description = "ARN of the interview start Lambda"
  type        = string
}
variable "interview_start_lambda_invoke_arn" {
  description = "Invoke ARN of the interview start Lambda"
  type        = string
}
variable "interview_answer_lambda_arn" {
  description = "ARN of the interview answer Lambda"
  type        = string
}
variable "interview_answer_lambda_invoke_arn" {
  description = "Invoke ARN of the interview answer Lambda"
  type        = string
}
variable "interview_exit_lambda_arn" {
  description = "ARN of the interview exit Lambda"
  type        = string
}
variable "interview_exit_lambda_invoke_arn" {
  description = "Invoke ARN of the interview exit Lambda"
  type        = string
}
variable "interview_report_lambda_arn" {
  description = "ARN of the interview report Lambda"
  type        = string
}
variable "interview_report_lambda_invoke_arn" {
  description = "Invoke ARN of the interview report Lambda"
  type        = string
}
variable "interview_sessions_lambda_arn" {
  description = "ARN of the interview sessions list Lambda"
  type        = string
}
variable "interview_sessions_lambda_invoke_arn" {
  description = "Invoke ARN of the interview sessions list Lambda"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "publish_portfolio_lambda_arn" {
  description = "ARN of the publish portfolio Lambda"
  type        = string
}

variable "publish_portfolio_lambda_invoke_arn" {
  description = "Invoke ARN of the publish portfolio Lambda"
  type        = string
}

variable "get_image_upload_url_lambda_arn" {
  description = "ARN of the get image upload URL Lambda"
  type        = string
}

variable "get_image_upload_url_lambda_invoke_arn" {
  description = "Invoke ARN of the get image upload URL Lambda"
  type        = string
}

variable "generate_project_image_lambda_arn" {
  description = "ARN of the generate project image Lambda"
  type        = string
}

variable "generate_project_image_lambda_invoke_arn" {
  description = "Invoke ARN of the generate project image Lambda"
  type        = string
}

variable "cancel_upload_lambda_arn" {
  description = "ARN of the cancel upload Lambda"
  type        = string
}
variable "cancel_upload_lambda_invoke_arn" {
  description = "Invoke ARN of the cancel upload Lambda"
  type        = string
}

variable "list_versions_lambda_arn" {
  description = "ARN of the list versions Lambda"
  type        = string
}
variable "list_versions_lambda_invoke_arn" {
  description = "Invoke ARN of the list versions Lambda"
  type        = string
}

variable "activate_version_lambda_arn" {
  description = "ARN of the activate version Lambda"
  type        = string
}
variable "activate_version_lambda_invoke_arn" {
  description = "Invoke ARN of the activate version Lambda"
  type        = string
}

variable "delete_version_lambda_arn" {
  description = "ARN of the delete version Lambda"
  type        = string
}
variable "delete_version_lambda_invoke_arn" {
  description = "Invoke ARN of the delete version Lambda"
  type        = string
}

variable "list_portfolios_lambda_arn" {
  description = "ARN of the list portfolios Lambda"
  type        = string
}
variable "list_portfolios_lambda_invoke_arn" {
  description = "Invoke ARN of the list portfolios Lambda"
  type        = string
}

variable "delete_portfolio_lambda_arn" {
  description = "ARN of the delete portfolio Lambda"
  type        = string
}
variable "delete_portfolio_lambda_invoke_arn" {
  description = "Invoke ARN of the delete portfolio Lambda"
  type        = string
}

variable "toggle_portfolio_live_lambda_arn" {
  description = "ARN of the toggle portfolio live Lambda"
  type        = string
}
variable "toggle_portfolio_live_lambda_invoke_arn" {
  description = "Invoke ARN of the toggle portfolio live Lambda"
  type        = string
}
