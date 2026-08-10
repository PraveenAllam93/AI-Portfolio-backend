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

# DELETE /status/{uploadId} — cancel an in-flight upload
resource "aws_api_gateway_method" "delete_status" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.status_id.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "delete_status" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.status_id.id
  http_method             = aws_api_gateway_method.delete_status.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.cancel_upload_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_cancel_upload" {
  statement_id  = "AllowAPIGatewayInvokeCancel"
  action        = "lambda:InvokeFunction"
  function_name = var.cancel_upload_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# /status/{uploadId}/start-generation
resource "aws_api_gateway_resource" "start_generation" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.status_id.id
  path_part   = "start-generation"
}

# POST /status/{uploadId}/start-generation — resume pipeline after selection
resource "aws_api_gateway_method" "post_start_generation" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.start_generation.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "post_start_generation" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.start_generation.id
  http_method             = aws_api_gateway_method.post_start_generation.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.start_generation_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_start_generation" {
  statement_id  = "AllowAPIGatewayInvokeStartGeneration"
  action        = "lambda:InvokeFunction"
  function_name = var.start_generation_lambda_arn
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

# GET /portfolio/{userId} → list all portfolios for user
resource "aws_api_gateway_method" "list_portfolios" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_id.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId" = true
  }
}

resource "aws_api_gateway_integration" "list_portfolios" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_id.id
  http_method             = aws_api_gateway_method.list_portfolios.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.list_portfolios_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_list_portfolios" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.list_portfolios_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# CORS for /portfolio/{userId}
resource "aws_api_gateway_method" "options_portfolio_id" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_portfolio_id" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_id.id
  http_method       = aws_api_gateway_method.options_portfolio_id.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_portfolio_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_id.id
  http_method = aws_api_gateway_method.options_portfolio_id.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_portfolio_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_id.id
  http_method = aws_api_gateway_method.options_portfolio_id.http_method
  status_code = aws_api_gateway_method_response.options_portfolio_id.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# /portfolio/{userId}/{uploadId}
resource "aws_api_gateway_resource" "portfolio_upload_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_id.id
  path_part   = "{uploadId}"
}

# GET /portfolio/{userId}/{uploadId} → get single portfolio
resource "aws_api_gateway_method" "get_portfolio" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_upload_id.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "get_portfolio" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_upload_id.id
  http_method             = aws_api_gateway_method.get_portfolio.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.get_portfolio_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_get_portfolio" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.get_portfolio_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# DELETE /portfolio/{userId}/{uploadId} → delete entire portfolio
resource "aws_api_gateway_method" "delete_portfolio" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_upload_id.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "delete_portfolio" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_upload_id.id
  http_method             = aws_api_gateway_method.delete_portfolio.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.delete_portfolio_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_delete_portfolio" {
  statement_id  = "AllowAPIGatewayInvokeDelete"
  action        = "lambda:InvokeFunction"
  function_name = var.delete_portfolio_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# CORS for /portfolio/{userId}/{uploadId}
resource "aws_api_gateway_method" "options_portfolio_upload_id" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_upload_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_portfolio_upload_id" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_upload_id.id
  http_method       = aws_api_gateway_method.options_portfolio_upload_id.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_portfolio_upload_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_upload_id.id
  http_method = aws_api_gateway_method.options_portfolio_upload_id.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_portfolio_upload_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_upload_id.id
  http_method = aws_api_gateway_method.options_portfolio_upload_id.http_method
  status_code = aws_api_gateway_method_response.options_portfolio_upload_id.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# -----------------------------------------------------------------------------
# /portfolio/{userId}/analytics  — GET (Cognito auth, owner-only analytics)
# /portfolio/{userId}/content    — PATCH (Cognito auth, manual field edit)
# /portfolio/{userId}/ai-enhance — POST (Cognito auth, AI suggestion)
# -----------------------------------------------------------------------------

# /portfolio/{userId}/{uploadId}/analytics
resource "aws_api_gateway_resource" "portfolio_analytics" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_upload_id.id
  path_part   = "analytics"
}

resource "aws_api_gateway_method" "get_analytics" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_analytics.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
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

# /portfolio/{userId}/{uploadId}/content
resource "aws_api_gateway_resource" "portfolio_content" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_upload_id.id
  path_part   = "content"
}

resource "aws_api_gateway_method" "patch_portfolio" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_content.id
  http_method   = "PATCH"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
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

