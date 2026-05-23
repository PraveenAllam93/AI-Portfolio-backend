"""
Lambda: AI Processing
Triggered by SQS queue. Calls OpenAI to parse resume and generate portfolio
content.

IMPORTANT: This Lambda only processes VALIDATED input from the trusted pipeline.

Security notes:
  - Raw exception messages are logged to CloudWatch only — never stored in
    DynamoDB or returned to the user. The user-facing field is a generic
    string; the real error is keyed by correlationId in CloudWatch.
  - DynamoDB UpdateExpression always uses ExpressionAttributeNames (#alias)
    to avoid failures on reserved words (e.g. 'name', 'status', 'timestamp').
"""

import json
import os
import re
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')
lambda_client = boto3.client('lambda')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
OPENAI_SECRET_NAME = os.environ.get('OPENAI_SECRET_NAME')
PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
PORTFOLIO_LAMBDA_NAME = os.environ.get('PORTFOLIO_LAMBDA_NAME')

# Resume keyword heuristics for ATS pre-check
_RESUME_KEYWORDS = [
    'experience', 'education', 'skills', 'work', 'employment', 'objective',
    'summary', 'university', 'college', 'degree', 'bachelor', 'master',
    'engineer', 'developer', 'manager', 'analyst', 'intern', 'graduate',
    'certification', 'project', 'responsibilities', 'achievements', 'profile',
]
_RESUME_MIN_KEYWORD_HITS = 4

# HTTP status codes from OpenAI that are transient and warrant SQS retry
_TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}

# Cache OpenAI API key across warm invocations
_openai_api_key = None

# ---------------------------------------------------------------------------
# Structured logger — outputs JSON, captured by CloudWatch Logs
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    entry = {
        "level": level,
        "function": "ai_processing",
        "message": message,
    }
    entry.update(kwargs)
    print(json.dumps(entry))


def _log_info(message: str, **kwargs) -> None:
    _log("INFO", message, **kwargs)


def _log_error(message: str, **kwargs) -> None:
    _log("ERROR", message, **kwargs)


def lambda_handler(event, context):
    """Process resume with OpenAI and generate portfolio data."""
    correlation_id = context.aws_request_id if context else 'local'

    for record in event['Records']:
        user_id = None
        upload_id = None
        receive_count = int(record.get('attributes', {}).get('ApproximateReceiveCount', 1))
        is_final_attempt = receive_count >= int(os.environ.get('SQS_MAX_RECEIVE_COUNT', 3))

        try:
            message = json.loads(record['body'])
            user_id = message['userId']
            upload_id = message['uploadId']
            resume_text = message['resumeText']
            content_hash = message.get('contentHash')

            _log_info(
                "AI processing started",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                receiveCount=receive_count,
            )

            _update_status(user_id, upload_id, 'AI_PROCESSING')

            category = message.get('category', 'software_engineer')
            template_id = message.get('templateId', 'minimal')
            ats_failed = message.get('atsFailed', False)

            # Check dedup cache: if the same content hash was already processed,
            # reuse the parsed data instead of calling OpenAI again.
            parsed_data, portfolio_content = None, {}
            if content_hash:
                parsed_data, portfolio_content = _get_cached_result(content_hash, correlation_id)

            if parsed_data:
                _log_info(
                    "Using cached AI result (content hash match)",
                    correlationId=correlation_id,
                    userId=user_id,
                    uploadId=upload_id,
                    contentHash=content_hash,
                )
            else:
                api_key = _get_openai_key()

                # ATS check: if ingestion flagged low keyword density, ask OpenAI
                # to first verify this is actually a resume before full parsing.
                if ats_failed:
                    is_resume = _verify_is_resume(resume_text, api_key, correlation_id)
                    if not is_resume:
                        _log_error(
                            "ATS check failed — document is not a resume",
                            correlationId=correlation_id,
                            userId=user_id,
                            uploadId=upload_id,
                        )
                        _update_status(user_id, upload_id, 'INVALID_DOCUMENT', {
                            'aiError': (
                                'The uploaded document does not appear to be a resume. '
                                'Please upload a resume (CV) in PDF or DOCX format.'
                            ),
                        })
                        continue

                parsed_data, portfolio_content, is_transient_error = _process_resume_with_openai(
                    resume_text, api_key, correlation_id, category
                )

                if not parsed_data:
                    _log_error(
                        "OpenAI returned no parsed data",
                        correlationId=correlation_id,
                        userId=user_id,
                        uploadId=upload_id,
                        isTransient=is_transient_error,
                    )
                    if is_transient_error and not is_final_attempt:
                        # Raise so SQS retries — visibility timeout will return
                        # the message to the queue for the next attempt.
                        raise RuntimeError("Transient OpenAI error — will retry via SQS")
                    _update_status(user_id, upload_id, 'AI_FAILED', {
                        'aiError': 'Failed to parse resume with AI',
                    })
                    continue

                # Cache result by content hash to deduplicate future uploads.
                if content_hash:
                    _save_cached_result(
                        user_id, content_hash, parsed_data, portfolio_content, correlation_id
                    )

            _update_status(user_id, upload_id, 'AI_COMPLETE', {
                'parsedData': json.dumps(parsed_data),
                'portfolioContent': json.dumps(portfolio_content),
            })

            _trigger_portfolio_generation(
                user_id, upload_id, parsed_data, portfolio_content, category, template_id
            )

            _log_info(
                "AI processing complete",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
            )

        except Exception as e:
            # Log real error internally — DO NOT store str(e) in DynamoDB.
            _log_error(
                "AI processing error",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                error=str(e),
                isFinalAttempt=is_final_attempt,
            )
            if user_id and upload_id:
                try:
                    if is_final_attempt:
                        # All retries exhausted — mark terminal so the user sees an error.
                        _update_status(user_id, upload_id, 'AI_FAILED', {
                            'aiError': 'AI processing failed. Please try again.',
                        })
                    else:
                        # Leave status as AI_PROCESSING so the frontend shows "in progress"
                        # while SQS retries. Raise to trigger SQS retry.
                        raise
                except Exception as db_err:
                    _log_error(
                        "Failed to update AI_FAILED status",
                        correlationId=correlation_id,
                        userId=user_id,
                        uploadId=upload_id,
                        error=str(db_err),
                    )
                    raise
            else:
                raise  # Can't identify the record — let SQS route to DLQ

    return {'statusCode': 200, 'body': 'Processing complete'}


