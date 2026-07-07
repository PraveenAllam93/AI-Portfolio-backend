"""
Lambda: Get Image Upload Presigned URL

POST /portfolio/{userId}/image-upload-url

Generates a short-lived PUT URL for uploading a portfolio asset image
directly to the portfolio S3 bucket under {userId}/assets/{imageId}.{ext}.

The returned imageUrl is the CloudFront URL that should be stored in
parsedData.profile.profile_image or parsedData.experience[n].images etc.

Security:
- userId in path must exactly match Cognito token sub.
- Only image MIME types are accepted.
- File size is NOT enforced here (S3 will accept any size via presigned URL);
  callers should enforce size client-side before uploading.
- No quarantine pipeline needed for images — they are rendered as <img> src
  attributes, not executed, so XSS risk is negligible.
"""

import json
import os
import uuid
import boto3
from botocore.config import Config
from urllib.parse import unquote

_AWS_REGION = os.environ.get('AWS_REGION', 'ap-south-1')
s3_client = boto3.client(
    's3',
    region_name=_AWS_REGION,
    endpoint_url=f'https://s3.{_AWS_REGION}.amazonaws.com',
    config=Config(s3={'addressing_style': 'virtual'}),
)
dynamodb = boto3.resource('dynamodb')

PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
CLOUDFRONT_DOMAIN = os.environ.get('CLOUDFRONT_DOMAIN')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PRESIGNED_URL_EXPIRY = int(os.environ.get('PRESIGNED_URL_EXPIRY_SECONDS', 300))
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

ALLOWED_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
}

MIME_TO_EXT = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
    'image/gif': '.gif',
}


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "get_image_upload_url", "message": message, **kwargs}))


def _response(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body),
    }


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    # Auth: path userId must match token sub
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

    content_type = body.get('contentType', '').strip()

    if content_type not in ALLOWED_MIME_TYPES:
        return _response(400, {
            'error': 'Invalid image type',
            'allowed': sorted(ALLOWED_MIME_TYPES),
        })

    ext = MIME_TO_EXT[content_type]
    image_id = str(uuid.uuid4())
    s3_key = f"{path_user_id}/{upload_id}/assets/{image_id}{ext}"

    presigned_url = s3_client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': PORTFOLIO_BUCKET,
            'Key': s3_key,
            'ContentType': content_type,
        },
        ExpiresIn=PRESIGNED_URL_EXPIRY,
    )

    image_url = f"https://{CLOUDFRONT_DOMAIN}/{s3_key}"

    _log('INFO', 'Image upload URL generated',
         correlationId=correlation_id,
         userId=path_user_id,
         s3Key=s3_key)

    return _response(200, {
        'uploadUrl': presigned_url,
        'imageUrl': image_url,
        'expiresIn': PRESIGNED_URL_EXPIRY,
    })
