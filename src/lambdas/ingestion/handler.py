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
import hashlib
import boto3
from urllib.parse import unquote_plus
from datetime import datetime, timezone

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

VALIDATED_BUCKET = os.environ.get('VALIDATED_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PROCESSING_QUEUE = os.environ.get('PROCESSING_QUEUE')
PORTFOLIO_LAMBDA_NAME = os.environ.get('PORTFOLIO_LAMBDA_NAME')

# Minimum resume keyword hits to pass the ATS pre-screen.
_RESUME_KEYWORDS = [
    'experience', 'education', 'skills', 'work', 'employment', 'objective',
    'summary', 'university', 'college', 'degree', 'bachelor', 'master',
    'engineer', 'developer', 'manager', 'analyst', 'intern', 'graduate',
    'certification', 'project', 'responsibilities', 'profile',
]
_RESUME_MIN_KEYWORD_HITS = 4

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

        # Read category and templateId from the DynamoDB UPLOAD record.
        table = dynamodb.Table(DYNAMODB_TABLE)
        upload_record = table.get_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': f'UPLOAD#{upload_id}',
            },
            ProjectionExpression='category, templateId',
        )
        upload_item = upload_record.get('Item', {})
        category = upload_item.get('category', 'software_engineer')
        template_id = upload_item.get('templateId', 'minimal')

        _update_status(user_id, upload_id, 'EXTRACTING_TEXT')

        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read()

        if ext == '.pdf':
            text = _extract_pdf_text(file_content, correlation_id)
        elif ext == '.docx':
            text = _extract_docx_text(file_content, correlation_id)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        # OCR fallback: if PyPDF2 extracted very little text the PDF is likely
        # image-based. Attempt Tesseract OCR if the layer is available.
        if len((text or '').strip()) < 200 and ext == '.pdf':
            ocr_text = _extract_pdf_ocr(file_content, correlation_id)
            if ocr_text and len(ocr_text.strip()) > len((text or '').strip()):
                _log_info(
                    "OCR extracted more text than PyPDF2 — using OCR result",
                    correlationId=correlation_id,
                    userId=user_id,
                    uploadId=upload_id,
                    ocrTextLength=len(ocr_text),
                )
                text = ocr_text

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
                    'Could not extract sufficient text from resume. '
                    'If your PDF is image-based, please export as text-based PDF.'
                ),
            })
            return {'statusCode': 400, 'body': 'Insufficient text content'}

        text_length = len(text)

        # Content hash: allows dedup and cache reuse in ai_processing.
        content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

        # ATS pre-screen: check if the document looks like a resume.
        # ai_processing will do a deeper OpenAI-based check if this fails.
        ats_failed = not _passes_ats_check(text)
        if ats_failed:
            _log_warning(
                "ATS pre-screen failed — document may not be a resume",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
            )

        # Dedup: check if this exact content has been processed before.
        cached = _get_cached_result(content_hash, correlation_id)
        if cached:
            _log_info(
                "Content hash match — reusing cached AI result",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                contentHash=content_hash,
            )
            _update_status(user_id, upload_id, 'AI_COMPLETE', {
                'parsedData': json.dumps(cached['parsedData']),
                'portfolioContent': json.dumps(cached['portfolioContent']),
                'rawTextLength': text_length,
            })
            # Trigger portfolio generation directly with the cached data.
            _trigger_portfolio_generation(
                user_id, upload_id, category, template_id, correlation_id
            )
            return {'statusCode': 200, 'body': 'Used cached result'}

        # Record text extraction — length only, NOT the text itself.
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
                'category': category,
                'templateId': template_id,
                'contentHash': content_hash,
                'atsFailed': ats_failed,
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
                'category': {
                    'DataType': 'String',
                    'StringValue': category,
                },
            },
        )

        _log_info(
            "Queued for AI processing",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
            textLength=text_length,
            contentHash=content_hash,
            atsFailed=ats_failed,
        )
        return {'statusCode': 200, 'body': 'Queued for processing'}

    except Exception as e:
        _log_error(
            "Ingestion error",
            correlationId=correlation_id,
            error=str(e),
        )
        raise


def _passes_ats_check(text: str) -> bool:
    """Returns True if the text has enough resume indicators."""
    lower = text.lower()
    hits = sum(1 for kw in _RESUME_KEYWORDS if kw in lower)
    return hits >= _RESUME_MIN_KEYWORD_HITS


def _get_cached_result(content_hash: str, correlation_id: str) -> dict | None:
    """Return cached parsedData+portfolioContent dict, or None on miss."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        resp = table.get_item(
            Key={
                'PK': f'CONTENT#{content_hash}',
                'SK': 'PARSED',
            },
            ProjectionExpression='parsedData, portfolioContent',
        )
        item = resp.get('Item')
        if not item or 'parsedData' not in item:
            return None
        parsed = item['parsedData']
        portfolio = item.get('portfolioContent', '{}')
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if isinstance(portfolio, str):
            portfolio = json.loads(portfolio)
        return {'parsedData': parsed, 'portfolioContent': portfolio}
    except Exception as e:
        _log_error(
            "Dedup cache lookup error — will queue for AI",
            correlationId=correlation_id,
            error=str(e),
        )
        return None


def _trigger_portfolio_generation(
    user_id: str,
    upload_id: str,
    category: str,
    template_id: str,
    correlation_id: str,
) -> None:
    """Invoke portfolio generator Lambda asynchronously (dedup fast-path)."""
    if not PORTFOLIO_LAMBDA_NAME:
        return
    try:
        lambda_client.invoke(
            FunctionName=PORTFOLIO_LAMBDA_NAME,
            InvocationType='Event',
            Payload=json.dumps({'userId': user_id, 'uploadId': upload_id}),
        )
        _log_info(
            "Portfolio generation triggered (dedup fast-path)",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
        )
    except Exception as e:
        _log_error(
            "Failed to trigger portfolio generation",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
            error=str(e),
        )


def _extract_pdf_ocr(content: bytes, correlation_id: str) -> str:
    """OCR fallback for image-based PDFs using Tesseract.

    Requires the Tesseract Lambda layer (tesseract binary + pytesseract +
    pdf2image + poppler). Returns empty string if the layer is not available.
    Build script: scripts/build_tesseract_layer.sh
    """
    try:
        import pytesseract
        import pdf2image
        from io import BytesIO

        images = pdf2image.convert_from_bytes(content, dpi=200)
        pages_text = []
        for img in images:
            page_text = pytesseract.image_to_string(img, lang='eng')
            if page_text:
                pages_text.append(page_text)
        return '\n'.join(pages_text)
    except ImportError:
        _log_info(
            "Tesseract layer not available — skipping OCR",
            correlationId=correlation_id,
        )
        return ''
    except Exception as e:
        _log_error(
            "OCR extraction error",
            correlationId=correlation_id,
            error=str(e),
        )
        return ''


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
