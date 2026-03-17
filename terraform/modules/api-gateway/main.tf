# =============================================================================
# API GATEWAY MODULE
# =============================================================================
# REST API with Cognito JWT authorization
# Endpoints:
# - POST /upload/presigned-url - Get presigned URL for upload
# - GET /status/{uploadId} - Get processing status
# - GET /portfolio/{userId} - Get portfolio data
# =============================================================================

# -----------------------------------------------------------------------------
# REST API
# -----------------------------------------------------------------------------

resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.name_prefix}-api"
  description = "AI Portfolio API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api"
  })
}

# -----------------------------------------------------------------------------
# COGNITO AUTHORIZER
# -----------------------------------------------------------------------------

resource "aws_api_gateway_authorizer" "cognito" {
  name            = "${var.name_prefix}-cognito-authorizer"
  rest_api_id     = aws_api_gateway_rest_api.main.id
  type            = "COGNITO_USER_POOLS"
  identity_source = "method.request.header.Authorization"
  provider_arns   = [var.user_pool_arn]
}

# -----------------------------------------------------------------------------
# /upload RESOURCE
# -----------------------------------------------------------------------------

resource "aws_api_gateway_resource" "upload" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "upload"
}

# /upload/presigned-url
resource "aws_api_gateway_resource" "presigned_url" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.upload.id
  path_part   = "presigned-url"
}

# POST /upload/presigned-url
resource "aws_api_gateway_method" "post_presigned_url" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.presigned_url.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "post_presigned_url" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.presigned_url.id
  http_method             = aws_api_gateway_method.post_presigned_url.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.get_presigned_url_lambda_invoke_arn
}

# Lambda permission for presigned URL
resource "aws_lambda_permission" "api_presigned_url" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.get_presigned_url_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# -----------------------------------------------------------------------------
# /status RESOURCE
# -----------------------------------------------------------------------------

resource "aws_api_gateway_resource" "status" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "status"
}

# /status/{uploadId}
resource "aws_api_gateway_resource" "status_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.status.id
  path_part   = "{uploadId}"
}

# GET /status/{uploadId}
resource "aws_api_gateway_method" "get_status" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.status_id.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "get_status" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.status_id.id
  http_method             = aws_api_gateway_method.get_status.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.get_status_lambda_invoke_arn
}

# Lambda permission for status
resource "aws_lambda_permission" "api_get_status" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.get_status_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# -----------------------------------------------------------------------------
# /portfolio RESOURCE
# -----------------------------------------------------------------------------

resource "aws_api_gateway_resource" "portfolio" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "portfolio"
}

# /portfolio/{userId}
resource "aws_api_gateway_resource" "portfolio_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio.id
  path_part   = "{userId}"
}

# GET /portfolio/{userId}
resource "aws_api_gateway_method" "get_portfolio" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_id.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId" = true
  }
}

resource "aws_api_gateway_integration" "get_portfolio" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_id.id
  http_method             = aws_api_gateway_method.get_portfolio.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.get_portfolio_lambda_invoke_arn
}

# Lambda permission for portfolio
resource "aws_lambda_permission" "api_get_portfolio" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.get_portfolio_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# -----------------------------------------------------------------------------
# /portfolio/{userId}/analytics  — GET (Cognito auth, owner-only analytics)
# /portfolio/{userId}/content    — PATCH (Cognito auth, manual field edit)
# /portfolio/{userId}/ai-enhance — POST (Cognito auth, AI suggestion)
# -----------------------------------------------------------------------------

# /portfolio/{userId}/analytics
resource "aws_api_gateway_resource" "portfolio_analytics" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_id.id
  path_part   = "analytics"
}

resource "aws_api_gateway_method" "get_analytics" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_analytics.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId" = true
  }
}

resource "aws_api_gateway_integration" "get_analytics" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_analytics.id
  http_method             = aws_api_gateway_method.get_analytics.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.get_analytics_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_get_analytics" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.get_analytics_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# /portfolio/{userId}/content
resource "aws_api_gateway_resource" "portfolio_content" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_id.id
  path_part   = "content"
}

resource "aws_api_gateway_method" "patch_portfolio" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_content.id
  http_method   = "PATCH"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId" = true
  }
}

resource "aws_api_gateway_integration" "patch_portfolio" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_content.id
  http_method             = aws_api_gateway_method.patch_portfolio.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.patch_portfolio_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_patch_portfolio" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.patch_portfolio_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# /portfolio/{userId}/ai-enhance
resource "aws_api_gateway_resource" "portfolio_ai_enhance" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_id.id
  path_part   = "ai-enhance"
}

resource "aws_api_gateway_method" "ai_enhance_portfolio" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_ai_enhance.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId" = true
  }
}

resource "aws_api_gateway_integration" "ai_enhance_portfolio" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_ai_enhance.id
  http_method             = aws_api_gateway_method.ai_enhance_portfolio.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.ai_enhance_portfolio_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_ai_enhance_portfolio" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.ai_enhance_portfolio_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# -----------------------------------------------------------------------------
# /templates — GET (public, no Cognito auth)
# Returns the template catalog with metadata for the frontend picker.
# No auth: template list is public information, not user-specific data.
# -----------------------------------------------------------------------------

resource "aws_api_gateway_resource" "templates" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "templates"
}

resource "aws_api_gateway_method" "get_templates" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.templates.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_templates" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.templates.id
  http_method             = aws_api_gateway_method.get_templates.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.get_templates_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_get_templates" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.get_templates_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# -----------------------------------------------------------------------------
# CORS (OPTIONS methods)
# -----------------------------------------------------------------------------

