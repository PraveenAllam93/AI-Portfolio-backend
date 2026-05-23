"""
Lambda: Activate Portfolio Version
Sets a specific published version as the live/main portfolio.
Updates PORTFOLIO#current and invalidates CloudFront.
"""

import json
import os
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
cf_client = boto3.client('cloudfront')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
CLOUDFRONT_DISTRIBUTION_ID = os.environ.get('CLOUDFRONT_DISTRIBUTION_ID', '')


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "activate_version", "message": message, **kwargs}))


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'
    try:
        user_id = event['pathParameters'].get('userId')
        version_id = event['pathParameters'].get('versionId')
        requesting_user_id = event['requestContext']['authorizer']['claims']['sub']

        if user_id != requesting_user_id:
            return _response(403, {'error': 'Access denied'})

        table = dynamodb.Table(DYNAMODB_TABLE)

        # Verify the version exists and belongs to this user
        version_res = table.get_item(
            Key={'PK': f'USER#{user_id}', 'SK': f'PORTFOLIO#VERSION#{version_id}'}
        )
        if 'Item' not in version_res:
            return _response(404, {'error': 'Version not found'})

        portfolio_path = version_res['Item'].get('portfolioPath', '')

        # Point PORTFOLIO#current at this version
        table.update_item(
            Key={'PK': f'USER#{user_id}', 'SK': 'PORTFOLIO#current'},
            UpdateExpression='SET activeVersion = :v, portfolioPath = :path, updatedAt = :now',
            ExpressionAttributeValues={
                ':v': version_id,
                ':path': portfolio_path,
                ':now': datetime.now(timezone.utc).isoformat()
            }
        )

        # Invalidate CloudFront cache — non-fatal
        if CLOUDFRONT_DISTRIBUTION_ID:
            try:
                cf_client.create_invalidation(
                    DistributionId=CLOUDFRONT_DISTRIBUTION_ID,
                    InvalidationBatch={
                        'Paths': {'Quantity': 1, 'Items': [f'/{user_id}/*']},
                        'CallerReference': correlation_id
                    }
                )
            except Exception as cf_err:
                _log('ERROR', 'CloudFront invalidation failed (non-fatal)',
                     correlationId=correlation_id, error=str(cf_err))

        _log('INFO', 'Version activated', correlationId=correlation_id,
             userId=user_id, versionId=version_id, portfolioPath=portfolio_path)
        return _response(200, {
            'message': f'{version_id} is now your active portfolio',
            'portfolioPath': portfolio_path
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
        'body': json.dumps(body)
    }
