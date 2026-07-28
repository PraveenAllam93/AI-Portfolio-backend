"""
Lambda: Toggle Portfolio Live

POST /portfolio/{userId}/{uploadId}/toggle-live
Body: { "isLive": true | false }

Sets the isLive flag on a portfolio. Multiple portfolios can be live simultaneously.
"""

import json
import os
import boto3
from datetime import datetime, timezone
from urllib.parse import unquote

import username_utils as uu

dynamodb = boto3.resource('dynamodb')
cf_client = boto3.client('cloudfront')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
CLOUDFRONT_DISTRIBUTION_ID = os.environ.get('CLOUDFRONT_DISTRIBUTION_ID', '')


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "toggle_portfolio_live", "message": message, **kwargs}))


def _response(status: int, body: dict) -> dict:
    allowed_origin = os.environ.get('ALLOWED_ORIGIN', '*')
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': allowed_origin,
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body),
    }


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    path_params = event.get('pathParameters') or {}
    path_user_id = unquote(path_params.get('userId', ''))
    upload_id = unquote(path_params.get('uploadId', ''))
    token_sub = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )

    if not path_user_id or path_user_id != token_sub:
        return _response(403, {'error': 'Forbidden'})

    if not upload_id:
        return _response(400, {'error': 'Missing uploadId'})

    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, ValueError):
        return _response(400, {'error': 'Invalid JSON body'})

    is_live = body.get('isLive')
    if not isinstance(is_live, bool):
        return _response(400, {'error': '"isLive" must be a boolean'})

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)

        # Verify portfolio exists. portfolioNumber comes along for the ride so
        # the cache invalidation below can target /u/{username}/{n}.
        result = table.get_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': f'PORTFOLIO#{upload_id}'},
            ProjectionExpression='uploadId, portfolioNumber',
        )
        if 'Item' not in result:
            return _response(404, {'error': 'Portfolio not found'})

        raw_number = result['Item'].get('portfolioNumber')
        portfolio_number = int(raw_number) if raw_number is not None else None

        table.update_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': f'PORTFOLIO#{upload_id}'},
            UpdateExpression='SET isLive = :live, updatedAt = :now',
            ExpressionAttributeValues={
                ':live': is_live,
                ':now': datetime.now(timezone.utc).isoformat(),
            },
        )

        # Invalidate CDN cache so Lambda@Edge re-checks access on next request.
        # Taking a portfolio offline MUST purge the viewer-facing /u/ paths, or
        # the edge keeps serving a portfolio the owner has just unpublished.
        if CLOUDFRONT_DISTRIBUTION_ID:
            try:
                username = uu.get_profile(table, path_user_id).get('username')
                paths = uu.invalidation_paths(
                    username, path_user_id, upload_id, portfolio_number
                )
                cf_client.create_invalidation(
                    DistributionId=CLOUDFRONT_DISTRIBUTION_ID,
                    InvalidationBatch={
                        'Paths': {'Quantity': len(paths), 'Items': paths},
                        'CallerReference': correlation_id,
                    },
                )
            except Exception as cf_err:
                _log('ERROR', 'CloudFront invalidation failed (non-fatal)',
                     correlationId=correlation_id, error=str(cf_err))

        _log('INFO', 'Portfolio live toggled',
             correlationId=correlation_id, userId=path_user_id,
             uploadId=upload_id, isLive=is_live)

        return _response(200, {
            'message': 'Portfolio updated',
            'uploadId': upload_id,
            'isLive': is_live,
        })

    except Exception as e:
        _log('ERROR', 'Unexpected error', correlationId=correlation_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})
