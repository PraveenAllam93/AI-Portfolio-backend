"""
Lambda: List Portfolio Versions
Returns all published portfolio versions for a user, with which one is active.
"""

import json
import os
import decimal
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')


class _DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "list_versions", "message": message, **kwargs}))


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'
    try:
        user_id = event['pathParameters'].get('userId')
        requesting_user_id = event['requestContext']['authorizer']['claims']['sub']

        if user_id != requesting_user_id:
            _log('INFO', 'Access denied', correlationId=correlation_id,
                 requestingUserId=requesting_user_id, requestedUserId=user_id)
            return _response(403, {'error': 'Access denied'})

        table = dynamodb.Table(DYNAMODB_TABLE)

        # Get active version from PORTFOLIO#current
        current_res = table.get_item(
            Key={'PK': f'USER#{user_id}', 'SK': 'PORTFOLIO#current'}
        )
        active_version = None
        if 'Item' in current_res:
            active_version = current_res['Item'].get('activeVersion')

        # Query all version snapshot records
        response = table.query(
            KeyConditionExpression=(
                Key('PK').eq(f'USER#{user_id}') &
                Key('SK').begins_with('PORTFOLIO#VERSION#')
            )
        )

        versions = []
        for item in response.get('Items', []):
            sk = item.get('SK', '')
            version_id = sk.replace('PORTFOLIO#VERSION#', '')
            versions.append({
                'versionId': version_id,
                'version': item.get('version'),
                'portfolioPath': item.get('portfolioPath'),
                'templateId': item.get('templateId'),
                'createdAt': item.get('createdAt'),
                'isActive': version_id == active_version,
            })

        versions.sort(key=lambda x: x.get('version') or 0, reverse=True)

        return _response(200, {
            'versions': versions,
            'activeVersion': active_version,
            'total': len(versions)
        })

    except Exception as e:
        _log('ERROR', 'Unexpected error', correlationId=correlation_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})


def _response(status_code, body):
    allowed_origin = os.environ.get('ALLOWED_ORIGIN', '*')
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': allowed_origin,
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body, cls=_DecimalEncoder)
    }
