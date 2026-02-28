"""
Lambda: Get Portfolio
API endpoint to retrieve portfolio data for a user.
"""

import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

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
        # Get user ID from path parameter
        user_id = event['pathParameters'].get('userId')

        # Get requesting user's ID from Cognito claims
        requesting_user_id = (
            event['requestContext']['authorizer']['claims']['sub']
        )

        _log_info(
            "Portfolio request",
            correlationId=correlation_id,
            requestedUserId=user_id,
        )

        # Authorization: users can only access their own portfolio.
        # Return 403 — not 404 — so we don't enumerate valid user IDs.
        if user_id != requesting_user_id:
            _log_info(
                "Access denied: userId mismatch",
                correlationId=correlation_id,
                requestingUserId=requesting_user_id,
                requestedUserId=user_id,
            )
            return _response(403, {'error': 'Access denied'})

        # Get portfolio from DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.get_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PORTFOLIO#current',
            }
        )

        if 'Item' not in response:
            return _response(404, {'error': 'Portfolio not found'})

        item = response['Item']

        # Return portfolio data
        return _response(200, {
            'userId': user_id,
            'status': item.get('status'),
            'portfolioPath': item.get('portfolioPath'),
            'parsedData': item.get('parsedData'),
            'portfolioContent': item.get('portfolioContent'),
            'version': item.get('version'),
            'createdAt': item.get('createdAt'),
            'updatedAt': item.get('updatedAt'),
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
        'body': json.dumps(body),
    }