# /portfolio/{userId}/{uploadId}/ai-enhance
resource "aws_api_gateway_resource" "portfolio_ai_enhance" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_upload_id.id
  path_part   = "ai-enhance"
}

resource "aws_api_gateway_method" "ai_enhance_portfolio" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_ai_enhance.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
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
# /portfolio/{userId}/versions  — GET (list), and nested version actions
# -----------------------------------------------------------------------------

resource "aws_api_gateway_resource" "portfolio_versions" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_upload_id.id
  path_part   = "versions"
}

# GET /portfolio/{userId}/{uploadId}/versions
resource "aws_api_gateway_method" "get_portfolio_versions" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_versions.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "get_portfolio_versions" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_versions.id
  http_method             = aws_api_gateway_method.get_portfolio_versions.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.list_versions_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_list_versions" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.list_versions_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# /portfolio/{userId}/versions/{versionId}
resource "aws_api_gateway_resource" "portfolio_version_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_versions.id
  path_part   = "{versionId}"
}

# DELETE /portfolio/{userId}/{uploadId}/versions/{versionId}
resource "aws_api_gateway_method" "delete_portfolio_version" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_version_id.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"    = true
    "method.request.path.uploadId"  = true
    "method.request.path.versionId" = true
  }
}

resource "aws_api_gateway_integration" "delete_portfolio_version" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_version_id.id
  http_method             = aws_api_gateway_method.delete_portfolio_version.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.delete_version_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_delete_version" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.delete_version_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# /portfolio/{userId}/versions/{versionId}/activate
resource "aws_api_gateway_resource" "portfolio_version_activate" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_version_id.id
  path_part   = "activate"
}

# POST /portfolio/{userId}/{uploadId}/versions/{versionId}/activate
resource "aws_api_gateway_method" "post_activate_version" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_version_activate.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"    = true
    "method.request.path.uploadId"  = true
    "method.request.path.versionId" = true
  }
}

resource "aws_api_gateway_integration" "post_activate_version" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_version_activate.id
  http_method             = aws_api_gateway_method.post_activate_version.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.activate_version_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_activate_version" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.activate_version_lambda_arn
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
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_analytics.id
  http_method       = aws_api_gateway_method.options_portfolio_analytics.http_method
  type              = "MOCK"
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
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_content.id
  http_method       = aws_api_gateway_method.options_portfolio_content.http_method
  type              = "MOCK"
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
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_ai_enhance.id
  http_method       = aws_api_gateway_method.options_portfolio_ai_enhance.http_method
  type              = "MOCK"
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

# /portfolio/{userId}/{uploadId}/custom-section — POST (Cognito auth, AI classifier)
resource "aws_api_gateway_resource" "portfolio_custom_section" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_upload_id.id
  path_part   = "custom-section"
}

resource "aws_api_gateway_method" "add_custom_section" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_custom_section.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "add_custom_section" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_custom_section.id
  http_method             = aws_api_gateway_method.add_custom_section.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.add_custom_section_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_add_custom_section" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.add_custom_section_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# CORS for /portfolio/{userId}/custom-section
resource "aws_api_gateway_method" "options_portfolio_custom_section" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_custom_section.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_portfolio_custom_section" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_custom_section.id
  http_method       = aws_api_gateway_method.options_portfolio_custom_section.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_portfolio_custom_section" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_custom_section.id
  http_method = aws_api_gateway_method.options_portfolio_custom_section.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_portfolio_custom_section" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_custom_section.id
  http_method = aws_api_gateway_method.options_portfolio_custom_section.http_method
  status_code = aws_api_gateway_method_response.options_portfolio_custom_section.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# -----------------------------------------------------------------------------
# /portfolio/{userId}/{uploadId}/publish — POST (Cognito auth, publish draft to live)
# -----------------------------------------------------------------------------

resource "aws_api_gateway_resource" "portfolio_publish" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_upload_id.id
  path_part   = "publish"
}

resource "aws_api_gateway_method" "post_publish_portfolio" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_publish.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "post_publish_portfolio" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_publish.id
  http_method             = aws_api_gateway_method.post_publish_portfolio.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.publish_portfolio_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_publish_portfolio" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.publish_portfolio_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_publish_portfolio" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_publish.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_publish_portfolio" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_publish.id
  http_method       = aws_api_gateway_method.options_publish_portfolio.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_publish_portfolio" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_publish.id
  http_method = aws_api_gateway_method.options_publish_portfolio.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_publish_portfolio" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_publish.id
  http_method = aws_api_gateway_method.options_publish_portfolio.http_method
  status_code = aws_api_gateway_method_response.options_publish_portfolio.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# -----------------------------------------------------------------------------
