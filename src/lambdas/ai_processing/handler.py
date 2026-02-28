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
        try:
            message = json.loads(record['body'])
            user_id = message['userId']
            upload_id = message['uploadId']
            resume_text = message['resumeText']

            _log_info(
                "AI processing started",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
            )

            _update_status(user_id, upload_id, 'AI_PROCESSING')

            api_key = _get_openai_key()

            parsed_data = _parse_resume_with_openai(
                resume_text, api_key, correlation_id
            )

            if not parsed_data:
                _log_error(
                    "OpenAI returned no parsed data",
                    correlationId=correlation_id,
                    userId=user_id,
                    uploadId=upload_id,
                )
                _update_status(user_id, upload_id, 'AI_FAILED', {
                    'aiError': 'Failed to parse resume with AI',
                })
                continue

            portfolio_content = _generate_portfolio_content(
                parsed_data, api_key, correlation_id
            )

            _update_status(user_id, upload_id, 'AI_COMPLETE', {
                'parsedData': json.dumps(parsed_data),
                'portfolioContent': json.dumps(portfolio_content),
            })

            _trigger_portfolio_generation(
                user_id, upload_id, parsed_data, portfolio_content
            )

            _log_info(
                "AI processing complete",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
            )

        except Exception as e:
            # Log real error internally — DO NOT store str(e) in DynamoDB.
            # str(e) may contain API keys, stack traces, or internal paths.
            _log_error(
                "AI processing error",
                correlationId=correlation_id,
                userId=user_id,
                uploadId=upload_id,
                error=str(e),
            )
            if user_id and upload_id:
                _update_status(user_id, upload_id, 'AI_FAILED', {
                    # Generic message only — real error is in CloudWatch logs
                    'aiError': 'AI processing failed. Please try again.',
                })
            raise

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


def _parse_resume_with_openai(
    resume_text: str, api_key: str, correlation_id: str
) -> dict:
    """Parse resume text using OpenAI API."""
    try:
        import urllib.request

        prompt = f"""Parse the following resume and extract structured information.
Return a JSON object with the following structure:
{{
    "name": "Full Name",
    "title": "Professional Title",
    "email": "email@example.com",
    "phone": "phone number",
    "location": "City, Country",
    "summary": "Professional summary (2-3 sentences)",
    "skills": ["skill1", "skill2"],
    "experience": [
        {{
            "company": "Company Name",
            "title": "Job Title",
            "duration": "Start - End",
            "description": "Brief description",
            "highlights": ["achievement1", "achievement2"]
        }}
    ],
    "education": [
        {{
            "institution": "University Name",
            "degree": "Degree Name",
            "field": "Field of Study",
            "year": "Graduation Year"
        }}
    ],
    "certifications": ["cert1", "cert2"],
    "languages": ["language1"],
    "links": {{
        "linkedin": "url",
        "github": "url",
        "portfolio": "url"
    }}
}}

Resume text:
{resume_text[:8000]}

Return ONLY the JSON object, no additional text."""

        request_body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a resume parser. Extract information "
                        "accurately and return valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=request_body,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        content = result['choices'][0]['message']['content']

        # Strip markdown code fence if present
        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]

        return json.loads(content.strip())

    except Exception as e:
        _log_error(
            "OpenAI parsing error",
            correlationId=correlation_id,
            error=str(e),
        )
        return None


def _generate_portfolio_content(
    parsed_data: dict, api_key: str, correlation_id: str
) -> dict:
    """Generate enhanced portfolio content using OpenAI."""
    try:
        import urllib.request

        prompt = f"""Based on this parsed resume data, generate enhanced portfolio content.
Create engaging, professional descriptions for a portfolio website.

Input data:
{json.dumps(parsed_data, indent=2)}

Return a JSON object with:
{{
    "headline": "A compelling one-line headline",
    "bio": "An engaging 3-4 sentence bio for the about section",
    "skillCategories": {{
        "category1": ["skill1", "skill2"]
    }},
    "experienceHighlights": [
        {{
            "title": "Role at Company",
            "impact": "Key achievement or impact statement"
        }}
    ],
    "uniqueValue": "What makes this person unique (2 sentences)"
}}

Return ONLY the JSON object."""

        request_body = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional portfolio content writer."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1500,
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=request_body,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        content = result['choices'][0]['message']['content']

        if content.startswith('```'):
            content = content.split('```')[1]
            if content.startswith('json'):
                content = content[4:]

        return json.loads(content.strip())

    except Exception as e:
        _log_error(
            "Portfolio content generation error",
            correlationId=correlation_id,
            error=str(e),
        )
        return {}


def _trigger_portfolio_generation(
    user_id: str,
    upload_id: str,
    parsed_data: dict,
    portfolio_content: dict,
) -> None:
    """Store portfolio data and invoke portfolio generator Lambda."""
    table = dynamodb.Table(DYNAMODB_TABLE)
    table.put_item(Item={
        'PK': f'USER#{user_id}',
        'SK': 'PORTFOLIO#current',
        'userId': user_id,
        'uploadId': upload_id,
        'parsedData': parsed_data,
        'portfolioContent': portfolio_content,
        'version': 1,
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'status': 'GENERATING',
    })

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

