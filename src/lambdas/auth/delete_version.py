"""
Lambda: Delete Portfolio Version
Deletes a specific portfolio version from DynamoDB and S3.
Cannot delete the currently active version.
"""

import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET', '')


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "delete_version", "message": message, **kwargs}))


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'
    try:
        path_params = event.get('pathParameters') or {}
        user_id = path_params.get('userId')
        upload_id = path_params.get('uploadId')
        version_id = path_params.get('versionId')
        requesting_user_id = event['requestContext']['authorizer']['claims']['sub']

        if user_id != requesting_user_id:
            return _response(403, {'error': 'Access denied'})

        if not upload_id:
            return _response(400, {'error': 'Missing uploadId'})

        table = dynamodb.Table(DYNAMODB_TABLE)

        # Verify version exists
        version_res = table.get_item(
            Key={'PK': f'USER#{user_id}', 'SK': f'PORTFOLIO#{upload_id}#VERSION#{version_id}'}
        )
        if 'Item' not in version_res:
            return _response(404, {'error': 'Version not found'})

        portfolio_path = version_res['Item'].get('portfolioPath', '')

        # Block deletion of the active version — activate another first
        current_res = table.get_item(
            Key={'PK': f'USER#{user_id}', 'SK': f'PORTFOLIO#{upload_id}'}
        )
        if 'Item' in current_res:
            if current_res['Item'].get('activeVersion') == version_id:
                return _response(409, {
                    'error': 'Cannot delete the active version. Set another version as main first.'
                })

        # Delete DynamoDB version record
        table.delete_item(
            Key={'PK': f'USER#{user_id}', 'SK': f'PORTFOLIO#{upload_id}#VERSION#{version_id}'}
        )

        # Delete S3 objects — non-fatal
        if PORTFOLIO_BUCKET and portfolio_path:
            try:
                s3_client.delete_object(
                    Bucket=PORTFOLIO_BUCKET,
                    Key=f'{portfolio_path}/index.html'
                )
            except Exception as s3_err:
                _log('ERROR', 'S3 delete failed (non-fatal)',
                     correlationId=correlation_id, error=str(s3_err))

        _log('INFO', 'Version deleted', correlationId=correlation_id,
             userId=user_id, versionId=version_id)
        return _response(200, {'message': f'{version_id} has been deleted'})

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
