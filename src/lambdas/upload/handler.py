"""
Lambda: Get Presigned Upload URL
Generates short-lived PUT URLs for uploading to the quarantine bucket.
"""

import json
import os
import uuid
import boto3
from datetime import datetime

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

QUARANTINE_BUCKET = os.environ.get('QUARANTINE_BUCKET')
MAX_UPLOAD_SIZE_MB = int(os.environ.get('MAX_UPLOAD_SIZE_MB', 10))
PRESIGNED_URL_EXPIRY = int(os.environ.get('PRESIGNED_URL_EXPIRY_SECONDS', 300))
ALLOWED_EXTENSIONS = os.environ.get('ALLOWED_EXTENSIONS', '.pdf,.docx').split(',')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')


def lambda_handler(event, context):
    """Generate presigned URL for file upload."""
    try:
        # Extract user ID from Cognito claims
        user_id = event['requestContext']['authorizer']['claims']['sub']

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename', '')
        content_type = body.get('contentType', '')

        # Validate file extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return _response(400, {
                'error': 'Invalid file type',
                'allowed': ALLOWED_EXTENSIONS
            })

        # Generate unique upload ID
        upload_id = str(uuid.uuid4())
        s3_key = f"{user_id}/{upload_id}/{filename}"

        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': QUARANTINE_BUCKET,
                'Key': s3_key,
                'ContentType': content_type,
            },
            ExpiresIn=PRESIGNED_URL_EXPIRY
        )

        # Record upload intent in DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.put_item(Item={
            'PK': f'USER#{user_id}',
            'SK': f'UPLOAD#{upload_id}',
            'uploadId': upload_id,
            'userId': user_id,
            'filename': filename,
            'status': 'PENDING_UPLOAD',
            'createdAt': datetime.utcnow().isoformat(),
            'GSI1PK': 'STATUS#PENDING_UPLOAD',
            'GSI1SK': f'USER#{user_id}#{upload_id}'
        })

        return _response(200, {
            'uploadUrl': presigned_url,
            'uploadId': upload_id,
            'expiresIn': PRESIGNED_URL_EXPIRY
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return _response(500, {'error': 'Internal server error'})


def _response(status_code, body):
    """Create API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        },
        'body': json.dumps(body)
    }