def _get_openai_key():
    """Get OpenAI API key from Secrets Manager (cached per warm container)."""
    global _openai_api_key
    if _openai_api_key:
        return _openai_api_key

    response = secrets_client.get_secret_value(SecretId=OPENAI_SECRET_NAME)
    secret = json.loads(response['SecretString'])
    _openai_api_key = (
        secret.get('api_key')
        or secret.get('OPENAI_API_KEY')
        or secret.get('openai_api_key')
    )
    return _openai_api_key


def _is_resume_text(text: str) -> bool:
    """Quick keyword heuristic — returns True if text looks like a resume."""
    lower = text.lower()
    hits = sum(1 for kw in _RESUME_KEYWORDS if kw in lower)
    return hits >= _RESUME_MIN_KEYWORD_HITS


def _verify_is_resume(resume_text: str, api_key: str, correlation_id: str) -> bool:
    """Ask OpenAI whether the document is a resume. Returns True if yes."""
    try:
        import urllib.request

        request_body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a document classifier. "
                        "Respond with exactly one word: YES or NO."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Is the following document a resume or CV? "
                        "Answer YES or NO only.\n\n"
                        f"{resume_text[:3000]}"
                    ),
                },
            ],
            "temperature": 0,
            "max_tokens": 5,
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=request_body,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        answer = result['choices'][0]['message']['content'].strip().upper()
        return answer.startswith('YES')

    except Exception as e:
        _log_error(
            "ATS verification error — assuming resume to avoid false positive",
            correlationId=correlation_id,
            error=str(e),
        )
        return True  # Fail open — don't block if we can't verify


def _get_cached_result(content_hash: str, correlation_id: str) -> tuple[dict | None, dict]:
    """Fetch previously parsed data by content hash. Returns (None, {}) on miss."""
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
        if not item:
            return None, {}
        parsed = item.get('parsedData')
        portfolio = item.get('portfolioContent', {})
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if isinstance(portfolio, str):
            portfolio = json.loads(portfolio)
        return parsed, portfolio
    except Exception as e:
        _log_error(
            "Cache lookup error — will call OpenAI",
            correlationId=correlation_id,
            error=str(e),
        )
        return None, {}


