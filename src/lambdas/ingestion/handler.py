"""
Lambda: Resume Ingestion
Triggered when a file is promoted to the validated bucket.
Extracts text from the resume, writes it to S3, and pushes a lightweight
job reference to SQS for AI processing.

Security notes:
  - Raw resume text is NEVER placed in the SQS message body — SQS has a
    256 KB limit and the message is visible in CloudWatch/DLQ traces. Text
    is written to the validated S3 bucket and referenced by key only.
  - upload_id and content_hash are read from S3 metadata (stamped by the
    quarantine validator). Missing metadata causes a loud rejection — no
    silent fallback.
  - Deduplication: if the same user uploads identical file content (same
    SHA-256 hash), AI processing is skipped and the existing portfolio is
    re-linked. This prevents redundant OpenAI spend on identical resumes.
  - Raw resume text is NOT stored in DynamoDB to avoid PII accumulation.
    Only text length is recorded for observability.
  - Structured JSON logging with correlation ID for every entry.
"""

import json
import os
import boto3
from urllib.parse import unquote_plus
from datetime import datetime, timezone

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

VALIDATED_BUCKET = os.environ.get('VALIDATED_BUCKET')
MAIN_TABLE = os.environ.get('MAIN_TABLE')
PROCESSING_QUEUE = os.environ.get('PROCESSING_QUEUE')

# ---------------------------------------------------------------------------
# Structured logger — outputs JSON, captured by CloudWatch Logs
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    entry = {
        "level": level,
        "function": "resume_ingestion",
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
    """Extract text from validated resume, store in S3, and queue for AI."""
    correlation_id = context.aws_request_id if context else 'local'
    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])

        _log_info(
            "Ingestion started",
            correlationId=correlation_id,
            bucket=bucket,
            key=key,
        )

        # Key format (set by quarantine validator):
        #   {userId}/{uploadId}/{sha256_hash}.{ext}
        parts = key.split('/')
        if len(parts) < 3:
            _log_warning(
                "Unexpected S3 key format — skipping",
                correlationId=correlation_id,
                key=key,
            )
            return {'statusCode': 400, 'body': 'Invalid key format'}

        user_id = parts[0]
        upload_id = parts[1]
        filename = parts[2]
        ext = os.path.splitext(filename)[1].lower()

        # Ignore the resume-text.txt file that we write ourselves below —
        # the validated bucket trigger fires for ALL object creates.
        if filename == 'resume-text.txt':
            _log_info(
                "Skipping resume-text.txt trigger",
                correlationId=correlation_id,
                key=key,
            )
            return {'statusCode': 200, 'body': 'Skipped text file trigger'}

        # Read metadata stamped by the quarantine validator.
        head = s3_client.head_object(Bucket=bucket, Key=key)
        metadata = head.get('Metadata', {})
        upload_id_meta = metadata.get('uploadid')
        content_hash = metadata.get('contenthash')  # S3 lowercases keys

        if not upload_id_meta:
            _log_warning(
                "Missing uploadId in S3 metadata — rejecting",
                correlationId=correlation_id,
                userId=user_id,
                key=key,
            )
            return {'statusCode': 400, 'body': 'Missing uploadId metadata'}

        if not content_hash:
            _log_warning(
                "Missing contentHash in S3 metadata — rejecting",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                key=key,
            )
            return {'statusCode': 400, 'body': 'Missing contentHash metadata'}

        _update_status(user_id, upload_id, 'EXTRACTING_TEXT')

        # --- Deduplication check ---
        # If this user already processed an identical resume (same content
        # hash), skip AI and re-link the existing portfolio.
        existing = _check_content_dedup(user_id, content_hash)
        if existing:
            _log_info(
                "Duplicate resume content — reusing existing portfolio",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                existingUploadId=existing.get('uploadId'),
            )
            _update_status(user_id, upload_id, 'COMPLETE', {
                'deduplicated': True,
                'sourceUploadId': existing.get('uploadId', ''),
                'portfolioPath': existing.get('portfolioPath', ''),
            })
            return {
                'statusCode': 200,
                'body': 'Deduplicated — reused existing portfolio',
            }

        # --- Text extraction ---
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read()

        if ext == '.pdf':
            text = _extract_pdf_text(file_content, correlation_id)
        elif ext == '.docx':
            text = _extract_docx_text(file_content, correlation_id)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        if not text or len(text.strip()) < 100:
            _log_warning(
                "Insufficient text extracted",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                textLength=len(text) if text else 0,
            )
            _update_status(user_id, upload_id, 'FAILED', {
                'failureMessage': (
                    'Could not extract sufficient text from resume.'
                ),
            })
            return {'statusCode': 400, 'body': 'Insufficient text content'}

        text_length = len(text)

        # --- Write extracted text to S3 ---
        # Keeps SQS messages small and avoids exposing resume content in
        # queue traces, DLQ messages, or CloudWatch log snippets.
        # Path mirrors the resume: {userId}/{uploadId}/resume-text.txt
        s3_text_key = f"{user_id}/{upload_id}/resume-text.txt"
        s3_client.put_object(
            Bucket=VALIDATED_BUCKET,
            Key=s3_text_key,
            Body=text.encode('utf-8'),
            ContentType='text/plain; charset=utf-8',
        )

        # Record text extraction — length only, NOT the text itself.
        _update_status(user_id, upload_id, 'QUEUED_FOR_AI', {
            'rawTextLength': text_length,
            'contentHash': content_hash,
        })

        # Read the templateId chosen at upload time.
        # Falls back to 'modern' if the field is absent (old uploads).
        template_id = _get_template_id(user_id, upload_id)

        # SQS message carries only S3 key references — no raw resume text.
        sqs_client.send_message(
            QueueUrl=PROCESSING_QUEUE,
            MessageBody=json.dumps({
                'userId': user_id,
                'uploadId': upload_id,
                's3TextKey': s3_text_key,
                'contentHash': content_hash,
                'templateId': template_id,
                'filename': filename,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }),
            MessageAttributes={
                'userId': {
                    'DataType': 'String',
                    'StringValue': user_id,
                },
                'uploadId': {
                    'DataType': 'String',
                    'StringValue': upload_id,
                },
            },
        )

        _log_info(
            "Queued for AI processing",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
            textLength=text_length,
            s3TextKey=s3_text_key,
        )
        return {'statusCode': 200, 'body': 'Queued for processing'}

    except Exception as e:
        _log_error(
            "Ingestion error",
            correlationId=correlation_id,
            error=str(e),
        )
        raise


