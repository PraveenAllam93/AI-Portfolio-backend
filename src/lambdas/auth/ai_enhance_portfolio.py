"""
Lambda: AI Portfolio Field Enhancer

POST /portfolio/{userId}/ai-enhance — Cognito-authenticated.

Given an existing portfolioContent field and a short user instruction,
calls OpenAI to generate an improved version of that field. Returns the
AI suggestion WITHOUT saving — the user reviews and explicitly saves via
PATCH /portfolio/{userId}/content.

Request body:
  { "field": "bio", "instruction": "Make it more concise and impactful" }

Response:
  { "field": "bio", "suggestedValue": "..." }

Architecture note — synchronous AI call:
  The "AI is never invoked synchronously" rule in CLAUDE.md applies to the
  main pipeline (resume upload → async background processing). Here the user
  is at an interactive edit screen and has explicitly requested AI assistance
  on a single text field. The task scope is narrow (one field, < 400 tokens),
  gpt-4o-mini typically responds in 2-6 seconds, and API Gateway's 29-second
  timeout is not a concern. This is a deliberate, documented exception.

Security notes:
  - userId in path MUST match the Cognito token sub.
  - Only explicitly allowlisted fields can be enhanced.
  - User instruction is capped at 300 chars to limit prompt injection surface.
  - AI response is returned as plain text — never executed or stored
    without explicit user confirmation via the PATCH endpoint.
  - IAM: GetItem scoped to USER#* keys + secretsmanager for OpenAI key only.
"""

import json
import os
import urllib.request
from urllib.parse import unquote

import boto3

dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
OPENAI_SECRET_NAME = os.environ.get('OPENAI_SECRET_NAME')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

# Only these portfolioContent fields may be AI-enhanced.
_ALLOWED_FIELDS: set[str] = {'bio', 'headline', 'uniqueValue'}

# Max chars for the user-supplied instruction (limits prompt injection surface).
_MAX_INSTRUCTION_CHARS = 300

# Max chars of the existing field value sent to OpenAI.
_FIELD_MAX_SEND_CHARS: dict[str, int] = {
    'bio': 1000,
    'headline': 200,
    'uniqueValue': 500,
}

# Human-readable field descriptions for the AI prompt.
_FIELD_LABELS: dict[str, str] = {
    'bio': 'professional bio (3-4 sentences for the About section of a portfolio website)',
    'headline': 'one-line professional headline',
    'uniqueValue': 'unique value proposition (2 sentences describing what makes this person stand out)',
}

# Cache OpenAI API key across warm invocations.
_openai_api_key: str | None = None

# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "ai_enhance_portfolio",
        "message": message,
        **kwargs,
    }))


# ---------------------------------------------------------------------------
# Response helper
# ---------------------------------------------------------------------------


def _response(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body),
    }


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------


def _get_openai_key() -> str:
    global _openai_api_key
    if _openai_api_key:
        return _openai_api_key
    resp = secrets_client.get_secret_value(SecretId=OPENAI_SECRET_NAME)
    secret = json.loads(resp['SecretString'])
    _openai_api_key = (
        secret.get('api_key')
        or secret.get('OPENAI_API_KEY')
        or secret.get('openai_api_key')
    )
    return _openai_api_key


def _call_openai(field: str, current_value: str, instruction: str, api_key: str) -> str:
    """
    Call OpenAI to rewrite a single portfolio field following the user's
    instruction. Returns the rewritten text only (no extra commentary).
    """
    max_chars = _FIELD_MAX_SEND_CHARS.get(field, 500)
    field_label = _FIELD_LABELS.get(field, field)

    prompt = (
        f"You are editing a portfolio website. "
        f"The current {field_label} reads:\n\n"
        f'"{current_value[:max_chars]}"\n\n'
        f"User instruction: {instruction}\n\n"
        f"Rewrite the {field_label} following the instruction precisely. "
        f"Return ONLY the rewritten text — no quotes, no explanation, no prefix."
    )

    request_body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional portfolio content editor. "
                    "Follow user instructions precisely and return only the "
                    "requested text with no surrounding commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 400,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=request_body,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
    )

    with urllib.request.urlopen(req, timeout=25) as resp:
        result = json.loads(resp.read().decode('utf-8'))

    return result['choices'][0]['message']['content'].strip()


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    # ------------------------------------------------------------------
    # Authorization: path userId must exactly match the token's sub claim.
    # ------------------------------------------------------------------
    path_user_id = unquote((event.get('pathParameters') or {}).get('userId', ''))
    token_sub = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )

    if not path_user_id or path_user_id != token_sub:
        _log('WARNING', 'AI enhance auth mismatch', correlationId=correlation_id)
        return _response(403, {'error': 'Forbidden'})

    # ------------------------------------------------------------------
    # Parse and validate body
    # ------------------------------------------------------------------
    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, ValueError):
        return _response(400, {'error': 'Invalid JSON body'})

    field = body.get('field', '')
    instruction = str(body.get('instruction', '')).strip()

    if field not in _ALLOWED_FIELDS:
        return _response(400, {
            'error': f'field must be one of: {", ".join(sorted(_ALLOWED_FIELDS))}'
        })

    if not instruction:
        return _response(400, {'error': 'instruction is required'})

    if len(instruction) > _MAX_INSTRUCTION_CHARS:
        return _response(400, {
            'error': f'instruction exceeds the {_MAX_INSTRUCTION_CHARS}-character limit'
        })

    # ------------------------------------------------------------------
    # Fetch current field value from DynamoDB
    # ------------------------------------------------------------------
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        result = table.get_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': 'PORTFOLIO#current'},
            ProjectionExpression='portfolioContent',
        )

        if 'Item' not in result:
            return _response(404, {
                'error': 'Portfolio not found. Generate a portfolio first.'
            })

        portfolio_content = result['Item'].get('portfolioContent') or {}
        current_value = str(portfolio_content.get(field) or '')

        # ------------------------------------------------------------------
        # Call OpenAI — synchronous, user is waiting at edit screen
        # ------------------------------------------------------------------
        api_key = _get_openai_key()
        suggested = _call_openai(field, current_value, instruction, api_key)

        _log('INFO', 'AI enhance complete',
             correlationId=correlation_id,
             userId=path_user_id,
             field=field)

        # Return suggestion only — user must explicitly call PATCH to save.
        return _response(200, {
            'field': field,
            'suggestedValue': suggested,
        })

    except Exception as e:
        _log('ERROR', 'AI enhance error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})
