"""
Lambda: Portfolio Generator
Generates static HTML/CSS portfolio website from parsed resume data.
Outputs to S3 portfolio bucket for CloudFront delivery.

Security notes:
  - parsedData in DynamoDB uses PII tokens ({{NAME}}, {{EMAIL}}, etc.)
    instead of real contact details. _get_pii() reads the dedicated
    PII#latest item and _unmask_pii() substitutes tokens at render time.
    SSN is always suppressed — never rendered in the portfolio HTML.
  - ALL user-supplied strings are html.escaped before any template sees them
    (_extract_vars() in templates/base.py). Prevents stored XSS regardless of
    what OpenAI returns or what was in the resume text.
  - Link URLs validated to http/https only (javascript: injection prevention)
  - CSP header added to every template: script-src 'none'
  - Arbitrary fields from AI output are never treated as raw HTML

Templates:
  Each template lives in templates/{name}.py and exposes:
    html(v: dict) -> str   — renders full HTML page
    css()         -> str   — returns stylesheet string
  v is a pre-escaped dict produced by templates.base._extract_vars().
  Adding a new template = add a .py file + register in VALID_TEMPLATE_IDS.
"""

import importlib
import json
import os
import re
import uuid
import boto3
from datetime import datetime, timezone

from templates.base import _extract_vars

s3_client = boto3.client('s3')
cloudfront_client = boto3.client('cloudfront')
dynamodb = boto3.resource('dynamodb')

PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
MAIN_TABLE = os.environ.get('MAIN_TABLE')
PII_TABLE = os.environ.get('PII_TABLE')
CLOUDFRONT_DISTRIBUTION_ID = os.environ.get('CLOUDFRONT_DISTRIBUTION_ID', '')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Keep in sync with upload/handler.py and auth/patch_portfolio.py
VALID_TEMPLATE_IDS = frozenset({
    'modern', 'minimal', 'bold', 'creative', 'executive',
    'nebula', 'aurora', 'luxury',
})
DEFAULT_TEMPLATE = 'modern'

# Only allow http and https schemes in user-supplied URLs
_ALLOWED_URL_RE = re.compile(r'^https?://', re.IGNORECASE)

# PII tokens and the pii_map key they correspond to.
# NAME is not masked — portfolio is public-facing; name is intentional.
# SSN maps to None — stored for compliance but never rendered.
_TOKEN_FIELD = {
    '{{EMAIL}}':        'email',
    '{{PHONE}}':        'phone',
    '{{LINKEDIN_URL}}': 'linkedin_url',
    '{{GITHUB_URL}}':   'github_url',
    '{{SSN}}':          None,   # suppressed
}


# ---------------------------------------------------------------------------
# Structured logger — outputs JSON, captured by CloudWatch Logs
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    entry = {
        "level": level,
        "function": "portfolio_generator",
        "message": message,
    }
    entry.update(kwargs)
    print(json.dumps(entry))


def _log_info(message: str, **kwargs) -> None:
    _log("INFO", message, **kwargs)


def _log_error(message: str, **kwargs) -> None:
    _log("ERROR", message, **kwargs)


# ---------------------------------------------------------------------------
# PII helpers
# ---------------------------------------------------------------------------


def _get_pii(user_id: str) -> dict:
    """
    Read real PII values from the dedicated DynamoDB PII#latest item.
    Returns an empty dict if not found (e.g. uploads pre-dating PII masking).
    """
    table = dynamodb.Table(PII_TABLE)
    resp = table.get_item(
        Key={
            'PK': f'USER#{user_id}',
            'SK': 'PII#latest',
        }
    )
    return resp.get('Item', {})


def _unmask_pii(data: dict, pii: dict) -> dict:
    """
    Recursively substitute {{TOKEN}} placeholders in a parsed-data dict
    with real values from pii. SSN tokens are replaced with '' (suppressed).
    Unknown tokens are left as-is so accidental content is not erased.
    """
    if not pii:
        return data

    def _sub(value: str) -> str:
        for token, field in _TOKEN_FIELD.items():
            if token in value:
                real = pii.get(field, '') if field else ''
                value = value.replace(token, real)
        return value

    result = {}
    for k, v in data.items():
        if isinstance(v, str):
            result[k] = _sub(v)
        elif isinstance(v, dict):
            result[k] = _unmask_pii(v, pii)
        elif isinstance(v, list):
            result[k] = [
                _unmask_pii(i, pii) if isinstance(i, dict)
                else (_sub(i) if isinstance(i, str) else i)
                for i in v
            ]
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    """Generate static portfolio website."""
    correlation_id = context.aws_request_id if context else 'local'
    user_id = None
    try:
        user_id = event.get('userId')
        upload_id = event.get('uploadId')

        if not user_id:
            if 'Records' in event:
                record = event['Records'][0]
                if record.get('eventName') in ['INSERT', 'MODIFY']:
                    keys = record['dynamodb']['Keys']
                    user_id = keys['PK']['S'].replace('USER#', '')
            else:
                return {'statusCode': 400, 'body': 'Missing userId'}

        _log_info(
            "Portfolio generation started",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
        )

        table = dynamodb.Table(MAIN_TABLE)
        response = table.get_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PORTFOLIO#current',
            }
        )

        if 'Item' not in response:
            _log_error(
                "Portfolio data not found",
                correlationId=correlation_id,
                userId=user_id,
            )
            return {'statusCode': 404, 'body': 'Portfolio data not found'}

        item = response['Item']
        parsed_data = item.get('parsedData', {})
        portfolio_content = item.get('portfolioContent', {})
        content_hash = item.get('contentHash', '')

        # Resolve templateId — default to 'modern' if missing or invalid
        template_id = item.get('templateId', DEFAULT_TEMPLATE)
        if template_id not in VALID_TEMPLATE_IDS:
            _log_info(
                "Unknown templateId — falling back to default",
                correlationId=correlation_id,
                userId=user_id,
                templateId=template_id,
                default=DEFAULT_TEMPLATE,
            )
            template_id = DEFAULT_TEMPLATE

        # Unmask PII tokens — substitutes {{NAME}}, {{EMAIL}}, etc. with
        # the real values stored in PII#latest. SSN is always suppressed.
        pii = _get_pii(user_id)
        parsed_data = _unmask_pii(parsed_data, pii)

        # Extract and escape all user data into a safe dict for templates
        template_vars = _extract_vars(parsed_data, portfolio_content)

        # Load and render the selected template module
        mod = importlib.import_module(f'templates.{template_id}')
        portfolio_html = mod.html(template_vars)
        css = mod.css()

        version = item.get('version', 1)
        base_path = f"{user_id}/v{version}"

        s3_client.put_object(
            Bucket=PORTFOLIO_BUCKET,
            Key=f"{base_path}/index.html",
            Body=portfolio_html.encode('utf-8'),
            ContentType='text/html',
            # no-store: browsers never cache the HTML locally.
            # CloudFront uses its own TTL but gets invalidated below on every publish.
            CacheControl='no-store',
        )

        s3_client.put_object(
            Bucket=PORTFOLIO_BUCKET,
            Key=f"{base_path}/styles.css",
            Body=css.encode('utf-8'),
            ContentType='text/css',
            CacheControl='max-age=86400',
        )

        # Invalidate CloudFront so edge caches immediately serve the new files.
        # Skip gracefully if the distribution ID is not configured (local/test).
        if CLOUDFRONT_DISTRIBUTION_ID:
            try:
                cloudfront_client.create_invalidation(
                    DistributionId=CLOUDFRONT_DISTRIBUTION_ID,
                    InvalidationBatch={
                        'Paths': {
                            'Quantity': 1,
                            'Items': [f'/{base_path}/*'],
                        },
                        'CallerReference': str(uuid.uuid4()),
                    },
                )
                _log_info(
                    "CloudFront cache invalidated",
                    correlationId=correlation_id,
                    userId=user_id,
                    path=base_path,
                )
            except Exception as cf_err:
                # Non-fatal: log and continue. Portfolio is already in S3;
                # users will see fresh content once the CF TTL expires.
                _log_error(
                    "CloudFront invalidation failed",
                    correlationId=correlation_id,
                    userId=user_id,
                    error=str(cf_err),
                )
        else:
            _log_info(
                "CLOUDFRONT_DISTRIBUTION_ID not set — skipping invalidation",
                correlationId=correlation_id,
                userId=user_id,
            )

        now = datetime.now(timezone.utc).isoformat()

        table.update_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PORTFOLIO#current',
            },
            UpdateExpression=(
                'SET #status = :status, portfolioPath = :path, '
                'updatedAt = :updatedAt'
            ),
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'PUBLISHED',
                ':path': base_path,
                ':updatedAt': now,
            },
        )

        if upload_id:
            table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'UPLOAD#{upload_id}',
                },
                UpdateExpression=(
                    'SET #status = :status, portfolioPath = :path, '
                    'updatedAt = :updatedAt'
                ),
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'COMPLETE',
                    ':path': base_path,
                    ':updatedAt': now,
                },
            )

        # Back-fill portfolioPath in the dedup record so future identical
        # uploads can short-circuit directly to the published portfolio.
        if content_hash:
            table.update_item(
                Key={
                    'PK': f'USER#{user_id}',
                    'SK': f'CONTENT#{content_hash}',
                },
                UpdateExpression='SET portfolioPath = :path',
                ExpressionAttributeValues={':path': base_path},
            )

        _log_info(
            "Portfolio published",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
            portfolioPath=base_path,
            templateId=template_id,
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'path': base_path, 'status': 'PUBLISHED'}),
        }

    except Exception as e:
        _log_error(
            "Portfolio generation error",
            correlationId=correlation_id,
            userId=user_id,
            error=str(e),
        )
        raise
