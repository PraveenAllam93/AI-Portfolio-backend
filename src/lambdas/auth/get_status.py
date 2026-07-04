"""
Lambda: Get Status
API endpoint to check the processing status of a resume upload.
"""

import json
import os
import boto3
from datetime import datetime, timezone, timedelta

dynamodb = boto3.resource('dynamodb')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

# AI processing Lambda timeout is 300s. If a record is still AI_PROCESSING
# after this threshold, the Lambda was killed (timeout/crash) and can never
# update its own status — treat it as failed so the frontend stops polling.
_AI_STALE_THRESHOLD = timedelta(seconds=360)

# Portfolio generator timeout is 60s, invoked async with up to 3 Lambda retries
# (3 × 60s = 180s) plus buffer. If AI_COMPLETE or GENERATING has not progressed
# past this threshold, the portfolio Lambda failed silently — surface as FAILED.
_PORTFOLIO_STALE_THRESHOLD = timedelta(seconds=300)

# ---------------------------------------------------------------------------
# Structured logger — outputs JSON to stdout, captured by CloudWatch Logs
# ---------------------------------------------------------------------------
_LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

def _log(level: str, message: str, **kwargs) -> None:
    """Emit a structured JSON log entry."""
    entry = {"level": level, "function": "get_status", "message": message}
    entry.update(kwargs)
    print(json.dumps(entry))

def _log_info(message: str, **kwargs) -> None:
    _log("INFO", message, **kwargs)

def _log_error(message: str, **kwargs) -> None:
    _log("ERROR", message, **kwargs)

# Status descriptions for user-friendly messages
STATUS_MESSAGES = {
    'PENDING_UPLOAD': 'Waiting for file upload',
    'VALIDATING': 'Validating your resume...',
    'VALIDATED': 'Resume validated successfully',
    'REJECTED': 'Resume validation failed',
    'EXTRACTING_TEXT': 'Extracting text from your resume...',
    'AWAITING_SELECTION': 'Detecting your profession...',
    'QUEUED_FOR_AI': 'Queued for AI processing',
    'AI_PROCESSING': 'AI is analyzing your resume...',
    'AI_COMPLETE': 'AI analysis complete',
    'AI_FAILED': 'AI processing failed',
    'INVALID_DOCUMENT': 'Document is not a resume',
    'GENERATING': 'Generating your portfolio...',
    'COMPLETE': 'Portfolio is ready!',
    'FAILED': 'Processing failed',
    'CANCELLED': 'Upload cancelled',
}

# Terminal states — frontend should stop polling
TERMINAL_STATES = {'COMPLETE', 'REJECTED', 'AI_FAILED', 'FAILED', 'INVALID_DOCUMENT', 'CANCELLED'}

# Failure states — frontend can offer a retry (CANCELLED is terminal but not a failure)
FAILURE_STATES = {'REJECTED', 'AI_FAILED', 'FAILED', 'INVALID_DOCUMENT'}

# Which pipeline stage each failure originated from
FAILURE_STAGE = {
    'REJECTED': 'VALIDATION',
    'AI_FAILED': 'AI_PROCESSING',
    'FAILED': 'PROCESSING',
    'INVALID_DOCUMENT': 'AI_PROCESSING',
}

# Approximate progress percentage per status (for progress bars)
STATUS_PROGRESS = {
    'PENDING_UPLOAD': 0,
    'VALIDATING': 15,
    'VALIDATED': 25,
    'EXTRACTING_TEXT': 35,
    'AWAITING_SELECTION': 50,
    'QUEUED_FOR_AI': 45,
    'AI_PROCESSING': 60,
    'AI_COMPLETE': 80,
    'GENERATING': 90,
    'COMPLETE': 100,
    'REJECTED': 15,
    'AI_FAILED': 60,
    'INVALID_DOCUMENT': 60,
    'FAILED': 40,
    'CANCELLED': 0,
}


