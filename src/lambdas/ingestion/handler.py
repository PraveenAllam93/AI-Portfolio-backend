"""
Lambda: Resume Ingestion
Triggered when a file is promoted to the validated bucket.
Extracts text from the resume and pushes a job to SQS for AI processing.

Security notes:
  - upload_id is read from S3 metadata (stamped by quarantine validator).
    If missing, the item is rejected — no silent fallback to 'unknown'.
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
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
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
    """Extract text from validated resume and queue for AI processing."""
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

        # Parse key: {user_id}/resume.{ext}
        parts = key.split('/')
        if len(parts) < 2:
            _log_warning(
                "Unexpected S3 key format — skipping",
                correlationId=correlation_id,
                key=key,
            )
            return {'statusCode': 400, 'body': 'Invalid key format'}

        user_id = parts[0]
        filename = parts[1]
        ext = os.path.splitext(filename)[1].lower()

        # Read upload_id from S3 metadata stamped by the quarantine validator.
        # Without this we cannot update the correct DynamoDB record — fail
        # loudly rather than silently writing to SK: UPLOAD#unknown.
        head = s3_client.head_object(Bucket=bucket, Key=key)
        upload_id = head.get('Metadata', {}).get('uploadid')

        if not upload_id:
            _log_warning(
                "Missing uploadId in S3 metadata — rejecting",
                correlationId=correlation_id,
                userId=user_id,
                key=key,
            )
            return {'statusCode': 400, 'body': 'Missing uploadId metadata'}

        _update_status(user_id, upload_id, 'EXTRACTING_TEXT')

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

        # Record text extraction — length only, NOT the text itself.
        # Storing resume text in the upload record would accumulate PII
        # unnecessarily; the text is already on S3 (encrypted) and passed
        # via SQS (encrypted, short-lived) to the AI Lambda.
        _update_status(user_id, upload_id, 'QUEUED_FOR_AI', {
            'rawTextLength': text_length,
        })

        sqs_client.send_message(
            QueueUrl=PROCESSING_QUEUE,
            MessageBody=json.dumps({
                'userId': user_id,
                'uploadId': upload_id,
                'resumeText': text,
                'filename': filename,
                's3Key': key,
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
        )
        return {'statusCode': 200, 'body': 'Queued for processing'}

    except Exception as e:
        _log_error(
            "Ingestion error",
            correlationId=correlation_id,
            error=str(e),
        )
        raise


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
    table = dynamodb.Table(DYNAMODB_TABLE)

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