# /portfolio/{userId}/{uploadId}/image-upload-url — POST
# -----------------------------------------------------------------------------

resource "aws_api_gateway_resource" "portfolio_image_upload_url" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_upload_id.id
  path_part   = "image-upload-url"
}

resource "aws_api_gateway_method" "post_image_upload_url" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_image_upload_url.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "post_image_upload_url" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_image_upload_url.id
  http_method             = aws_api_gateway_method.post_image_upload_url.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.get_image_upload_url_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_get_image_upload_url" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.get_image_upload_url_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_portfolio_image_upload_url" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_image_upload_url.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_portfolio_image_upload_url" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_image_upload_url.id
  http_method       = aws_api_gateway_method.options_portfolio_image_upload_url.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_portfolio_image_upload_url" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_image_upload_url.id
  http_method = aws_api_gateway_method.options_portfolio_image_upload_url.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_portfolio_image_upload_url" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_image_upload_url.id
  http_method = aws_api_gateway_method.options_portfolio_image_upload_url.http_method
  status_code = aws_api_gateway_method_response.options_portfolio_image_upload_url.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# =============================================================================
# /portfolio/{userId}/{uploadId}/project-image/generate — POST (DALL-E 3 image generation)
# =============================================================================

resource "aws_api_gateway_resource" "portfolio_project_image" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_upload_id.id
  path_part   = "project-image"
}

resource "aws_api_gateway_resource" "portfolio_project_image_generate" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_project_image.id
  path_part   = "generate"
}

resource "aws_api_gateway_method" "post_project_image_generate" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_project_image_generate.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "post_project_image_generate" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_project_image_generate.id
  http_method             = aws_api_gateway_method.post_project_image_generate.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.generate_project_image_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_generate_project_image" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.generate_project_image_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_portfolio_project_image_generate" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_project_image_generate.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_portfolio_project_image_generate" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_project_image_generate.id
  http_method       = aws_api_gateway_method.options_portfolio_project_image_generate.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_portfolio_project_image_generate" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_project_image_generate.id
  http_method = aws_api_gateway_method.options_portfolio_project_image_generate.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_portfolio_project_image_generate" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_project_image_generate.id
  http_method = aws_api_gateway_method.options_portfolio_project_image_generate.http_method
  status_code = aws_api_gateway_method_response.options_portfolio_project_image_generate.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# =============================================================================
# /portfolio/{userId}/{uploadId}/toggle-live — POST
# =============================================================================

resource "aws_api_gateway_resource" "portfolio_toggle_live" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_upload_id.id
  path_part   = "toggle-live"
}

resource "aws_api_gateway_method" "post_toggle_live" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_toggle_live.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"   = true
    "method.request.path.uploadId" = true
  }
}

resource "aws_api_gateway_integration" "post_toggle_live" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_toggle_live.id
  http_method             = aws_api_gateway_method.post_toggle_live.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.toggle_portfolio_live_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_toggle_portfolio_live" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.toggle_portfolio_live_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_portfolio_toggle_live" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_toggle_live.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_portfolio_toggle_live" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_toggle_live.id
  http_method       = aws_api_gateway_method.options_portfolio_toggle_live.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_portfolio_toggle_live" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_toggle_live.id
  http_method = aws_api_gateway_method.options_portfolio_toggle_live.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_portfolio_toggle_live" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_toggle_live.id
  http_method = aws_api_gateway_method.options_portfolio_toggle_live.http_method
  status_code = aws_api_gateway_method_response.options_portfolio_toggle_live.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# =============================================================================
# /portfolio/{userId}/{uploadId}/preview — GET (owner-only presigned S3 URL)
# =============================================================================

resource "aws_api_gateway_resource" "portfolio_preview" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.portfolio_upload_id.id
  path_part   = "preview"
}

resource "aws_api_gateway_method" "get_portfolio_preview_url" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_preview.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.userId"           = true
    "method.request.path.uploadId"         = true
    "method.request.querystring.versionId" = true
  }
}

