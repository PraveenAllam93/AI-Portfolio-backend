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

dynamodb = boto3.resource('dynamodb')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')


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

        # Verify portfolio exists
        result = table.get_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': f'PORTFOLIO#{upload_id}'},
            ProjectionExpression='uploadId',
        )
        if 'Item' not in result:
            return _response(404, {'error': 'Portfolio not found'})

        table.update_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': f'PORTFOLIO#{upload_id}'},
            UpdateExpression='SET isLive = :live, updatedAt = :now',
            ExpressionAttributeValues={
                ':live': is_live,
                ':now': datetime.now(timezone.utc).isoformat(),
            },
        )

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