def _save_cached_result(
    user_id: str,
    content_hash: str,
    parsed_data: dict,
    portfolio_content: dict,
    correlation_id: str,
) -> None:
    """Persist parsed result keyed by content hash for future dedup hits."""
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.put_item(Item={
            'PK': f'CONTENT#{content_hash}',
            'SK': 'PARSED',
            'parsedBy': user_id,
            'parsedData': json.dumps(parsed_data),
            'portfolioContent': json.dumps(portfolio_content),
            'createdAt': datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        _log_error(
            "Failed to save cached result — non-fatal",
            correlationId=correlation_id,
            error=str(e),
        )


def _process_resume_with_openai(
    resume_text: str, api_key: str, correlation_id: str, category: str = 'software_engineer'
) -> tuple[dict | None, dict, bool]:
    """Parse resume AND generate portfolio content in a single OpenAI call.

    Returns (parsed_data, portfolio_content, is_transient_error).
    is_transient_error=True means the caller should allow SQS to retry.
    """
    try:
        import urllib.request
        from urllib.error import HTTPError
        from resume_models import get_category_config

        config = get_category_config(category)
        schema = json.dumps(config['schema_json'], indent=2)
        system_instruction = config['instruction']

        prompt = f"""You have two tasks. Process the resume below and return a single JSON object with exactly two top-level keys: "parsed" and "portfolio".

TASK 1 — "parsed": Extract structured resume data matching this JSON Schema exactly:
{schema}

TASK 2 — "portfolio": Generate engaging portfolio website content:
{{
    "headline": "A compelling one-line professional headline",
    "bio": "An engaging 3-4 sentence bio for the about section",
    "skillCategories": {{
        "category_name": ["skill1", "skill2"]
    }},
    "experienceHighlights": [
        {{
            "title": "Role at Company",
            "impact": "Key achievement or impact statement"
        }}
    ],
    "uniqueValue": "What makes this person unique (2 sentences)"
}}

Resume text:
{resume_text[:8000]}

Return ONLY the JSON object with "parsed" and "portfolio" keys. No additional text."""

        request_body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{system_instruction} "
                        "You are also a professional portfolio content writer. "
                        "Return valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 3500,
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=request_body,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode('utf-8'))
        except HTTPError as http_err:
            is_transient = http_err.code in _TRANSIENT_HTTP_CODES
            _log_error(
                "OpenAI HTTP error",
                correlationId=correlation_id,
                statusCode=http_err.code,
                isTransient=is_transient,
            )
            return None, {}, is_transient
        except Exception:
            # Socket timeout, connection reset, etc. are transient
            raise

        content = result['choices'][0]['message']['content']

        # Strip markdown code fence if present
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]

        combined = json.loads(content.strip())
        parsed_data = combined.get('parsed')
        portfolio_content = combined.get('portfolio', {})

        return parsed_data, portfolio_content, False

    except Exception as e:
        _log_error(
            "OpenAI processing error",
            correlationId=correlation_id,
            error=str(e),
        )
        # Unknown errors (JSON parse failure, socket timeout) are treated as
        # transient so SQS can retry them.
        return None, {}, True


def _trigger_portfolio_generation(
    user_id: str,
    upload_id: str,
    parsed_data: dict,
    portfolio_content: dict,
    category: str = 'software_engineer',
    template_id: str = 'minimal',
) -> None:
    """Store portfolio data and invoke portfolio generator Lambda."""
    table = dynamodb.Table(DYNAMODB_TABLE)
    table.put_item(Item={
        'PK': f'USER#{user_id}',
        'SK': 'PORTFOLIO#current',
        'userId': user_id,
        'uploadId': upload_id,
        'category': category,
        'templateId': template_id,
        'parsedData': parsed_data,
        'portfolioContent': portfolio_content,
        'version': 1,
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'status': 'GENERATING',
    })

    # Advance the upload record to GENERATING so the frontend progresses to step 4.
    # This must happen BEFORE invoking the portfolio Lambda to avoid a race condition
    # where the Lambda completes and sets COMPLETE before we set GENERATING.
    _update_status(user_id, upload_id, 'GENERATING')

    if PORTFOLIO_LAMBDA_NAME:
        lambda_client.invoke(
            FunctionName=PORTFOLIO_LAMBDA_NAME,
            InvocationType='Event',  # async
            Payload=json.dumps({
                'userId': user_id,
                'uploadId': upload_id,
            }),
        )
        _log_info(
            "Portfolio generation triggered",
            userId=user_id,
            uploadId=upload_id,
        )


def _update_status(user_id, upload_id, status, extra_data=None):
    """
    Update upload status in DynamoDB.

    ALWAYS uses ExpressionAttributeNames for every attribute name to:
      1. Prevent failures on DynamoDB reserved words ('name', 'status', etc.)
      2. Ensure consistent behaviour regardless of extra_data key names.
    """
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
            # Wrap every attribute name in an alias — no exceptions
            alias = f'#extra_{k}'
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

