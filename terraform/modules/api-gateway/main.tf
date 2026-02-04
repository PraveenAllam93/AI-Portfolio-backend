# =============================================================================
# API GATEWAY MODULE
# =============================================================================
# REST API with Cognito JWT authorization
# Endpoints:
# - GET /user/info - Get user info from JWT token (ACTIVE)
# - POST /upload/presigned-url - Get presigned URL for upload (COMMENTED OUT)
# - GET /status/{uploadId} - Get processing status (COMMENTED OUT)
# - GET /portfolio/{userId} - Get portfolio data (COMMENTED OUT)
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
# /upload RESOURCE (COMMENTED OUT - NOT DEPLOYED)
# -----------------------------------------------------------------------------

# resource "aws_api_gateway_resource" "upload" {
#   rest_api_id = aws_api_gateway_rest_api.main.id
#   parent_id   = aws_api_gateway_rest_api.main.root_resource_id
#   path_part   = "upload"
# }

# # /upload/presigned-url
# resource "aws_api_gateway_resource" "presigned_url" {
#   rest_api_id = aws_api_gateway_rest_api.main.id
#   parent_id   = aws_api_gateway_resource.upload.id
#   path_part   = "presigned-url"
# }

# # POST /upload/presigned-url
# resource "aws_api_gateway_method" "post_presigned_url" {
#   rest_api_id   = aws_api_gateway_rest_api.main.id
#   resource_id   = aws_api_gateway_resource.presigned_url.id
#   http_method   = "POST"
#   authorization = "COGNITO_USER_POOLS"
#   authorizer_id = aws_api_gateway_authorizer.cognito.id
# }

# resource "aws_api_gateway_integration" "post_presigned_url" {
#   rest_api_id             = aws_api_gateway_rest_api.main.id
#   resource_id             = aws_api_gateway_resource.presigned_url.id
#   http_method             = aws_api_gateway_method.post_presigned_url.http_method
#   integration_http_method = "POST"
#   type                    = "AWS_PROXY"
#   uri                     = var.get_presigned_url_lambda_invoke_arn
# }

# # Lambda permission for presigned URL
# resource "aws_lambda_permission" "api_presigned_url" {
#   statement_id  = "AllowAPIGatewayInvoke"
#   action        = "lambda:InvokeFunction"
#   function_name = var.get_presigned_url_lambda_arn
#   principal     = "apigateway.amazonaws.com"
#   source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
# }

# -----------------------------------------------------------------------------
# /status RESOURCE (COMMENTED OUT - NOT DEPLOYED)
# -----------------------------------------------------------------------------

# resource "aws_api_gateway_resource" "status" {
#   rest_api_id = aws_api_gateway_rest_api.main.id
#   parent_id   = aws_api_gateway_rest_api.main.root_resource_id
#   path_part   = "status"
# }

# # /status/{uploadId}
# resource "aws_api_gateway_resource" "status_id" {
#   rest_api_id = aws_api_gateway_rest_api.main.id
#   parent_id   = aws_api_gateway_resource.status.id
#   path_part   = "{uploadId}"
# }

# # GET /status/{uploadId}
# resource "aws_api_gateway_method" "get_status" {
#   rest_api_id   = aws_api_gateway_rest_api.main.id
#   resource_id   = aws_api_gateway_resource.status_id.id
#   http_method   = "GET"
#   authorization = "COGNITO_USER_POOLS"
#   authorizer_id = aws_api_gateway_authorizer.cognito.id

#   request_parameters = {
#     "method.request.path.uploadId" = true
#   }
# }

# resource "aws_api_gateway_integration" "get_status" {
#   rest_api_id             = aws_api_gateway_rest_api.main.id
#   resource_id             = aws_api_gateway_resource.status_id.id
#   http_method             = aws_api_gateway_method.get_status.http_method
#   integration_http_method = "POST"
#   type                    = "AWS_PROXY"
#   uri                     = var.get_status_lambda_invoke_arn
# }

# # Lambda permission for status
# resource "aws_lambda_permission" "api_get_status" {
#   statement_id  = "AllowAPIGatewayInvoke"
#   action        = "lambda:InvokeFunction"
#   function_name = var.get_status_lambda_arn
#   principal     = "apigateway.amazonaws.com"
#   source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
# }

# -----------------------------------------------------------------------------
# /portfolio RESOURCE (COMMENTED OUT - NOT DEPLOYED)
# -----------------------------------------------------------------------------

# resource "aws_api_gateway_resource" "portfolio" {
#   rest_api_id = aws_api_gateway_rest_api.main.id
#   parent_id   = aws_api_gateway_rest_api.main.root_resource_id
#   path_part   = "portfolio"
# }

# # /portfolio/{userId}
# resource "aws_api_gateway_resource" "portfolio_id" {
#   rest_api_id = aws_api_gateway_rest_api.main.id
#   parent_id   = aws_api_gateway_resource.portfolio.id
#   path_part   = "{userId}"
# }

# # GET /portfolio/{userId}
# resource "aws_api_gateway_method" "get_portfolio" {
#   rest_api_id   = aws_api_gateway_rest_api.main.id
#   resource_id   = aws_api_gateway_resource.portfolio_id.id
#   http_method   = "GET"
#   authorization = "COGNITO_USER_POOLS"
#   authorizer_id = aws_api_gateway_authorizer.cognito.id

