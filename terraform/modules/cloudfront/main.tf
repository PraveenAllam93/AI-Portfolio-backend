# =============================================================================
# CLOUDFRONT MODULE
# =============================================================================
# CDN for serving generated portfolio websites
# Origin: Portfolio S3 bucket
# =============================================================================

terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws, aws.us_east_1]
    }
  }
}

# -----------------------------------------------------------------------------
# ORIGIN ACCESS CONTROL
# -----------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_control" "portfolio" {
  name                              = "${var.name_prefix}-portfolio-oac"
  description                       = "OAC for portfolio S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# -----------------------------------------------------------------------------
# CLOUDFRONT DISTRIBUTION
# -----------------------------------------------------------------------------

resource "aws_cloudfront_distribution" "portfolio" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.name_prefix} Portfolio CDN"
  default_root_object = "index.html"
  price_class         = "PriceClass_200"  # Excludes South America and Australia

  # Standard access logging: CloudFront writes gzip log files to the dedicated
  # access-logs S3 bucket every ~5 minutes. The process_access_logs Lambda
  # reads these files to extract portfolio view events.
  logging_config {
    bucket          = var.access_logs_bucket_domain
    include_cookies = false
    prefix          = "cloudfront/"
  }

  # Origin: Portfolio S3 bucket
  origin {
    domain_name              = var.portfolio_bucket_domain
    origin_id                = "S3-${var.portfolio_bucket_id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.portfolio.id
  }

  # Default cache behavior
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${var.portfolio_bucket_id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600     # 1 hour
    max_ttl                = 86400    # 24 hours
    compress               = true
  }

  # Custom error responses
  custom_error_response {
    error_code         = 403
    response_code      = 404
    response_page_path = "/error.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/error.html"
  }

  # Restrictions
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # SSL certificate (default CloudFront certificate)
  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-portfolio-cdn"
  })
}

# -----------------------------------------------------------------------------
# S3 BUCKET POLICY (allow CloudFront access)
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "portfolio_bucket_policy" {
  statement {
    sid    = "AllowCloudFrontServicePrincipal"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions   = ["s3:GetObject"]
    resources = ["${var.portfolio_bucket_arn}/*"]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.portfolio.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "portfolio" {
  bucket = var.portfolio_bucket_id
  policy = data.aws_iam_policy_document.portfolio_bucket_policy.json
}
