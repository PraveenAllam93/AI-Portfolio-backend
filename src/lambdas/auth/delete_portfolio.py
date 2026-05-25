"""
Lambda: Delete Portfolio

DELETE /portfolio/{userId}/{uploadId}

Deletes a portfolio and all its data:
1. Query and delete all version snapshot records (PORTFOLIO#{uploadId}#VERSION#*)
2. Delete all S3 objects under {userId}/{uploadId}/ prefix (list + batch delete)
3. Delete the main PORTFOLIO#{uploadId} DynamoDB record
"""

import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from urllib.parse import unquote

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET', '')


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "delete_portfolio", "message": message, **kwargs}))


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


def _delete_s3_prefix(bucket: str, prefix: str, correlation_id: str) -> int:
    """Delete all S3 objects under the given prefix. Returns count of deleted objects."""
    deleted = 0
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = page.get('Contents', [])
        if not objects:
            continue
        s3_client.delete_objects(
            Bucket=bucket,
            Delete={
                'Objects': [{'Key': obj['Key']} for obj in objects],
                'Quiet': True,
            },
        )
        deleted += len(objects)
    return deleted


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

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)

        # Verify portfolio exists
        portfolio_res = table.get_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': f'PORTFOLIO#{upload_id}'},
        )
        if 'Item' not in portfolio_res:
            return _response(404, {'error': 'Portfolio not found'})

        # 1. Delete all version snapshot records
        version_items = []
        query_kwargs = dict(
            KeyConditionExpression=(
                Key('PK').eq(f'USER#{path_user_id}') &
                Key('SK').begins_with(f'PORTFOLIO#{upload_id}#VERSION#')
            ),
            ProjectionExpression='PK, SK',
        )
        while True:
            resp = table.query(**query_kwargs)
            version_items.extend(resp.get('Items', []))
            if 'LastEvaluatedKey' not in resp:
                break
            query_kwargs['ExclusiveStartKey'] = resp['LastEvaluatedKey']

        with table.batch_writer() as batch:
            for item in version_items:
                batch.delete_item(Key={'PK': item['PK'], 'SK': item['SK']})

        # 2. Delete S3 prefix — non-fatal
        if PORTFOLIO_BUCKET:
            try:
                s3_prefix = f'{path_user_id}/{upload_id}/'
                deleted_count = _delete_s3_prefix(PORTFOLIO_BUCKET, s3_prefix, correlation_id)
                _log('INFO', 'S3 objects deleted',
                     correlationId=correlation_id, prefix=s3_prefix, count=deleted_count)
            except Exception as s3_err:
                _log('ERROR', 'S3 delete failed (non-fatal)',
                     correlationId=correlation_id, error=str(s3_err))

        # 3. Delete main portfolio record
        table.delete_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': f'PORTFOLIO#{upload_id}'}
        )

        _log('INFO', 'Portfolio deleted',
             correlationId=correlation_id, userId=path_user_id,
             uploadId=upload_id, versionsDeleted=len(version_items))

        return _response(200, {
            'message': 'Portfolio deleted',
            'uploadId': upload_id,
            'versionsDeleted': len(version_items),
        })

    except Exception as e:
        _log('ERROR', 'Unexpected error', correlationId=correlation_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})
