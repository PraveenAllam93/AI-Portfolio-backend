"""
Lambda: Get Presigned Upload URL
Generates short-lived PUT URLs for uploading to the quarantine bucket.
"""

import json
import os
import re
import uuid
import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from datetime import datetime, timezone

_AWS_REGION = os.environ.get('AWS_REGION', 'ap-south-1')
# Use the regional endpoint so presigned PUT URLs don't go through the global
# endpoint and get a 307 redirect that browsers can't follow with a body.
s3_client = boto3.client(
    's3',
    region_name=_AWS_REGION,
    endpoint_url=f'https://s3.{_AWS_REGION}.amazonaws.com',
    config=Config(s3={'addressing_style': 'virtual'}),
)
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
# Paused / pre-AI states that wait on the user (or on an upload that may never
# arrive) and have no natural timeout. Once older than STALE_UPLOAD_EXPIRY_HOURS
# they are treated as abandoned and no longer count toward the active quota, so
# forgotten uploads can never permanently consume a user's upload slots.
STALE_UPLOAD_EXPIRY_HOURS = float(
    os.environ.get('STALE_UPLOAD_EXPIRY_HOURS', 24)
)
_EXPIRABLE_STATUSES = {'PENDING_UPLOAD', 'AWAITING_SELECTION'}

# Sentinel stored when category/templateId are deferred until the user confirms
# the (auto-detected) profession after upload. start_generation overwrites these.
_PENDING = 'pending'

ALLOWED_CATEGORIES = {'software_engineer', 'designer', 'marketing', 'finance', 'civil_engineer', 'mechanical_engineer'}
ALLOWED_TEMPLATES = {'minimal', 'modern', 'bold', 'creative', 'aurora', 'nebula', 'luxury', 'executive', 'codex', 'neon', 'circuit', 'glitch', 'navy-gold', 'cosmos', 'retro', 'luxe', 'quantum', 'designer', 'designer-2', 'marketing', 'structura', 'blueprint', 'precision'}

# Safe filename: block path separators, null bytes, and Windows reserved chars.
# Allowlist approach was too strict (rejected spaces in names like "resume 1.pdf").
_SAFE_FILENAME_RE = re.compile(r'^[^/\\:*?"<>|\x00]{1,200}$')

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
        # category / templateId are DEFERRED in the new flow: the resume is
        # uploaded first, the pipeline extracts text + classifies the profession,
        # then the user confirms the profession/template and the start-generation
        # Lambda writes the real values. If the client omits them we store the
        # PENDING sentinel and skip their validation here.
        category = body.get('category', '') or _PENDING
        template_id = body.get('templateId', '') or _PENDING

        _log_info(
            "Presigned URL requested",
            correlationId=correlation_id,
            userId=user_id,
            filename=filename,
            contentType=content_type,
            category=category,
            templateId=template_id,
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

        # --- Validation 4: category (only if provided; deferred otherwise) ---
        if category != _PENDING and category not in ALLOWED_CATEGORIES:
            _log_warning(
                "Invalid category rejected",
                correlationId=correlation_id,
                userId=user_id,
                category=category,
            )
            return _response(400, {
                'error': 'Invalid category',
                'allowed': sorted(ALLOWED_CATEGORIES),
            })

        # --- Validation 5: templateId (only if provided; deferred otherwise) ---
        if template_id != _PENDING and template_id not in ALLOWED_TEMPLATES:
            _log_warning(
                "Invalid templateId rejected",
                correlationId=correlation_id,
                userId=user_id,
                templateId=template_id,
            )
            return _response(400, {
                'error': 'Invalid templateId',
                'allowed': sorted(ALLOWED_TEMPLATES),
            })

        # --- Validation 6: per-user upload quota ---
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
            'category': category,
            'templateId': template_id,
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
            'category': category,
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


def _parse_iso(value):
    """Parse a stored ISO-8601 timestamp; return None if missing/unparseable."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    # Treat naive timestamps as UTC so comparisons never raise.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _is_stale(item, now) -> bool:
    """
    True when a paused/pre-AI record has sat idle past the expiry window.
    Only EXPIRABLE statuses can be stale — genuinely processing uploads
    (QUEUED_FOR_AI / AI_PROCESSING / GENERATING) never expire.
    """
    if item.get('status') not in _EXPIRABLE_STATUSES:
        return False
    # Use the most recent activity timestamp; PENDING_UPLOAD has no updatedAt.
    last_touched = _parse_iso(item.get('updatedAt')) or _parse_iso(
        item.get('createdAt')
    )
    if last_touched is None:
        return False  # no timestamp — count it to stay safe
    age_hours = (now - last_touched).total_seconds() / 3600.0
    return age_hours >= STALE_UPLOAD_EXPIRY_HOURS


def _active_upload_count(user_id: str) -> int:
    """
    Count uploads for this user that are still in-flight.
    Queries the user's UPLOAD# records directly and checks the live status
    attribute — avoids relying on GSI1PK which is never updated after creation.

    Paused/pre-AI states that wait on the user (PENDING_UPLOAD,
    AWAITING_SELECTION) stop counting once older than STALE_UPLOAD_EXPIRY_HOURS,
    so abandoned uploads can never permanently hold a user's quota slots.
    """
    in_flight = {
        'PENDING_UPLOAD', 'VALIDATING', 'VALIDATED',
        'EXTRACTING_TEXT', 'AWAITING_SELECTION', 'QUEUED_FOR_AI',
        'AI_PROCESSING', 'GENERATING',
    }
    now = datetime.now(timezone.utc)
    table = dynamodb.Table(DYNAMODB_TABLE)
    count = 0
    query_kwargs = {
        'KeyConditionExpression': (
            Key('PK').eq(f'USER#{user_id}') & Key('SK').begins_with('UPLOAD#')
        ),
        'ProjectionExpression': '#s, createdAt, updatedAt',
        'ExpressionAttributeNames': {'#s': 'status'},
    }
    while True:
        resp = table.query(**query_kwargs)
        for item in resp.get('Items', []):
            if item.get('status') in in_flight and not _is_stale(item, now):
                count += 1
                if count >= MAX_ACTIVE_UPLOADS:
                    return count
        last_key = resp.get('LastEvaluatedKey')
        if not last_key:
            break
        query_kwargs['ExclusiveStartKey'] = last_key
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
