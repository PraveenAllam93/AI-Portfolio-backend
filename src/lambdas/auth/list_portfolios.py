"""
Lambda: List Portfolios

GET /portfolio/{userId}

Returns all portfolio records for the authenticated user.
Each entry is a summary card — no full parsedData/portfolioContent returned.
"""

import json
import os
import decimal
import boto3
from boto3.dynamodb.conditions import Key
from urllib.parse import unquote

dynamodb = boto3.resource('dynamodb')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
CLOUDFRONT_URL = os.environ.get('CLOUDFRONT_URL', '').rstrip('/')


class _DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "list_portfolios", "message": message, **kwargs}))


def _response(status: int, body) -> dict:
    allowed_origin = os.environ.get('ALLOWED_ORIGIN', '*')
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': allowed_origin,
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body, cls=_DecimalEncoder),
    }


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    path_params = event.get('pathParameters') or {}
    path_user_id = unquote(path_params.get('userId', ''))
    token_sub = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )

    if not path_user_id or path_user_id != token_sub:
        return _response(403, {'error': 'Forbidden'})

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)

        # Query all PORTFOLIO# records for this user, paginating through all pages
        items = []
        query_kwargs = dict(
            KeyConditionExpression=(
                Key('PK').eq(f'USER#{path_user_id}') &
                Key('SK').begins_with('PORTFOLIO#')
            ),
        )
        while True:
            response = table.query(**query_kwargs)
            items.extend(response.get('Items', []))
            if 'LastEvaluatedKey' not in response:
                break
            query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

        # Filter out version snapshots — keep only the top-level portfolio records
        portfolios = []
        for item in items:
            sk = item.get('SK', '')
            if '#VERSION#' in sk:
                continue

            upload_id = item.get('uploadId', sk.replace('PORTFOLIO#', ''))
            portfolio_path = item.get('portfolioPath', '')
            active_version = item.get('activeVersion')

            portfolio_url = None
            if CLOUDFRONT_URL and portfolio_path and active_version:
                portfolio_url = f'{CLOUDFRONT_URL}/{portfolio_path}/index.html'

            portfolios.append({
                'uploadId': upload_id,
                'templateId': item.get('templateId', 'minimal'),
                'status': item.get('status'),
                'portfolioPath': portfolio_path,
                'activeVersion': active_version,
                'portfolioUrl': portfolio_url,
                'isLive': item.get('isLive', False),
                'category': item.get('category', 'software_engineer'),
                'version': item.get('version'),
                'createdAt': item.get('createdAt'),
                'updatedAt': item.get('updatedAt'),
            })

        # Newest first
        portfolios.sort(key=lambda x: x.get('createdAt') or '', reverse=True)

        _log('INFO', 'Portfolios listed',
             correlationId=correlation_id, userId=path_user_id, count=len(portfolios))

        return _response(200, {'portfolios': portfolios, 'total': len(portfolios)})

    except Exception as e:
        _log('ERROR', 'Unexpected error', correlationId=correlation_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})
