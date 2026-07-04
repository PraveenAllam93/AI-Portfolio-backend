"""
Lambda: Start Generation

Resumes the resume pipeline after the user has confirmed/overridden the
auto-detected profession and picked a template.

The pipeline pauses at status AWAITING_SELECTION (set by resume_ingestion, which
extracted the text, persisted it to the validated bucket, and classified the
profession). This Lambda:
  1. Validates the chosen category + templateId.
  2. Writes them to the UPLOAD record.
  3. Reads the extracted text back from the validated bucket.
  4. Queues the AI-processing job on SQS (the step that used to live at the tail
     of resume_ingestion).

Security notes:
  - PK/SK are scoped to the caller's Cognito sub — no cross-user access.
  - Only acts on records in AWAITING_SELECTION; anything else is rejected or
    treated as already-started (idempotent) so a double click can't double-queue.
"""

import json
import os
import boto3
from datetime import datetime, timezone

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
VALIDATED_BUCKET = os.environ.get('VALIDATED_BUCKET')
PROCESSING_QUEUE = os.environ.get('PROCESSING_QUEUE')

# Allowlists — keep in sync with upload/handler.py and patch_portfolio.py
# (see memory: adding a profession/template touches every backend allowlist).
ALLOWED_CATEGORIES = {
    'software_engineer', 'designer', 'marketing', 'finance',
    'civil_engineer', 'mechanical_engineer',
}
ALLOWED_TEMPLATES = {
    'minimal', 'modern', 'bold', 'creative', 'aurora', 'nebula', 'luxury',
    'executive', 'codex', 'neon', 'circuit', 'glitch', 'navy-gold', 'cosmos',
    'retro', 'luxe', 'quantum', 'designer', 'designer-2', 'marketing',
    'structura', 'blueprint', 'precision',
}

# Status the record must be in for generation to start.
_READY_STATUS = 'AWAITING_SELECTION'
# Statuses meaning generation has already begun — treat start as idempotent.
_ALREADY_STARTED = {
    'QUEUED_FOR_AI', 'AI_PROCESSING', 'AI_COMPLETE', 'GENERATING', 'COMPLETE',
}


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "start_generation", "message": message, **kwargs}))


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'
    try:
        upload_id = (event.get('pathParameters') or {}).get('uploadId')
        user_id = event['requestContext']['authorizer']['claims']['sub']

        body = json.loads(event.get('body') or '{}')
        category = body.get('category', '')
        template_id = body.get('templateId', '')

        _log('INFO', 'Start generation requested', correlationId=correlation_id,
             userId=user_id, uploadId=upload_id, category=category, templateId=template_id)

        if not upload_id:
            return _response(400, {'error': 'Missing uploadId'})

        if category not in ALLOWED_CATEGORIES:
            return _response(400, {'error': 'Invalid category', 'allowed': sorted(ALLOWED_CATEGORIES)})

        if template_id not in ALLOWED_TEMPLATES:
            return _response(400, {'error': 'Invalid templateId', 'allowed': sorted(ALLOWED_TEMPLATES)})

        table = dynamodb.Table(DYNAMODB_TABLE)
        key = {'PK': f'USER#{user_id}', 'SK': f'UPLOAD#{upload_id}'}
        response = table.get_item(Key=key)

        if 'Item' not in response:
            return _response(404, {'error': 'Upload not found'})

        item = response['Item']
        status = item.get('status', '')

        # Idempotency: a second call after generation already started is a no-op.
        if status in _ALREADY_STARTED:
            _log('INFO', 'Generation already started — no-op', correlationId=correlation_id,
                 userId=user_id, uploadId=upload_id, status=status)
            return _response(200, {'message': 'Generation already started', 'status': status})

        if status != _READY_STATUS:
            return _response(409, {
                'error': f'Upload is not ready for generation (status: {status})'
            })

        text_key = item.get('rawTextS3Key')
        if not text_key:
            _log('ERROR', 'Missing rawTextS3Key on record', correlationId=correlation_id,
                 userId=user_id, uploadId=upload_id)
            return _response(409, {'error': 'Resume text is not available — please re-upload'})

        # Read the extracted text back from the trusted validated bucket.
        obj = s3_client.get_object(Bucket=VALIDATED_BUCKET, Key=text_key)
        resume_text = obj['Body'].read().decode('utf-8')

        content_hash = item.get('contentHash')
        ats_failed = bool(item.get('atsFailed', False))
        filename = item.get('filename', '')

        # Persist the user's choices, then move the record to QUEUED_FOR_AI.
        table.update_item(
            Key=key,
            UpdateExpression=(
                'SET #s = :status, category = :category, templateId = :template, '
                '#gsi1pk = :gsi1pk, updatedAt = :now'
            ),
            ExpressionAttributeNames={'#s': 'status', '#gsi1pk': 'GSI1PK'},
            ExpressionAttributeValues={
                ':status': 'QUEUED_FOR_AI',
                ':category': category,
                ':template': template_id,
                ':gsi1pk': 'STATUS#QUEUED_FOR_AI',
                ':now': datetime.now(timezone.utc).isoformat(),
            },
        )

        sqs_client.send_message(
            QueueUrl=PROCESSING_QUEUE,
            MessageBody=json.dumps({
                'userId': user_id,
                'uploadId': upload_id,
                'resumeText': resume_text,
                'filename': filename,
                'category': category,
                'templateId': template_id,
                'contentHash': content_hash,
                'atsFailed': ats_failed,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }),
            MessageAttributes={
                'userId': {'DataType': 'String', 'StringValue': user_id},
                'uploadId': {'DataType': 'String', 'StringValue': upload_id},
                'category': {'DataType': 'String', 'StringValue': category},
            },
        )

        _log('INFO', 'Queued for AI processing', correlationId=correlation_id,
             userId=user_id, uploadId=upload_id, category=category, templateId=template_id)
        return _response(200, {'message': 'Generation started', 'status': 'QUEUED_FOR_AI'})

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
