"""
Lambda: Get Portfolio Preview URL

GET /portfolio/{userId}/{uploadId}/preview?versionId=v3

Owner-only. Returns a short-lived presigned S3 GET URL for any portfolio version
(active or not, live or not). The URL expires in 1 hour.

This is the mechanism by which owners preview their non-public versions —
the public CloudFront URL for those versions is blocked by Lambda@Edge.

Security:
  - userId in path MUST match the Cognito token sub.
  - versionId is validated against the DynamoDB VERSION# record before signing.
  - Presigned URL is caller-unaware (bearer token): anyone who holds the URL can
    view the HTML for up to 1 hour. Owners should not share it publicly.
"""

import json
import os
import boto3
from urllib.parse import unquote

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
PREVIEW_URL_TTL = int(os.environ.get('PREVIEW_URL_TTL_SECONDS', '3600'))  # 1 hour


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({'level': level, 'function': 'get_portfolio_preview_url',
                      'message': message, **kwargs}))


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

    qs = event.get('queryStringParameters') or {}
    version_id = qs.get('versionId', '').strip()

    if not version_id:
        return _response(400, {'error': 'Missing versionId query parameter'})

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)

        if version_id == 'draft':
            # Draft path: verify the portfolio record exists.
            result = table.get_item(
                Key={'PK': f'USER#{path_user_id}', 'SK': f'PORTFOLIO#{upload_id}'},
                ProjectionExpression='uploadId',
            )
            if 'Item' not in result:
                return _response(404, {'error': 'Portfolio not found'})
            portfolio_path = f'{path_user_id}/{upload_id}/draft'
        else:
            # Published version: verify the VERSION# snapshot exists.
            result = table.get_item(
                Key={
                    'PK': f'USER#{path_user_id}',
                    'SK': f'PORTFOLIO#{upload_id}#VERSION#{version_id}',
                },
                ProjectionExpression='portfolioPath',
            )
            if 'Item' not in result:
                return _response(404, {'error': 'Version not found'})
            portfolio_path = result['Item'].get('portfolioPath', '')
            if not portfolio_path:
                return _response(404, {'error': 'Version has no portfolio path'})

        s3_key = f'{portfolio_path}/index.html'

        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': PORTFOLIO_BUCKET, 'Key': s3_key},
            ExpiresIn=PREVIEW_URL_TTL,
        )

        _log('INFO', 'Preview URL generated', correlationId=correlation_id,
             userId=path_user_id, uploadId=upload_id, versionId=version_id)

        return _response(200, {
            'previewUrl': presigned_url,
            'expiresInSeconds': PREVIEW_URL_TTL,
        })

    except Exception as e:
        _log('ERROR', 'Unexpected error', correlationId=correlation_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})
