"""
Lambda: Cancel Upload
Marks an in-flight upload as CANCELLED so the frontend stops polling.
Only allowed if the upload is not already in a terminal state.
"""

import json
import os
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

TERMINAL_STATES = {
    'COMPLETE', 'REJECTED', 'AI_FAILED', 'FAILED', 'INVALID_DOCUMENT', 'CANCELLED'
}


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "cancel_upload", "message": message, **kwargs}))


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'
    try:
        upload_id = event['pathParameters'].get('uploadId')
        user_id = event['requestContext']['authorizer']['claims']['sub']

        _log('INFO', 'Cancel requested', correlationId=correlation_id,
             userId=user_id, uploadId=upload_id)

        table = dynamodb.Table(DYNAMODB_TABLE)

        response = table.get_item(
            Key={'PK': f'USER#{user_id}', 'SK': f'UPLOAD#{upload_id}'}
        )

        if 'Item' not in response:
            return _response(404, {'error': 'Upload not found'})

        current_status = response['Item'].get('status', '')
        if current_status in TERMINAL_STATES:
            return _response(409, {
                'error': f'Upload cannot be cancelled — it is already {current_status}'
            })

        table.update_item(
            Key={'PK': f'USER#{user_id}', 'SK': f'UPLOAD#{upload_id}'},
            UpdateExpression='SET #s = :status, updatedAt = :now',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':status': 'CANCELLED',
                ':now': datetime.now(timezone.utc).isoformat()
            }
        )

        _log('INFO', 'Upload cancelled', correlationId=correlation_id,
             userId=user_id, uploadId=upload_id)
        return _response(200, {'message': 'Upload cancelled successfully'})

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
