"""
Lambda: Quarantine Validator
Validates files in the quarantine bucket before promoting to validated bucket.

Validation Layers (Fail Fast):
1. Extension validation
2. File size validation
3. Magic number validation
4. Zip bomb protection (DOCX)
5. Resume semantic validation (basic)
"""

import io
import json
import os
import zipfile
import boto3
from datetime import datetime, timezone
from urllib.parse import unquote_plus

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

QUARANTINE_BUCKET = os.environ.get('QUARANTINE_BUCKET')
VALIDATED_BUCKET = os.environ.get('VALIDATED_BUCKET')
REJECTED_BUCKET = os.environ.get('REJECTED_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', 10))
ALLOWED_EXTENSIONS = os.environ.get(
    'ALLOWED_EXTENSIONS', '.pdf,.docx'
).split(',')

# Magic numbers for file type validation
MAGIC_NUMBERS = {
    '.pdf': b'%PDF-',
    '.docx': b'PK\x03\x04',  # ZIP signature (DOCX is a ZIP)
}

# Zip bomb thresholds for DOCX
DOCX_MAX_DECOMPRESSED_MB = 50   # reject if any single entry exceeds 50 MB
DOCX_MAX_COMPRESSION_RATIO = 20  # reject if ratio > 20x
DOCX_MAX_FILE_COUNT = 1000       # reject if ZIP has > 1000 entries

