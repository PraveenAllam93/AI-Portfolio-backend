"""
Lambda: Get Presigned Upload URL
Generates short-lived PUT URLs for uploading to the quarantine bucket.
"""

import json
import os
import re
import uuid
import boto3
from datetime import datetime, timezone

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

QUARANTINE_BUCKET = os.environ.get('QUARANTINE_BUCKET')
MAX_UPLOAD_SIZE_MB = int(os.environ.get('MAX_UPLOAD_SIZE_MB', 10))
PRESIGNED_URL_EXPIRY = int(
    os.environ.get('PRESIGNED_URL_EXPIRY_SECONDS', 300)
)
ALLOWED_EXTENSIONS = os.environ.get(
    'ALLOWED_EXTENSIONS', '.pdf,.docx'
).split(',')
ALLOWED_MIME_TYPES = os.environ.get(
    'ALLOWED_MIME_TYPES',
    'application/pdf,'
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
).split(',')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
# Maximum concurrent pending/active uploads per user (abuse protection)
MAX_ACTIVE_UPLOADS = int(os.environ.get('MAX_ACTIVE_UPLOADS', 5))

# Safe filename: alphanumeric, dash, underscore, dot only. Max 200 chars.
_SAFE_FILENAME_RE = re.compile(r'^[\w\-. ]{1,200}$')

# ---------------------------------------------------------------------------
# Structured logger — outputs JSON, captured by CloudWatch Logs
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    entry = {
        "level": level,
        "function": "get_presigned_url",
        "message": message,
    }
    entry.update(kwargs)
    print(json.dumps(entry))


def _log_info(message: str, **kwargs) -> None:
    _log("INFO", message, **kwargs)


def _log_warning(message: str, **kwargs) -> None:
    _log("WARNING", message, **kwargs)


def _log_error(message: str, **kwargs) -> None:
    _log("ERROR", message, **kwargs)


def lambda_handler(event, context):
    """Generate presigned URL for file upload."""
    correlation_id = context.aws_request_id if context else 'local'
    user_id = None
    try:
        # Extract user ID from Cognito claims (guaranteed by API GW authorizer)
        user_id = event['requestContext']['authorizer']['claims']['sub']

        # Parse request body
        body = json.loads(event.get('body') or '{}')
        filename = body.get('filename', '')
        content_type = body.get('contentType', '')

        _log_info(
            "Presigned URL requested",
            correlationId=correlation_id,
            userId=user_id,
            filename=filename,
            contentType=content_type,
        )

        # --- Validation 1: filename characters (path-traversal protection) ---
        # Reject any filename with directory separators or unsafe chars
        safe_filename = os.path.basename(filename)  # strip any path prefix
        if not safe_filename or not _SAFE_FILENAME_RE.match(safe_filename):
            _log_warning(
                "Invalid filename rejected",
                correlationId=correlation_id,
                userId=user_id,
                filename=filename,
            )
            return _response(400, {'error': 'Invalid filename'})

        # --- Validation 2: file extension ---
        ext = os.path.splitext(safe_filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            _log_warning(
                "Invalid extension rejected",
                correlationId=correlation_id,
                userId=user_id,
                ext=ext,
            )
            return _response(400, {
                'error': 'Invalid file type',
                'allowed': ALLOWED_EXTENSIONS,
            })

        # --- Validation 3: declared MIME type must match allowed list ---
        if content_type not in ALLOWED_MIME_TYPES:
            _log_warning(
                "Invalid MIME type rejected",
                correlationId=correlation_id,
                userId=user_id,
                contentType=content_type,
            )
            return _response(400, {
                'error': 'Invalid content type',
                'allowed': ALLOWED_MIME_TYPES,
            })

        # --- Validation 4: per-user upload quota ---
        # Count uploads in non-terminal states to prevent pipeline flooding
        if _active_upload_count(user_id) >= MAX_ACTIVE_UPLOADS:
            _log_warning(
                "Upload quota exceeded",
                correlationId=correlation_id,
                userId=user_id,
                limit=MAX_ACTIVE_UPLOADS,
            )
            return _response(429, {
                'error': (
                    'Too many active uploads. '
                    'Please wait for existing uploads to complete.'
                )
            })

        # Generate unique upload ID
        upload_id = str(uuid.uuid4())

        # S3 key: {userId}/{uploadId}/{safe_filename}
        # user_id from Cognito (trusted); upload_id is UUID (no traversal risk)
        s3_key = f"{user_id}/{upload_id}/{safe_filename}"

        # Generate presigned URL — enforce ContentType so client cannot swap it.
        # ContentLength is intentionally excluded: including it as a signed
        # param requires the PUT body to be EXACTLY that many bytes, causing
        # 403 for any real file smaller than the max. File size is enforced
        # by the quarantine validator after upload.
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': QUARANTINE_BUCKET,
                'Key': s3_key,
                'ContentType': content_type,
            },
            ExpiresIn=PRESIGNED_URL_EXPIRY,
        )

        # Record upload intent in DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.put_item(Item={
            'PK': f'USER#{user_id}',
            'SK': f'UPLOAD#{upload_id}',
            'uploadId': upload_id,
            'userId': user_id,
            'filename': safe_filename,
            'status': 'PENDING_UPLOAD',
            'createdAt': datetime.now(timezone.utc).isoformat(),
            'GSI1PK': 'STATUS#PENDING_UPLOAD',
            'GSI1SK': f'USER#{user_id}#{upload_id}',
        })

        _log_info(
            "Presigned URL generated",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
            s3Key=s3_key,
            expiresIn=PRESIGNED_URL_EXPIRY,
        )

        return _response(200, {
            'uploadUrl': presigned_url,
            'uploadId': upload_id,
            'expiresIn': PRESIGNED_URL_EXPIRY,
        })

    except Exception as e:
        _log_error(
            "Unexpected error",
            correlationId=correlation_id,
            userId=user_id,
            error=str(e),
        )
        return _response(500, {'error': 'Internal server error'})


def _active_upload_count(user_id: str) -> int:
    """
    Count uploads for this user that are still in-flight.
    Uses the GSI1 index to query by status prefix.
    In-flight statuses: PENDING_UPLOAD, VALIDATING, EXTRACTING_TEXT,
    QUEUED_FOR_AI, AI_PROCESSING, GENERATING.
    """
    in_flight = {
        'PENDING_UPLOAD', 'VALIDATING', 'VALIDATED',
        'EXTRACTING_TEXT', 'QUEUED_FOR_AI', 'AI_PROCESSING', 'GENERATING',
    }
    table = dynamodb.Table(DYNAMODB_TABLE)
    count = 0
    for status in in_flight:
        resp = table.query(
            IndexName='GSI1',
            KeyConditionExpression=(
                'GSI1PK = :gsi1pk AND begins_with(GSI1SK, :prefix)'
            ),
            ExpressionAttributeValues={
                ':gsi1pk': f'STATUS#{status}',
                ':prefix': f'USER#{user_id}#',
            },
            Select='COUNT',
        )
        count += resp.get('Count', 0)
        if count >= MAX_ACTIVE_UPLOADS:
            break
    return count


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
        'body': json.dumps(body),
    }