resource "aws_api_gateway_integration" "get_portfolio_preview_url" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.portfolio_preview.id
  http_method             = aws_api_gateway_method.get_portfolio_preview_url.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.get_portfolio_preview_url_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_get_portfolio_preview_url" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.get_portfolio_preview_url_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_portfolio_preview" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.portfolio_preview.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_portfolio_preview" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.portfolio_preview.id
  http_method       = aws_api_gateway_method.options_portfolio_preview.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_portfolio_preview" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_preview.id
  http_method = aws_api_gateway_method.options_portfolio_preview.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_portfolio_preview" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.portfolio_preview.id
  http_method = aws_api_gateway_method.options_portfolio_preview.http_method
  status_code = aws_api_gateway_method_response.options_portfolio_preview.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# =============================================================================
# INTERVIEW AGENT ROUTES
# POST /interview/start
# POST /interview/answer
# POST /interview/exit
# GET  /interview/{sessionId}/report
# =============================================================================

resource "aws_api_gateway_resource" "interview" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "interview"
}

# /interview/start
resource "aws_api_gateway_resource" "interview_start" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.interview.id
  path_part   = "start"
}

resource "aws_api_gateway_method" "post_interview_start" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interview_start.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "post_interview_start" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.interview_start.id
  http_method             = aws_api_gateway_method.post_interview_start.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.interview_start_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_interview_start" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.interview_start_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_interview_start" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interview_start.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_interview_start" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.interview_start.id
  http_method       = aws_api_gateway_method.options_interview_start.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_interview_start" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.interview_start.id
  http_method = aws_api_gateway_method.options_interview_start.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_interview_start" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.interview_start.id
  http_method = aws_api_gateway_method.options_interview_start.http_method
  status_code = aws_api_gateway_method_response.options_interview_start.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# /interview/answer
resource "aws_api_gateway_resource" "interview_answer" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.interview.id
  path_part   = "answer"
}

resource "aws_api_gateway_method" "post_interview_answer" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interview_answer.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "post_interview_answer" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.interview_answer.id
  http_method             = aws_api_gateway_method.post_interview_answer.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.interview_answer_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_interview_answer" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.interview_answer_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_interview_answer" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interview_answer.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_interview_answer" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.interview_answer.id
  http_method       = aws_api_gateway_method.options_interview_answer.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_interview_answer" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.interview_answer.id
  http_method = aws_api_gateway_method.options_interview_answer.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_interview_answer" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.interview_answer.id
  http_method = aws_api_gateway_method.options_interview_answer.http_method
  status_code = aws_api_gateway_method_response.options_interview_answer.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# /interview/exit
resource "aws_api_gateway_resource" "interview_exit" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.interview.id
  path_part   = "exit"
}

resource "aws_api_gateway_method" "post_interview_exit" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interview_exit.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "post_interview_exit" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.interview_exit.id
  http_method             = aws_api_gateway_method.post_interview_exit.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.interview_exit_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_interview_exit" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.interview_exit_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_interview_exit" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interview_exit.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_interview_exit" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.interview_exit.id
  http_method       = aws_api_gateway_method.options_interview_exit.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_interview_exit" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.interview_exit.id
  http_method = aws_api_gateway_method.options_interview_exit.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_interview_exit" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.interview_exit.id
  http_method = aws_api_gateway_method.options_interview_exit.http_method
  status_code = aws_api_gateway_method_response.options_interview_exit.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# /interview/{sessionId}
resource "aws_api_gateway_resource" "interview_session_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.interview.id
  path_part   = "{sessionId}"
}

# /interview/{sessionId}/report
resource "aws_api_gateway_resource" "interview_report" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.interview_session_id.id
  path_part   = "report"
}

resource "aws_api_gateway_method" "get_interview_report" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interview_report.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_interview_report" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.interview_report.id
  http_method             = aws_api_gateway_method.get_interview_report.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.interview_report_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_interview_report" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.interview_report_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_interview_report" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interview_report.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_interview_report" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.interview_report.id
  http_method       = aws_api_gateway_method.options_interview_report.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_interview_report" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.interview_report.id
  http_method = aws_api_gateway_method.options_interview_report.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_interview_report" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.interview_report.id
  http_method = aws_api_gateway_method.options_interview_report.http_method
  status_code = aws_api_gateway_method_response.options_interview_report.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,GET'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# /interview/sessions
resource "aws_api_gateway_resource" "interview_sessions" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.interview.id
  path_part   = "sessions"
}