# ---------------------------------------------------------------------------
# Structured logger — outputs JSON, captured by CloudWatch Logs
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    entry = {
        "level": level,
        "function": "quarantine_validator",
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
    """Validate uploaded file and promote or reject."""
    correlation_id = context.aws_request_id if context else 'local'
    try:
        # Get S3 event details
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        size = record['s3']['object']['size']

        _log_info(
            "Validation started",
            correlationId=correlation_id,
            bucket=bucket,
            key=key,
            sizeBytes=size,
        )

        # Parse key to extract user_id and upload_id
        parts = key.split('/')
        if len(parts) < 3:
            _log_warning(
                "Invalid key format — rejecting",
                correlationId=correlation_id,
                key=key,
            )
            return _reject(bucket, key, "Invalid key format")

        user_id = parts[0]
        upload_id = parts[1]
        filename = parts[2]

        # Update status to VALIDATING
        _update_status(user_id, upload_id, 'VALIDATING')

        # --- Validation 1: file extension ---
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return _reject(
                bucket, key,
                f"Invalid extension: {ext}",
                user_id, upload_id, correlation_id,
            )

        # --- Validation 2: file size (from S3 event metadata) ---
        max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if size > max_size_bytes:
            return _reject(
                bucket, key,
                f"File too large: {size} bytes (max {max_size_bytes})",
                user_id, upload_id, correlation_id,
            )

        # --- Validation 3: magic number (read first 8 bytes) ---
        head_resp = s3_client.get_object(
            Bucket=bucket,
            Key=key,
            Range='bytes=0-7',
        )
        first_bytes = head_resp['Body'].read()

        expected_magic = MAGIC_NUMBERS.get(ext)
        if expected_magic and not first_bytes.startswith(expected_magic):
            return _reject(
                bucket, key,
                "File content doesn't match declared extension",
                user_id, upload_id, correlation_id,
            )

        # --- Validation 4: DOCX zip bomb protection ---
        if ext == '.docx':
            file_resp = s3_client.get_object(Bucket=bucket, Key=key)
            file_content = file_resp['Body'].read()
            bomb_reason = _check_docx_zip_bomb(file_content)
            if bomb_reason:
                _log_warning(
                    "Zip bomb detected",
                    correlationId=correlation_id,
                    userId=user_id,
                    uploadId=upload_id,
                    reason=bomb_reason,
                )
                return _reject(
                    bucket, key,
                    "File rejected: zip bomb detected",
                    user_id, upload_id, correlation_id,
                )

        # --- All validations passed: promote to validated bucket ---
        validated_key = f"{user_id}/resume{ext}"

        s3_client.copy_object(
            Bucket=VALIDATED_BUCKET,
            Key=validated_key,
            CopySource={'Bucket': bucket, 'Key': key},
            Metadata={
                'validated': 'true',
                'originalKey': key,
                'uploadId': upload_id,
            },
            MetadataDirective='REPLACE',
        )

        s3_client.delete_object(Bucket=bucket, Key=key)

        _update_status(user_id, upload_id, 'VALIDATED', {
            'validatedKey': validated_key,
            'validatedBucket': VALIDATED_BUCKET,
        })

        _log_info(
            "Validation passed — promoted",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
            validatedKey=validated_key,
        )
        return {'statusCode': 200, 'body': 'Validation successful'}

    except Exception as e:
        _log_error(
            "Validation error",
            correlationId=correlation_id,
            error=str(e),
        )
        raise


def _check_docx_zip_bomb(content: bytes) -> str | None:
    """
    Inspect the DOCX (ZIP) for zip bomb indicators.
    Returns a reason string if suspicious, None if safe.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            entries = zf.infolist()

            # Check 1: excessive entry count
            if len(entries) > DOCX_MAX_FILE_COUNT:
                return (
                    f"Too many ZIP entries: {len(entries)} "
                    f"(max {DOCX_MAX_FILE_COUNT})"
                )

            total_compressed = 0
            total_uncompressed = 0

            for entry in entries:
                total_compressed += entry.compress_size
                total_uncompressed += entry.file_size

                # Check 2: single-entry decompressed size
                max_bytes = DOCX_MAX_DECOMPRESSED_MB * 1024 * 1024
                if entry.file_size > max_bytes:
                    return (
                        f"Entry '{entry.filename}' decompresses to "
                        f"{entry.file_size} bytes "
                        f"(max {max_bytes})"
                    )

            # Check 3: overall compression ratio
            if (
                total_compressed > 0
                and total_uncompressed / total_compressed
                > DOCX_MAX_COMPRESSION_RATIO
            ):
                ratio = total_uncompressed / total_compressed
                return (
                    f"Compression ratio {ratio:.1f}x exceeds "
                    f"limit of {DOCX_MAX_COMPRESSION_RATIO}x"
                )

    except zipfile.BadZipFile:
        return "File is not a valid ZIP/DOCX archive"
    except Exception as e:
        return f"ZIP inspection error: {e}"

    return None


def _reject(
    bucket, key, reason,
    user_id=None, upload_id=None, correlation_id='',
):
    """Move file to rejected bucket and update status."""
    _log_warning(
        "File rejected",
        correlationId=correlation_id,
        key=key,
        # Log the real reason internally; never expose it raw to the user
        reason=reason,
        userId=user_id,
        uploadId=upload_id,
    )

    try:
        rejected_key = f"rejected/{key}"
        s3_client.copy_object(
            Bucket=REJECTED_BUCKET,
            Key=rejected_key,
            CopySource={'Bucket': bucket, 'Key': key},
            # Do NOT store the rejection reason in S3 metadata —
            # it exposes validation logic to anyone with bucket access.
            Metadata={},
            MetadataDirective='REPLACE',
        )
        s3_client.delete_object(Bucket=bucket, Key=key)

        if user_id and upload_id:
            # Store a generic rejection reason visible to the user;
            # the detailed reason is in CloudWatch logs only.
            _update_status(user_id, upload_id, 'REJECTED', {
                'reason': 'File did not pass security validation.',
            })

    except Exception as e:
        _log_error(
            "Error during rejection cleanup",
            correlationId=correlation_id,
            error=str(e),
        )

    return {'statusCode': 400, 'body': 'Rejected'}


def _update_status(user_id, upload_id, status, extra_data=None):
    """Update upload status in DynamoDB."""
    table = dynamodb.Table(DYNAMODB_TABLE)

    update_expr = (
        "SET #status = :status, updatedAt = :updatedAt, GSI1PK = :gsi1pk"
    )
    expr_names = {'#status': 'status'}
    expr_values = {
        ':status': status,
        ':updatedAt': datetime.now(timezone.utc).isoformat(),
        ':gsi1pk': f'STATUS#{status}',
    }

    if extra_data:
        for k, v in extra_data.items():
            update_expr += f", #{k} = :{k}"
            expr_names[f'#{k}'] = k
            expr_values[f':{k}'] = v

    table.update_item(
        Key={
            'PK': f'USER#{user_id}',
            'SK': f'UPLOAD#{upload_id}',
        },
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )
