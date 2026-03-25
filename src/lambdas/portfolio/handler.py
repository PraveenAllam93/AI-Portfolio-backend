"""
Lambda: Portfolio Generator
Generates static HTML/CSS portfolio website from parsed resume data.
Outputs to S3 portfolio bucket for CloudFront delivery.

Security notes:
  - All user-supplied strings are HTML-escaped before injection (XSS prevention)
  - Link URLs validated to http/https only (javascript: injection prevention)
  - Content-Security-Policy header added to generated pages (script-src 'none')
  - Arbitrary fields from AI output are never treated as raw HTML
"""

import json
import os
import boto3
from datetime import datetime, timezone

from templates import minimal, modern, bold, creative, aurora, executive, luxury, nebula
from templates.base import normalize, DEFAULT_SECTION_ORDER

s3_client = boto3.client('s3')
cf_client = boto3.client('cloudfront')
dynamodb = boto3.resource('dynamodb')

PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
CLOUDFRONT_DISTRIBUTION_ID = os.environ.get('CLOUDFRONT_DISTRIBUTION_ID')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

_TEMPLATES = {
    'minimal':   minimal,
    'modern':    modern,
    'bold':      bold,
    'creative':  creative,
    'aurora':    aurora,
    'executive': executive,
    'luxury':    luxury,
    'nebula':    nebula,
}
_DEFAULT_TEMPLATE = 'minimal'

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


def lambda_handler(event, context):
    """Generate static portfolio website."""
    correlation_id = context.aws_request_id if context else 'local'
    user_id = None
    upload_id = None
    try:
        # Can be triggered by direct Lambda invocation or DynamoDB Stream
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

        # Get portfolio data from DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
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
        category = item.get('category', 'software_engineer')
        template_id = item.get('templateId', _DEFAULT_TEMPLATE)
        section_order = item.get('sectionOrder') or DEFAULT_SECTION_ORDER
        hidden_sections = item.get('hiddenSections') or []

        # target='draft'   → write to {userId}/draft/ (no DynamoDB status update)
        # target='publish' → write to {userId}/v{n}/ (updates DynamoDB status)
        target = event.get('target', 'publish')

        # Normalize data and dispatch to the chosen template module
        tmpl = _TEMPLATES.get(template_id, minimal)
        v = normalize(parsed_data, portfolio_content, category, section_order, hidden_sections)
        portfolio_html = tmpl.html(v)
        css = tmpl.css()

        # Determine S3 output path based on target
        if target == 'draft':
            base_path = f"{user_id}/draft"
        else:
            version = item.get('version', 1)
            base_path = f"{user_id}/v{version}"

        s3_client.put_object(
            Bucket=PORTFOLIO_BUCKET,
            Key=f"{base_path}/index.html",
            Body=portfolio_html.encode('utf-8'),
            ContentType='text/html',
            CacheControl='no-cache, no-store, must-revalidate',
        )

        s3_client.put_object(
            Bucket=PORTFOLIO_BUCKET,
            Key=f"{base_path}/styles.css",
            Body=css.encode('utf-8'),
            ContentType='text/css',
            CacheControl='no-cache, no-store, must-revalidate',
        )

        # Only update DynamoDB status for publish (not draft)
        now = datetime.now(timezone.utc).isoformat()
        if target != 'draft':
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

        # Invalidate CloudFront cache so the new template is served immediately.
        # Scoped to this user's path only — no other user's portfolio is affected.
        if CLOUDFRONT_DISTRIBUTION_ID:
            try:
                cf_client.create_invalidation(
                    DistributionId=CLOUDFRONT_DISTRIBUTION_ID,
                    InvalidationBatch={
                        'Paths': {
                            'Quantity': 1,
                            'Items': [f'/{user_id}/*'],
                        },
                        'CallerReference': correlation_id,
                    },
                )
                _log_info(
                    "CloudFront cache invalidated",
                    correlationId=correlation_id,
                    userId=user_id,
                    path=f'/{user_id}/*',
                )
            except Exception as cf_err:
                # Non-fatal: portfolio is already written to S3.
                # Cache will expire naturally; log for visibility.
                _log_error(
                    "CloudFront invalidation failed (non-fatal)",
                    correlationId=correlation_id,
                    userId=user_id,
                    error=str(cf_err),
                )

        _log_info(
            "Portfolio published",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
            portfolioPath=base_path,
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
            uploadId=upload_id,
            error=str(e),
        )
        # Mark the upload as FAILED so the frontend stops polling.
        # Without this, the upload record stays at GENERATING forever since
        # this Lambda was invoked async and can never bubble errors to the caller.
        if user_id and upload_id:
            try:
                table = dynamodb.Table(DYNAMODB_TABLE)
                table.update_item(
                    Key={
                        'PK': f'USER#{user_id}',
                        'SK': f'UPLOAD#{upload_id}',
                    },
                    UpdateExpression='SET #status = :status, #updatedAt = :updatedAt',
                    ExpressionAttributeNames={
                        '#status': 'status',
                        '#updatedAt': 'updatedAt',
                    },
                    ExpressionAttributeValues={
                        ':status': 'FAILED',
                        ':updatedAt': datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as db_err:
                _log_error(
                    "Failed to mark upload as FAILED",
                    correlationId=correlation_id,
                    userId=user_id,
                    uploadId=upload_id,
                    error=str(db_err),
                )
        raise