resource "aws_api_gateway_method" "get_interview_sessions" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interview_sessions.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_interview_sessions" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.interview_sessions.id
  http_method             = aws_api_gateway_method.get_interview_sessions.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.interview_sessions_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_interview_sessions" {
  statement_id  = "AllowAPIGatewayInvokeInterviewSessions"
  action        = "lambda:InvokeFunction"
  function_name = var.interview_sessions_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_interview_sessions" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interview_sessions.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_interview_sessions" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.interview_sessions.id
  http_method       = aws_api_gateway_method.options_interview_sessions.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_interview_sessions" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.interview_sessions.id
  http_method = aws_api_gateway_method.options_interview_sessions.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_interview_sessions" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.interview_sessions.id
  http_method = aws_api_gateway_method.options_interview_sessions.http_method
  status_code = aws_api_gateway_method_response.options_interview_sessions.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,GET'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# =============================================================================
# GUEST CLAIM ROUTE
# POST /guest/claim — Cognito-authenticated (the newly-created real user).
# Migrates an anonymous guest's portfolio onto the real account and publishes.
# =============================================================================

resource "aws_api_gateway_resource" "guest" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "guest"
}

resource "aws_api_gateway_resource" "guest_claim" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.guest.id
  path_part   = "claim"
}

resource "aws_api_gateway_method" "post_guest_claim" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.guest_claim.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "post_guest_claim" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.guest_claim.id
  http_method             = aws_api_gateway_method.post_guest_claim.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.claim_guest_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_guest_claim" {
  statement_id  = "AllowAPIGatewayInvokeGuestClaim"
  action        = "lambda:InvokeFunction"
  function_name = var.claim_guest_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_guest_claim" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.guest_claim.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_guest_claim" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.guest_claim.id
  http_method       = aws_api_gateway_method.options_guest_claim.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_guest_claim" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.guest_claim.id
  http_method = aws_api_gateway_method.options_guest_claim.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_guest_claim" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.guest_claim.id
  http_method = aws_api_gateway_method.options_guest_claim.http_method
  status_code = aws_api_gateway_method_response.options_guest_claim.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST'"
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
      aws_api_gateway_resource.portfolio_upload_id.id,
      aws_api_gateway_resource.portfolio_analytics.id,
      aws_api_gateway_resource.portfolio_content.id,
      aws_api_gateway_resource.portfolio_ai_enhance.id,
      aws_api_gateway_resource.portfolio_publish.id,
      aws_api_gateway_resource.portfolio_image_upload_url.id,
      aws_api_gateway_resource.portfolio_project_image.id,
      aws_api_gateway_resource.portfolio_project_image_generate.id,
      aws_api_gateway_resource.portfolio_toggle_live.id,
      aws_api_gateway_resource.interview.id,
      aws_api_gateway_resource.interview_start.id,
      aws_api_gateway_resource.interview_answer.id,
      aws_api_gateway_resource.interview_exit.id,
      aws_api_gateway_resource.interview_session_id.id,
      aws_api_gateway_resource.interview_report.id,
      aws_api_gateway_resource.interview_sessions.id,
      aws_api_gateway_resource.username.id,
      aws_api_gateway_resource.username_check.id,
      aws_api_gateway_resource.profile.id,
      aws_api_gateway_resource.entitlements.id,
      aws_api_gateway_method.get_username_check.id,
      aws_api_gateway_method.get_profile.id,
      aws_api_gateway_method.patch_profile.id,
      aws_api_gateway_method.get_entitlements.id,
      aws_api_gateway_integration.get_entitlements.id,
      aws_api_gateway_method.post_presigned_url.id,
      aws_api_gateway_method.get_status.id,
      aws_api_gateway_method.list_portfolios.id,
      aws_api_gateway_method.get_portfolio.id,
      aws_api_gateway_method.delete_portfolio.id,
      aws_api_gateway_method.get_analytics.id,
      aws_api_gateway_method.patch_portfolio.id,
      aws_api_gateway_method.ai_enhance_portfolio.id,
      aws_api_gateway_method.post_toggle_live.id,
      aws_api_gateway_integration.post_presigned_url.id,
      aws_api_gateway_integration.get_status.id,
      aws_api_gateway_integration.list_portfolios.id,
      aws_api_gateway_integration.get_portfolio.id,
      aws_api_gateway_integration.delete_portfolio.id,
      aws_api_gateway_integration.get_analytics.id,
      aws_api_gateway_integration.patch_portfolio.id,
      aws_api_gateway_integration.ai_enhance_portfolio.id,
      aws_api_gateway_integration.post_toggle_live.id,
      aws_api_gateway_method.post_publish_portfolio.id,
      aws_api_gateway_integration.post_publish_portfolio.id,
      aws_api_gateway_method.post_image_upload_url.id,
      aws_api_gateway_integration.post_image_upload_url.id,
      aws_api_gateway_method.post_project_image_generate.id,
      aws_api_gateway_integration.post_project_image_generate.id,
      aws_api_gateway_method.post_interview_start.id,
      aws_api_gateway_method.post_interview_answer.id,
      aws_api_gateway_method.post_interview_exit.id,
      aws_api_gateway_method.get_interview_report.id,
      aws_api_gateway_method.get_interview_sessions.id,
      aws_api_gateway_integration.post_interview_start.id,
      aws_api_gateway_integration.post_interview_answer.id,
      aws_api_gateway_integration.post_interview_exit.id,
      aws_api_gateway_integration.get_interview_report.id,
      aws_api_gateway_integration.get_interview_sessions.id,
      aws_api_gateway_resource.portfolio_custom_section.id,
      aws_api_gateway_method.add_custom_section.id,
      aws_api_gateway_integration.add_custom_section.id,
      aws_api_gateway_resource.portfolio_preview.id,
      aws_api_gateway_method.get_portfolio_preview_url.id,
      aws_api_gateway_integration.get_portfolio_preview_url.id,
      aws_api_gateway_resource.start_generation.id,
      aws_api_gateway_method.post_start_generation.id,
      aws_api_gateway_integration.post_start_generation.id,
      aws_api_gateway_resource.guest.id,
      aws_api_gateway_resource.guest_claim.id,
      aws_api_gateway_method.post_guest_claim.id,
      aws_api_gateway_integration.post_guest_claim.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
  # Every integration must exist before the stage is deployed. Without this,
  # a from-scratch build races: `triggers` only creates implicit dependencies
  # on resources and methods, so CreateDeployment can fire while integrations
  # are still being created and fails with "No integration defined for method".
  depends_on = [
    aws_api_gateway_integration.post_presigned_url,
    aws_api_gateway_integration.get_status,
    aws_api_gateway_integration.delete_status,
    aws_api_gateway_integration.post_start_generation,
    aws_api_gateway_integration.list_portfolios,
    aws_api_gateway_integration.options_portfolio_id,
    aws_api_gateway_integration.get_portfolio,
    aws_api_gateway_integration.delete_portfolio,
    aws_api_gateway_integration.options_portfolio_upload_id,
    aws_api_gateway_integration.get_analytics,
    aws_api_gateway_integration.patch_portfolio,
    aws_api_gateway_integration.ai_enhance_portfolio,
    aws_api_gateway_integration.get_portfolio_versions,
    aws_api_gateway_integration.delete_portfolio_version,
    aws_api_gateway_integration.post_activate_version,
    aws_api_gateway_integration.options_presigned_url,
    aws_api_gateway_integration.options_portfolio_analytics,
    aws_api_gateway_integration.options_portfolio_content,
    aws_api_gateway_integration.options_portfolio_ai_enhance,
    aws_api_gateway_integration.add_custom_section,
    aws_api_gateway_integration.options_portfolio_custom_section,
    aws_api_gateway_integration.post_publish_portfolio,
    aws_api_gateway_integration.options_publish_portfolio,
    aws_api_gateway_integration.post_image_upload_url,
    aws_api_gateway_integration.options_portfolio_image_upload_url,
    aws_api_gateway_integration.post_project_image_generate,
    aws_api_gateway_integration.options_portfolio_project_image_generate,
    aws_api_gateway_integration.post_toggle_live,
    aws_api_gateway_integration.options_portfolio_toggle_live,
    aws_api_gateway_integration.get_portfolio_preview_url,
    aws_api_gateway_integration.options_portfolio_preview,
    aws_api_gateway_integration.post_interview_start,
    aws_api_gateway_integration.options_interview_start,
    aws_api_gateway_integration.post_interview_answer,
    aws_api_gateway_integration.options_interview_answer,
    aws_api_gateway_integration.post_interview_exit,
    aws_api_gateway_integration.options_interview_exit,
    aws_api_gateway_integration.get_interview_report,
    aws_api_gateway_integration.options_interview_report,
    aws_api_gateway_integration.get_interview_sessions,
    aws_api_gateway_integration.options_interview_sessions,
    aws_api_gateway_integration.post_guest_claim,
    aws_api_gateway_integration.options_guest_claim,
    aws_api_gateway_integration.get_username_check,
    aws_api_gateway_integration.options_username_check,
    aws_api_gateway_integration.get_profile,
    aws_api_gateway_integration.patch_profile,
    aws_api_gateway_integration.options_profile,
    aws_api_gateway_integration.get_entitlements,
    aws_api_gateway_integration.options_entitlements,
  ]

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
    logging_level      = var.environment == "prod" ? "ERROR" : "INFO"
    data_trace_enabled = var.environment != "prod" # full req/resp in non-prod only
  }
}

