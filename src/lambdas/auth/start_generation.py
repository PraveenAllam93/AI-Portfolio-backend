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

# Anonymous "Try for free" guests are real Cognito users whose email lives on
# this reserved, non-routable domain (created by the frontend guest-session
# endpoint). Their portfolios are generated as a private DRAFT only — never
# auto-published to a public URL — until they create a real account. Detection
# is by the verified `email` claim, so a client cannot spoof guest/non-guest.
GUEST_EMAIL_DOMAIN = os.environ.get('GUEST_EMAIL_DOMAIN', 'guest.aifolio.internal')

# Allowlists — keep in sync with upload/handler.py and patch_portfolio.py
# (see memory: adding a profession/template touches every backend allowlist).
ALLOWED_CATEGORIES = {
    'software_engineer', 'designer', 'marketing', 'finance',
    'civil_engineer', 'mechanical_engineer',
}
# MUST stay in sync with the frontend TEMPLATE_META (templates/index.ts) and
# upload/handler.py ALLOWED_TEMPLATES. This list previously lagged 28 templates
# behind the renderer, so picking any newer template (torque, ledger, sterling,
# atelier, voltage, …) failed here with "Invalid templateId".
ALLOWED_TEMPLATES = {
    'aurora', 'nebula', 'codex', 'neon', 'circuit', 'glitch', 'navy-gold',
    'cosmos', 'retro', 'luxe', 'quantum', 'voltage', 'nimbus', 'citrus',
    'console', 'neural', 'flux', 'monolith', 'helix', 'orbit', 'iris',
    'terminal', 'beacon',
    'designer', 'designer-2', 'atelier', 'terra', 'ember', 'folio',
    'obsidian', 'muse', 'prism', 'salon',
    'marketing', 'momentum', 'apex', 'bloom', 'signal', 'vantage', 'canopy',
    'structura', 'blueprint',
    'precision', 'torque',
    'ledger', 'sterling',
}

# Cap on the resume text embedded in the SQS message body. SQS has a hard
# 256 KB limit — a long or OCR'd resume read whole from S3 would overflow it and
# fail send_message. The AI consumer (ai_processing) already truncates to its own
# MAX_RESUME_CHARS (40000), so a larger inline copy is pure risk with no benefit.
# The FULL text also stays in S3 (rawTextS3Key), so nothing is lost.
_MAX_SQS_RESUME_CHARS = int(os.environ.get('MAX_RESUME_CHARS', 40000))

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
        claims = event['requestContext']['authorizer']['claims']
        user_id = claims['sub']
        # Guests get a draft-only pipeline (no auto-publish). Derived from the
        # verified email claim — never from client input.
        email = (claims.get('email') or '').lower()
        is_guest = email.endswith('@' + GUEST_EMAIL_DOMAIN)

        body = json.loads(event.get('body') or '{}')
        category = body.get('category', '')
        template_id = body.get('templateId', '')

        _log('INFO', 'Start generation requested', correlationId=correlation_id,
             userId=user_id, uploadId=upload_id, category=category,
             templateId=template_id, isGuest=is_guest)

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

        try:
            sqs_client.send_message(
                QueueUrl=PROCESSING_QUEUE,
                MessageBody=json.dumps({
                    'userId': user_id,
                    'uploadId': upload_id,
                    # Capped to stay under the 256 KB SQS limit; full text remains
                    # in S3 at rawTextS3Key. The consumer truncates here anyway.
                    'resumeText': resume_text[:_MAX_SQS_RESUME_CHARS],
                    'rawTextS3Key': text_key,
                    'filename': filename,
                    'category': category,
                    'templateId': template_id,
                    'contentHash': content_hash,
                    'atsFailed': ats_failed,
                    'isGuest': is_guest,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                }),
                MessageAttributes={
                    'userId': {'DataType': 'String', 'StringValue': user_id},
                    'uploadId': {'DataType': 'String', 'StringValue': upload_id},
                    'category': {'DataType': 'String', 'StringValue': category},
                },
            )
        except Exception as sqs_err:
            # The status was already flipped to QUEUED_FOR_AI (for idempotency).
            # If the enqueue fails, roll it back to AWAITING_SELECTION so the
            # record isn't stuck forever and the user can retry.
            _log('ERROR', 'SQS enqueue failed — reverting to AWAITING_SELECTION',
                 correlationId=correlation_id, userId=user_id, uploadId=upload_id,
                 error=str(sqs_err))
            try:
                table.update_item(
                    Key=key,
                    UpdateExpression='SET #s = :status, #gsi1pk = :gsi1pk, updatedAt = :now',
                    ExpressionAttributeNames={'#s': 'status', '#gsi1pk': 'GSI1PK'},
                    ExpressionAttributeValues={
                        ':status': _READY_STATUS,
                        ':gsi1pk': f'STATUS#{_READY_STATUS}',
                        ':now': datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as revert_err:
                _log('ERROR', 'Failed to revert status after SQS failure',
                     correlationId=correlation_id, userId=user_id, uploadId=upload_id,
                     error=str(revert_err))
            return _response(503, {'error': 'Could not start generation. Please try again.'})

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
