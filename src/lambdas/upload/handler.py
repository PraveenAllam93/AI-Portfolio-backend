"""
Lambda: Get Presigned Upload URL
Generates short-lived PUT URLs for uploading to the quarantine bucket.
"""

import json
import os
import re
import uuid
import boto3
from botocore.config import Config
from datetime import datetime, timezone

import entitlements as ent

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
# Maximum concurrent pending/active uploads per user (abuse protection).
# Distinct from the plan's portfolio limit: this caps how many uploads may be
# moving through the pipeline AT ONCE, regardless of tier.
MAX_ACTIVE_UPLOADS = int(os.environ.get('MAX_ACTIVE_UPLOADS', 5))
# The in-flight scan and its STALE_UPLOAD_EXPIRY_HOURS abandonment rule now live
# in entitlements.active_upload_ids(), shared with the plan gates.

# Sentinel stored when category/templateId are deferred until the user confirms
# the (auto-detected) profession after upload. start_generation overwrites these.
_PENDING = 'pending'

ALLOWED_CATEGORIES = {'software_engineer', 'designer', 'marketing', 'finance', 'civil_engineer', 'mechanical_engineer', 'accountant', 'hr', 'sales'}
# MUST stay in sync with the frontend TEMPLATE_META (templates/index.ts) and
# start_generation.py ALLOWED_TEMPLATES. Legacy ids that no longer exist in the
# renderer (minimal/modern/bold/creative/luxury/executive) have been removed —
# they silently fell back to neon at render time.
ALLOWED_TEMPLATES = {'aurora', 'nebula', 'codex', 'neon', 'circuit', 'glitch', 'navy-gold', 'cosmos', 'retro', 'luxe', 'quantum', 'voltage', 'nimbus', 'citrus', 'console', 'neural', 'flux', 'monolith', 'helix', 'orbit', 'iris', 'terminal', 'beacon', 'designer', 'designer-2', 'atelier', 'terra', 'ember', 'folio', 'obsidian', 'muse', 'prism', 'salon', 'marketing', 'momentum', 'apex', 'bloom', 'signal', 'vantage', 'canopy', 'structura', 'blueprint', 'precision', 'torque', 'ledger', 'sterling', 'meridian', 'cambria', 'verdant', 'haven', 'solace', 'quill', 'journal', 'atrium', 'clarion', 'cadence'}

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

        # Resolve the plan once — both the template gate and the portfolio gate
        # below need it.
        plan = ent.get_plan(user_id)

        # --- Validation 6: template must be available on the caller's plan ---
        # Only meaningful when the client sent a templateId; in the normal
        # deferred flow it is _PENDING here and start_generation applies the
        # same gate once the user actually picks one.
        if template_id != _PENDING and not ent.template_allowed(plan, template_id):
            _log_warning(
                "Paid template rejected for plan",
                correlationId=correlation_id,
                userId=user_id,
                templateId=template_id,
                plan=plan,
            )
            return ent.template_limit_response(plan, template_id)

        # --- Validation 7: per-plan total portfolio limit ---
        # Counts finished portfolios plus uploads already committed to
        # generation. Deliberately NOT every in-flight upload: one still sitting
        # on the profession/template screen has no dashboard entry, so counting
        # it told the user to "delete a portfolio" that they could not see.
        max_portfolios = ent.limits_for(plan).get('portfolios')
        if max_portfolios is not None:
            used = ent.used_portfolio_slots(user_id)
            if used >= max_portfolios:
                _log_warning(
                    "Portfolio limit reached",
                    correlationId=correlation_id,
                    userId=user_id,
                    plan=plan,
                    limit=max_portfolios,
                    used=used,
                )
                return ent.portfolio_limit_response(plan, used, max_portfolios)

        # --- Validation 8: concurrent-upload quota (abuse protection) ---
        # Independent of the plan limit above: this one caps how many uploads
        # may be in the pipeline AT ONCE, and exists to stop pipeline flooding.
        # It DOES count uploads awaiting selection — that is what keeps a user
        # from opening unlimited half-finished uploads.
        if len(ent.active_upload_ids(user_id)) >= MAX_ACTIVE_UPLOADS:
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