# =============================================================================
# /username/check — PUBLIC (no authorizer)
# =============================================================================
# The caller has no account yet, so this cannot be behind the Cognito
# authorizer. It exposes only whether a public handle is taken — the same thing
# a portfolio URL already reveals. Stage-level throttling caps scraping.
# =============================================================================

resource "aws_api_gateway_resource" "username" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "username"
}

resource "aws_api_gateway_resource" "username_check" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.username.id
  path_part   = "check"
}

resource "aws_api_gateway_method" "get_username_check" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.username_check.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.querystring.username" = true
  }
}

resource "aws_api_gateway_integration" "get_username_check" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.username_check.id
  http_method             = aws_api_gateway_method.get_username_check.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.check_username_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_check_username" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.check_username_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_username_check" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.username_check.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_username_check" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.username_check.id
  http_method       = aws_api_gateway_method.options_username_check.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_username_check" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.username_check.id
  http_method = aws_api_gateway_method.options_username_check.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_username_check" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.username_check.id
  http_method = aws_api_gateway_method.options_username_check.http_method
  status_code = aws_api_gateway_method_response.options_username_check.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# =============================================================================
# /profile — GET and PATCH (Cognito authenticated)
# =============================================================================
# No userId in the path: the Lambda derives the caller from the token's sub
# claim, so there is nothing to tamper with and no ownership check to get wrong.
# =============================================================================