# CORS for /upload/presigned-url
resource "aws_api_gateway_method" "options_presigned_url" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.presigned_url.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_presigned_url" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presigned_url.id
  http_method = aws_api_gateway_method.options_presigned_url.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_presigned_url" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presigned_url.id
  http_method = aws_api_gateway_method.options_presigned_url.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_presigned_url" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presigned_url.id
  http_method = aws_api_gateway_method.options_presigned_url.http_method
  status_code = aws_api_gateway_method_response.options_presigned_url.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# CORS for /portfolio/{userId}/analytics
resource "aws_api_gateway_method" "options_portfolio_analytics" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_analytics.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_portfolio_analytics" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_analytics.id
  http_method = aws_api_gateway_method.options_portfolio_analytics.http_method
  type        = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_portfolio_analytics" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_analytics.id
  http_method = aws_api_gateway_method.options_portfolio_analytics.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_portfolio_analytics" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_analytics.id
  http_method = aws_api_gateway_method.options_portfolio_analytics.http_method
  status_code = aws_api_gateway_method_response.options_portfolio_analytics.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# CORS for /portfolio/{userId}/content
resource "aws_api_gateway_method" "options_portfolio_content" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_content.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_portfolio_content" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_content.id
  http_method = aws_api_gateway_method.options_portfolio_content.http_method
  type        = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_portfolio_content" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_content.id
  http_method = aws_api_gateway_method.options_portfolio_content.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_portfolio_content" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_content.id
  http_method = aws_api_gateway_method.options_portfolio_content.http_method
  status_code = aws_api_gateway_method_response.options_portfolio_content.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,PATCH'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# CORS for /portfolio/{userId}/ai-enhance
resource "aws_api_gateway_method" "options_portfolio_ai_enhance" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_ai_enhance.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_portfolio_ai_enhance" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_ai_enhance.id
  http_method = aws_api_gateway_method.options_portfolio_ai_enhance.http_method
  type        = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_portfolio_ai_enhance" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_ai_enhance.id
  http_method = aws_api_gateway_method.options_portfolio_ai_enhance.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_portfolio_ai_enhance" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_ai_enhance.id
  http_method = aws_api_gateway_method.options_portfolio_ai_enhance.http_method
  status_code = aws_api_gateway_method_response.options_portfolio_ai_enhance.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# CORS for /templates (public endpoint — no Authorization header required)
resource "aws_api_gateway_method" "options_templates" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.templates.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_templates" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.templates.id
  http_method = aws_api_gateway_method.options_templates.http_method
  type        = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_templates" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.templates.id
  http_method = aws_api_gateway_method.options_templates.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_templates" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.templates.id
  http_method = aws_api_gateway_method.options_templates.http_method
  status_code = aws_api_gateway_method_response.options_templates.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# -----------------------------------------------------------------------------
# ACCESS LOGGING
# -----------------------------------------------------------------------------

# CloudWatch log group for API Gateway access logs
resource "aws_cloudwatch_log_group" "api_access_logs" {
  name              = "/aws/apigateway/${var.name_prefix}/access-logs"
  retention_in_days = 90

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-access-logs"
  })
}

# IAM role that allows API Gateway to write to CloudWatch Logs.
# This is an account-level setting — only one role is needed per account.
resource "aws_iam_role" "apigw_cloudwatch" {
  name = "${var.name_prefix}-apigw-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "apigateway.amazonaws.com" }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "apigw_cloudwatch" {
  role       = aws_iam_role.apigw_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# Register the CloudWatch role with the API Gateway account settings
resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.apigw_cloudwatch.arn
}

# -----------------------------------------------------------------------------
# DEPLOYMENT & STAGE
# -----------------------------------------------------------------------------

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.upload.id,
      aws_api_gateway_resource.presigned_url.id,
      aws_api_gateway_resource.status.id,
      aws_api_gateway_resource.status_id.id,
      aws_api_gateway_resource.portfolio.id,
      aws_api_gateway_resource.portfolio_id.id,
      aws_api_gateway_resource.portfolio_analytics.id,
      aws_api_gateway_resource.portfolio_content.id,
      aws_api_gateway_resource.portfolio_ai_enhance.id,
      aws_api_gateway_resource.templates.id,
      aws_api_gateway_method.post_presigned_url.id,
      aws_api_gateway_method.get_status.id,
      aws_api_gateway_method.get_portfolio.id,
      aws_api_gateway_method.get_analytics.id,
      aws_api_gateway_method.patch_portfolio.id,
      aws_api_gateway_method.ai_enhance_portfolio.id,
      aws_api_gateway_method.get_templates.id,
      aws_api_gateway_integration.post_presigned_url.id,
      aws_api_gateway_integration.get_status.id,
      aws_api_gateway_integration.get_portfolio.id,
      aws_api_gateway_integration.get_analytics.id,
      aws_api_gateway_integration.patch_portfolio.id,
      aws_api_gateway_integration.ai_enhance_portfolio.id,
      aws_api_gateway_integration.get_templates.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  # Access logging: every request is recorded with method, path, status,
  # latency, and the Cognito user ID — essential for audit and abuse detection.
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      cognitoUser    = "$context.authorizer.claims.sub"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
    })
  }

  depends_on = [aws_api_gateway_account.main]

  variables = {
    "environment" = var.environment
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-api-${var.environment}"
  })
}

# -----------------------------------------------------------------------------
# THROTTLING
# -----------------------------------------------------------------------------

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  method_path = "*/*"

  settings {
    throttling_rate_limit  = var.rate_limit
    throttling_burst_limit = var.burst_limit
    metrics_enabled        = true
    # ERROR logs auth failures and 5xx — INFO adds every request.
    # Use ERROR in prod to balance visibility vs. cost/noise.
    logging_level       = var.environment == "prod" ? "ERROR" : "INFO"
    data_trace_enabled  = var.environment != "prod"  # full req/resp in non-prod only
  }
}