def _get_template_id(user_id: str, upload_id: str) -> str:
    """
    Read the templateId chosen at upload time from the UPLOAD DynamoDB record.
    Falls back to 'modern' if the field is absent (pre-template uploads).
    """
    table = dynamodb.Table(MAIN_TABLE)
    resp = table.get_item(
        Key={
            'PK': f'USER#{user_id}',
            'SK': f'UPLOAD#{upload_id}',
        },
        ProjectionExpression='templateId',
    )
    return resp.get('Item', {}).get('templateId', 'modern')


def _check_content_dedup(user_id: str, content_hash: str) -> dict | None:
    """
    Check if this user has already processed a resume with this content hash.
    Returns the existing record dict (with uploadId, portfolioPath) if found,
    or None if this is new content.

    DynamoDB record: PK=USER#{userId}, SK=CONTENT#{hash}
    """
    table = dynamodb.Table(MAIN_TABLE)
    resp = table.get_item(
        Key={
            'PK': f'USER#{user_id}',
            'SK': f'CONTENT#{content_hash}',
        },
        ProjectionExpression='uploadId, portfolioPath',
    )
    return resp.get('Item')


def _extract_pdf_text(content: bytes, correlation_id: str) -> str:
    """Extract text from PDF content using PyPDF2."""
    try:
        from io import BytesIO
        from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(content))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        _log_error(
            "PDF extraction error",
            correlationId=correlation_id,
            error=str(e),
        )
        return ""


def _extract_docx_text(content: bytes, correlation_id: str) -> str:
    """Extract text from DOCX content using basic XML parsing."""
    try:
        import io
        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(io.BytesIO(content)) as z:
            xml_content = z.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            ns = {
                'w': (
                    'http://schemas.openxmlformats.org/'
                    'wordprocessingml/2006/main'
                )
            }
            text_elements = tree.findall('.//w:t', ns)
            return ' '.join(e.text for e in text_elements if e.text)
    except Exception as e:
        _log_error(
            "DOCX extraction error",
            correlationId=correlation_id,
            error=str(e),
        )
        return ""


def _update_status(user_id, upload_id, status, extra_data=None):
    """Update upload status in DynamoDB."""
    table = dynamodb.Table(MAIN_TABLE)

    update_expr = (
        "SET #status = :status, #updatedAt = :updatedAt, #gsi1pk = :gsi1pk"
    )
    expr_names = {
        '#status': 'status',
        '#updatedAt': 'updatedAt',
        '#gsi1pk': 'GSI1PK',
    }
    expr_values = {
        ':status': status,
        ':updatedAt': datetime.now(timezone.utc).isoformat(),
        ':gsi1pk': f'STATUS#{status}',
    }

    if extra_data:
        for k, v in extra_data.items():
            alias = f'#{k}'
            update_expr += f", {alias} = :{k}"
            expr_names[alias] = k
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
