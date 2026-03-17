"""
Lambda: Get Status
API endpoint to check the processing status of a resume upload.
"""

import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
MAIN_TABLE = os.environ.get('MAIN_TABLE')

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
    'QUEUED_FOR_AI': 'Queued for AI processing',
    'AI_PROCESSING': 'AI is analyzing your resume...',
    'AI_COMPLETE': 'AI analysis complete',
    'AI_FAILED': 'AI processing failed',
    'GENERATING': 'Generating your portfolio...',
    'COMPLETE': 'Portfolio is ready!',
    'FAILED': 'Processing failed'
}

# Terminal states — frontend should stop polling
TERMINAL_STATES = {'COMPLETE', 'REJECTED', 'AI_FAILED', 'FAILED'}

# Failure states — frontend can offer a retry
FAILURE_STATES = {'REJECTED', 'AI_FAILED', 'FAILED'}

# Which pipeline stage each failure originated from
FAILURE_STAGE = {
    'REJECTED': 'VALIDATION',
    'AI_FAILED': 'AI_PROCESSING',
    'FAILED': 'PROCESSING',
}

# Approximate progress percentage per status (for progress bars)
STATUS_PROGRESS = {
    'PENDING_UPLOAD': 0,
    'VALIDATING': 15,
    'VALIDATED': 25,
    'EXTRACTING_TEXT': 35,
    'QUEUED_FOR_AI': 45,
    'AI_PROCESSING': 60,
    'AI_COMPLETE': 80,
    'GENERATING': 90,
    'COMPLETE': 100,
    'REJECTED': 15,
    'AI_FAILED': 60,
    'FAILED': 40,
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
        table = dynamodb.Table(MAIN_TABLE)
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