#   request_parameters = {
#     "method.request.path.userId" = true
#   }
# }

# resource "aws_api_gateway_integration" "get_portfolio" {
#   rest_api_id             = aws_api_gateway_rest_api.main.id
#   resource_id             = aws_api_gateway_resource.portfolio_id.id
#   http_method             = aws_api_gateway_method.get_portfolio.http_method
#   integration_http_method = "POST"
#   type                    = "AWS_PROXY"
#   uri                     = var.get_portfolio_lambda_invoke_arn
# }

# # Lambda permission for portfolio
# resource "aws_lambda_permission" "api_get_portfolio" {
#   statement_id  = "AllowAPIGatewayInvoke"
#   action        = "lambda:InvokeFunction"
#   function_name = var.get_portfolio_lambda_arn
#   principal     = "apigateway.amazonaws.com"
#   source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
# }

# -----------------------------------------------------------------------------
# /user RESOURCE (NEW - ACTIVE)
# -----------------------------------------------------------------------------

resource "aws_api_gateway_resource" "user" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "user"
}

# /user/info
resource "aws_api_gateway_resource" "user_info" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.user.id
  path_part   = "info"
}

# GET /user/info - Returns name and email from JWT token
resource "aws_api_gateway_method" "get_user_info" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.user_info.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_user_info" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.user_info.id
  http_method             = aws_api_gateway_method.get_user_info.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = var.get_user_info_lambda_invoke_arn
}

# Lambda permission for user info
resource "aws_lambda_permission" "api_get_user_info" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.get_user_info_lambda_arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# -----------------------------------------------------------------------------
# CORS (OPTIONS methods)
# -----------------------------------------------------------------------------

# CORS for /upload/presigned-url (COMMENTED OUT - NOT DEPLOYED)
# resource "aws_api_gateway_method" "options_presigned_url" {
#   rest_api_id   = aws_api_gateway_rest_api.main.id
#   resource_id   = aws_api_gateway_resource.presigned_url.id
#   http_method   = "OPTIONS"
#   authorization = "NONE"
# }

# resource "aws_api_gateway_integration" "options_presigned_url" {
#   rest_api_id = aws_api_gateway_rest_api.main.id
#   resource_id = aws_api_gateway_resource.presigned_url.id
#   http_method = aws_api_gateway_method.options_presigned_url.http_method
#   type        = "MOCK"

#   request_templates = {
#     "application/json" = "{\"statusCode\": 200}"
#   }
# }

# resource "aws_api_gateway_method_response" "options_presigned_url" {
#   rest_api_id = aws_api_gateway_rest_api.main.id
#   resource_id = aws_api_gateway_resource.presigned_url.id
#   http_method = aws_api_gateway_method.options_presigned_url.http_method
#   status_code = "200"

#   response_parameters = {
#     "method.response.header.Access-Control-Allow-Headers" = true
#     "method.response.header.Access-Control-Allow-Methods" = true
#     "method.response.header.Access-Control-Allow-Origin"  = true
#   }
# }

# resource "aws_api_gateway_integration_response" "options_presigned_url" {
#   rest_api_id = aws_api_gateway_rest_api.main.id
#   resource_id = aws_api_gateway_resource.presigned_url.id
#   http_method = aws_api_gateway_method.options_presigned_url.http_method
#   status_code = aws_api_gateway_method_response.options_presigned_url.status_code

#   response_parameters = {
#     "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
#     "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT'"
#     "method.response.header.Access-Control-Allow-Origin"  = "'*'"
#   }
# }

# CORS for /user/info (NEW - ACTIVE)
resource "aws_api_gateway_method" "options_user_info" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.user_info.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_user_info" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.user_info.id
  http_method = aws_api_gateway_method.options_user_info.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_user_info" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.user_info.id
  http_method = aws_api_gateway_method.options_user_info.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "options_user_info" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.user_info.id
  http_method = aws_api_gateway_method.options_user_info.http_method
  status_code = aws_api_gateway_method_response.options_user_info.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# -----------------------------------------------------------------------------
# DEPLOYMENT & STAGE
# -----------------------------------------------------------------------------

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      # OLD ROUTES (COMMENTED OUT - NOT DEPLOYED)
      # aws_api_gateway_resource.upload.id,
      # aws_api_gateway_resource.presigned_url.id,
      # aws_api_gateway_resource.status.id,
      # aws_api_gateway_resource.status_id.id,
      # aws_api_gateway_resource.portfolio.id,
      # aws_api_gateway_resource.portfolio_id.id,
      # aws_api_gateway_method.post_presigned_url.id,
      # aws_api_gateway_method.get_status.id,
      # aws_api_gateway_method.get_portfolio.id,
      # aws_api_gateway_integration.post_presigned_url.id,
      # aws_api_gateway_integration.get_status.id,
      # aws_api_gateway_integration.get_portfolio.id,

      # NEW ROUTE (ACTIVE)
      aws_api_gateway_resource.user.id,
      aws_api_gateway_resource.user_info.id,
      aws_api_gateway_method.get_user_info.id,
      aws_api_gateway_integration.get_user_info.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.get_user_info,
    aws_api_gateway_integration.options_user_info
  ]
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  # Throttling
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
    logging_level          = "OFF"  # Requires account-level CloudWatch role setup
  }
}