resource "aws_api_gateway_resource" "profile" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "profile"
}

resource "aws_api_gateway_method" "get_profile" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.profile.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_profile" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.profile.id
  http_method             = aws_api_gateway_method.get_profile.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.profile_lambda_invoke_arn
}

resource "aws_api_gateway_method" "patch_profile" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.profile.id
  http_method   = "PATCH"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "patch_profile" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.profile.id
  http_method             = aws_api_gateway_method.patch_profile.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.profile_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_profile" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.profile_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_profile" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.profile.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_profile" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.profile.id
  http_method       = aws_api_gateway_method.options_profile.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_profile" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.profile.id
  http_method = aws_api_gateway_method.options_profile.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_profile" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.profile.id
  http_method = aws_api_gateway_method.options_profile.http_method
  status_code = aws_api_gateway_method_response.options_profile.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,PATCH,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# =============================================================================
# /entitlements — GET (Cognito authenticated)
# =============================================================================
# Reports the caller's plan limits and today's usage so the UI can render locks
# and credit counters. Like /profile there is no userId in the path: the Lambda
# reads the token's sub claim, so a caller can only ever see their own.
# =============================================================================

resource "aws_api_gateway_resource" "entitlements" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "entitlements"
}

resource "aws_api_gateway_method" "get_entitlements" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.entitlements.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_entitlements" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.entitlements.id
  http_method             = aws_api_gateway_method.get_entitlements.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.get_entitlements_lambda_invoke_arn
}

resource "aws_lambda_permission" "api_entitlements" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.get_entitlements_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "options_entitlements" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.entitlements.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_entitlements" {
  rest_api_id       = aws_api_gateway_rest_api.main.id
  resource_id       = aws_api_gateway_resource.entitlements.id
  http_method       = aws_api_gateway_method.options_entitlements.http_method
  type              = "MOCK"
  request_templates = { "application/json" = "{\"statusCode\": 200}" }
}

resource "aws_api_gateway_method_response" "options_entitlements" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.entitlements.id
  http_method = aws_api_gateway_method.options_entitlements.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_entitlements" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.entitlements.id
  http_method = aws_api_gateway_method.options_entitlements.http_method
  status_code = aws_api_gateway_method_response.options_entitlements.status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}