def lambda_handler(event, context):
    """Get processing status for an upload."""
    correlation_id = context.aws_request_id if context else 'local'
    try:
        # Get upload ID from path parameter
        upload_id = event['pathParameters'].get('uploadId')

        # Get user ID from Cognito claims
        user_id = event['requestContext']['authorizer']['claims']['sub']

        _log_info("Status check", correlationId=correlation_id,
                  userId=user_id, uploadId=upload_id)

        # Get status from DynamoDB — PK/SK scoped to this user, no cross-user access possible
        table = dynamodb.Table(DYNAMODB_TABLE)
        response = table.get_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': f'UPLOAD#{upload_id}'
            }
        )

        if 'Item' not in response:
            _log_info("Upload not found", correlationId=correlation_id,
                      userId=user_id, uploadId=upload_id)
            return _response(404, {'error': 'Upload not found'})

        item = response['Item']
        status = item.get('status', 'UNKNOWN')

        # If AI processing Lambda was killed (timeout/crash), it can never update
        # its own status. Detect stale AI_PROCESSING and surface it as AI_FAILED
        # so the frontend stops polling instead of waiting forever.
        if status == 'AI_PROCESSING':
            updated_at_str = item.get('updatedAt')
            if updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str)
                    if datetime.now(timezone.utc) - updated_at > _AI_STALE_THRESHOLD:
                        status = 'AI_FAILED'
                        _log_info(
                            "Stale AI_PROCESSING detected — surfacing as AI_FAILED",
                            correlationId=correlation_id,
                            userId=user_id,
                            uploadId=upload_id,
                            updatedAt=updated_at_str,
                        )
                except (ValueError, TypeError):
                    pass

        # If portfolio Lambda failed silently (async invocation — errors are not
        # propagated back), the upload stays at AI_COMPLETE or GENERATING forever.
        # Detect stale portfolio states and surface as FAILED so polling stops.
        if status in ('AI_COMPLETE', 'GENERATING'):
            updated_at_str = item.get('updatedAt')
            if updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str)
                    if datetime.now(timezone.utc) - updated_at > _PORTFOLIO_STALE_THRESHOLD:
                        stalled_status = status
                        status = 'FAILED'
                        _log_info(
                            "Stale portfolio generation detected — surfacing as FAILED",
                            correlationId=correlation_id,
                            userId=user_id,
                            uploadId=upload_id,
                            stalledStatus=stalled_status,
                            updatedAt=updated_at_str,
                        )
                except (ValueError, TypeError):
                    pass

        # Build response
        result = {
            'uploadId': upload_id,
            'status': status,
            'message': STATUS_MESSAGES.get(status, 'Processing...'),
            'filename': item.get('filename'),
            'createdAt': item.get('createdAt'),
            'updatedAt': item.get('updatedAt'),
            'progress': STATUS_PROGRESS.get(status, 0),
            'isTerminal': status in TERMINAL_STATES,
        }

        # Expose the auto-detected profession so the upload wizard can
        # pre-select / auto-skip the profession step. Advisory only.
        if status == 'AWAITING_SELECTION':
            predicted = item.get('predictedProfession')
            confidence = item.get('predictedConfidence')
            result['predictedProfession'] = predicted if predicted else None
            try:
                result['predictedConfidence'] = int(confidence) if confidence is not None else 0
            except (TypeError, ValueError):
                result['predictedConfidence'] = 0

        # Add portfolio URL if complete
        if status == 'COMPLETE':
            result['portfolioPath'] = item.get('portfolioPath')
            result['canRetry'] = False

        # Add failure details if failed — never expose raw internal errors to the client
        if status in FAILURE_STATES:
            stage = FAILURE_STAGE.get(status, 'UNKNOWN')
            result['failureReason'] = _safe_failure_message(status)
            result['failureStage'] = stage
            result['canRetry'] = True
            # Log the real reason internally for debugging
            _log_info("Upload failed", correlationId=correlation_id,
                      userId=user_id, uploadId=upload_id, stage=stage,
                      internalReason=item.get('reason') or item.get('error'))

        return _response(200, result)

    except Exception as e:
        _log_error("Unexpected error", correlationId=correlation_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})


def _safe_failure_message(status: str) -> str:
    """Return a user-safe failure description — never internal error details."""
    messages = {
        'REJECTED': 'Your file could not be validated. Please check that it is a valid PDF or DOCX resume.',
        'AI_FAILED': 'We were unable to process your resume with AI. Please try again.',
        'INVALID_DOCUMENT': (
            'The uploaded document does not appear to be a resume. '
            'Please upload a resume (CV) in PDF or DOCX format.'
        ),
        'FAILED': 'An error occurred while processing your resume. Please try again.',
    }
    return messages.get(status, 'Processing failed. Please try again.')


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
        'body': json.dumps(body)
    }
