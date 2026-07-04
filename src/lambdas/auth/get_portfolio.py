"""
Lambda: Get Portfolio
API endpoint to retrieve portfolio data for a user.
"""

import json
import os
import decimal
import boto3

dynamodb = boto3.resource('dynamodb')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')


class _DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns numeric types as Decimal; convert to int/float for JSON."""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)

# ---------------------------------------------------------------------------
# Structured logger — outputs JSON, captured by CloudWatch Logs
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    entry = {
        "level": level,
        "function": "get_portfolio",
        "message": message,
    }
    entry.update(kwargs)
    print(json.dumps(entry))


def _log_info(message: str, **kwargs) -> None:
    _log("INFO", message, **kwargs)


def _log_error(message: str, **kwargs) -> None:
    _log("ERROR", message, **kwargs)


def lambda_handler(event, context):
    """Get portfolio data for a user."""
    correlation_id = context.aws_request_id if context else 'local'
    try:
        path_params = event.get('pathParameters') or {}
        user_id = path_params.get('userId')
        upload_id = path_params.get('uploadId')

        # Get requesting user's ID from Cognito claims
        requesting_user_id = (
            event['requestContext']['authorizer']['claims']['sub']
        )

        _log_info(
            "Portfolio request",
            correlationId=correlation_id,
            requestedUserId=user_id,
            uploadId=upload_id,
        )

        # Authorization: users can only access their own portfolio.
        if user_id != requesting_user_id:
            _log_info(
                "Access denied: userId mismatch",
                correlationId=correlation_id,
                requestingUserId=requesting_user_id,
                requestedUserId=user_id,
            )
            return _response(403, {'error': 'Access denied'})

        if not upload_id:
            return _response(400, {'error': 'Missing uploadId'})

        # Get portfolio from DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.get_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': f'PORTFOLIO#{upload_id}',
            }
        )

        if 'Item' not in response:
            return _response(404, {'error': 'Portfolio not found'})

        item = response['Item']

        # Return portfolio data
        return _response(200, {
            'userId': user_id,
            'uploadId': upload_id,
            'status': item.get('status'),
            'portfolioPath': item.get('portfolioPath'),
            'parsedData': item.get('parsedData'),
            'portfolioContent': item.get('portfolioContent'),
            'category': item.get('category', 'software_engineer'),
            'templateId': item.get('templateId', 'minimal'),
            'version': item.get('version'),
            'isLive': item.get('isLive', False),
            'activeVersion': item.get('activeVersion'),
            'createdAt': item.get('createdAt'),
            'updatedAt': item.get('updatedAt'),
            'lastPublishedAt': item.get('lastPublishedAt'),
            'sectionOrder': item.get('sectionOrder'),
            'hiddenSections': item.get('hiddenSections'),
            'templateOverrides': item.get('templateOverrides'),
        })

    except Exception as e:
        _log_error(
            "Unexpected error",
            correlationId=correlation_id,
            error=str(e),
        )
        return _response(500, {'error': 'Internal server error'})


def _response(status_code, body):
    """Create API Gateway response."""
    allowed_origin = os.environ.get('ALLOWED_ORIGIN', '*')
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': allowed_origin,
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body, cls=_DecimalEncoder),
    }
