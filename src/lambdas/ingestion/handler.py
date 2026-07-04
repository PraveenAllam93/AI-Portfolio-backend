"""
Lambda: Resume Ingestion
Triggered when a file is promoted to the validated bucket.
Extracts text from the resume, classifies the profession, then PAUSES the
pipeline so the user can confirm/override the auto-detected profession and pick
a template. The start_generation Lambda resumes the pipeline (queues AI
processing) once the user has made a selection.

Security notes:
  - upload_id is read from S3 metadata (stamped by quarantine validator).
    If missing, the item is rejected — no silent fallback to 'unknown'.
  - The extracted text is written to the (trusted) validated bucket so the
    paused pipeline can resume without re-extracting. It is NOT stored in
    DynamoDB. Only the text length is recorded there for observability.
  - Profession classification runs on text already extracted from a VALIDATED
    file (on-doctrine: AI is never invoked on unvalidated input). It is
    advisory only — failure degrades to manual selection, never blocks.
  - Structured JSON logging with correlation ID for every entry.
"""

import json
import os
import hashlib
import boto3
from urllib.parse import unquote_plus
from datetime import datetime, timezone

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

VALIDATED_BUCKET = os.environ.get('VALIDATED_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
# Name of the classify_profession Lambda invoked synchronously after extraction.
CLASSIFY_LAMBDA_NAME = os.environ.get('CLASSIFY_LAMBDA_NAME')

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

        # Ignore our own extracted-text artifact ({uploadId}.txt). It is written
        # to this same bucket after extraction, which re-fires ObjectCreated.
        # The bucket notification has no suffix filter, so guard here to avoid
        # reprocessing (which would clobber AWAITING_SELECTION and error).
        if ext == '.txt':
            return {'statusCode': 200, 'body': 'Skipping extracted-text artifact'}

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

        # category / templateId are NOT read here: the pipeline pauses after
        # extraction so the user can confirm them. start_generation reads/writes
        # them when it resumes the pipeline.
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

        # Persist the extracted text to the (trusted) validated bucket so the
        # paused pipeline can resume without re-extracting. NOT stored in
        # DynamoDB (PII). start_generation reads it back by this key.
        text_key = f"{user_id}/{upload_id}.txt"
        s3_client.put_object(
            Bucket=VALIDATED_BUCKET,
            Key=text_key,
            Body=text.encode('utf-8'),
            ContentType='text/plain; charset=utf-8',
            Metadata={'uploadid': upload_id},
        )

        # Classify the profession (advisory) AND gate on "is this a resume?".
        # On-doctrine: runs on validated, server-extracted text. The same call
        # returns is_resume; failure fails open (is_resume=True) so a real
        # resume is never rejected because the classifier was unavailable.
        predicted_profession, predicted_confidence, is_resume = _classify_profession(
            text, correlation_id
        )

        # RESUME GATE: reject non-resumes here — before the pipeline pauses for
        # profession/template selection. The user should not be asked to pick a
        # template for a document we are about to reject, and AI must not parse
        # it. INVALID_DOCUMENT is a terminal status the frontend surfaces with a
        # human-readable message.
        if not is_resume:
            _log_warning(
                "Document is not a resume — rejecting before AI parsing",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
            )
            _update_status(user_id, upload_id, 'INVALID_DOCUMENT', {
                'failureMessage': (
                    'The uploaded document does not appear to be a resume. '
                    'Please upload a resume (CV) in PDF or DOCX format.'
                ),
            })
            return {'statusCode': 200, 'body': 'Rejected: not a resume'}

        # PAUSE the pipeline. The user confirms/overrides the profession and
        # picks a template; start_generation then queues AI processing.
        extra = {
            'rawTextLength': text_length,
            'rawTextS3Key': text_key,
            'contentHash': content_hash,
            'atsFailed': ats_failed,
            'predictedConfidence': predicted_confidence,
        }
        if predicted_profession:
            extra['predictedProfession'] = predicted_profession
        _update_status(user_id, upload_id, 'AWAITING_SELECTION', extra)

        _log_info(
            "Paused for profession selection",
            correlationId=correlation_id,
            userId=user_id,
            uploadId=upload_id,
            textLength=text_length,
            contentHash=content_hash,
            atsFailed=ats_failed,
            predictedProfession=predicted_profession,
            predictedConfidence=predicted_confidence,
        )
        return {'statusCode': 200, 'body': 'Awaiting profession selection'}

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


def _classify_profession(
    text: str, correlation_id: str
) -> tuple[str | None, int, bool]:
    """Synchronously invoke the classify_profession Lambda.

    Returns (profession|None, confidence:int, is_resume:bool). Never raises —
    classification is advisory, so any failure degrades to (None, 0) for the
    profession. The resume gate FAILS OPEN: any failure returns is_resume=True
    so we never reject a genuine resume because the classifier was unavailable.
    """
    if not CLASSIFY_LAMBDA_NAME:
        return None, 0, True
    try:
        resp = lambda_client.invoke(
            FunctionName=CLASSIFY_LAMBDA_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'resumeText': text,
                'correlationId': correlation_id,
            }),
        )
        payload = json.loads(resp['Payload'].read() or b'{}')
        # classify_profession returns a plain dict on success; if it errored at
        # the Lambda layer the payload may contain errorMessage instead.
        if not isinstance(payload, dict) or 'profession' not in payload:
            return None, 0, True
        profession = payload.get('profession') or None
        try:
            confidence = int(payload.get('confidence', 0) or 0)
        except (TypeError, ValueError):
            confidence = 0
        # Only a clearly-false verdict blocks; missing/garbled → fail open.
        is_resume = payload.get('isResume', True) is not False
        return profession, max(0, min(100, confidence)), is_resume
    except Exception as e:
        _log_error(
            "Profession classification failed — defaulting to manual selection",
            correlationId=correlation_id,
            error=str(e),
        )
        return None, 0, True


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
