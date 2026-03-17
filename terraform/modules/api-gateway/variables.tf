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

variable "get_templates_lambda_arn" {
  description = "ARN of the get templates Lambda"
  type        = string
}

variable "get_templates_lambda_invoke_arn" {
  description = "Invoke ARN of the get templates Lambda"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
