"""
Lambda: AI Custom Section Classifier

POST /portfolio/{userId}/custom-section — Cognito-authenticated.

Takes free-form text describing content the user wants to add to their portfolio.
AI classifies: merge into an existing section, or create a new CustomSection?

Body:
  { "text": "...", "title": "Speaking Engagements" }   # title is optional hint

Response (AI suggests new custom section):
  {
    "action": "new_section",
    "section": {
      "section_id": "speaking_engagements",
      "title": "Speaking Engagements",
      "display_type": "timeline",
      "items": [{ "label": "...", "value": "...", "subtitle": "...", "tags": [...], "url": null }]
    }
  }

Response (AI suggests merging into existing section):
  {
    "action": "merge",
    "targetSection": "achievements",
    "item": { ...structured item matching that section's schema... }
  }

Nothing is saved — the caller must explicitly PATCH /portfolio/{userId}/content to persist.

Security notes:
  - userId in path MUST match the Cognito token sub.
  - text input capped at 2000 chars to limit prompt injection surface.
  - AI response returned as suggestion only — never stored without explicit user save.
"""

import json
import os
import re
import urllib.request
from urllib.parse import unquote

import boto3

dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
OPENAI_SECRET_NAME = os.environ.get('OPENAI_SECRET_NAME')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

_MAX_TEXT_CHARS = 2000
_MAX_TITLE_CHARS = 100

# Existing sections the AI can suggest merging into, with their schema hint
_MERGEABLE_SECTIONS = {
    'experience': 'company, role, start_date, end_date, description, key_points[]',
    'projects': 'title, description, responsibilities[], measurable_outcomes[], tech_stack[]',
    'achievements': 'title, description, year, achievement_url',
    'education': 'degree, field_of_study, institution, location, start_year, end_year, grade_or_score',
    'certifications': 'name, issuer, year, certification_url',
    'awards': 'title, awarding_body, year, award_url',
    'campaigns': 'campaign_name, campaign_type, channels_used[], budget, performance_metrics[]',
    'financial_modeling': 'model_type, tools_used[], outcome',
    'investment_portfolios': 'portfolio_type, assets_under_management, performance_return',
    'skills': 'category, skills[]',
}

_openai_api_key = None


def _log(level, message, **kwargs):
    print(json.dumps({
        "level": level,
        "function": "add_custom_section",
        "message": message,
        **kwargs,
    }))


def _response(status, body):
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body),
    }


def _get_openai_key():
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


def _call_openai(prompt, api_key, max_tokens=800):
    request_body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a portfolio content architect. "
                    "Analyse user-provided content and decide whether to merge it into an "
                    "existing portfolio section or create a new custom section. "
                    "Return ONLY valid JSON — no markdown, no commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": max_tokens,
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


def _slug(text):
    """Convert a title to a snake_case section_id."""
    s = re.sub(r'[^a-zA-Z0-9 ]', '', text.lower())
    s = re.sub(r'\s+', '_', s.strip())
    return s or 'custom_section'


def _build_prompt(text, title_hint, existing_section_names, category):
    sections_list = '\n'.join(
        f"  - {k}: {v}" for k, v in _MERGEABLE_SECTIONS.items()
        if k in existing_section_names or k in ('experience', 'achievements', 'projects')
    )

    title_line = f'User title hint: "{title_hint}"\n' if title_hint else ''

    return f"""You are building a portfolio for a {category} professional.

The user wants to add the following content to their portfolio:
---
{title_line}Content: {text}
---

Existing section types in this portfolio (schema shown for reference):
{sections_list}

Your task:
1. Decide if this content clearly belongs in one of the existing sections above.
2. If YES → return a "merge" response with a structured item matching that section's schema.
3. If NO (the content represents a genuinely new type of section) → return a "new_section" response.

For a NEW section, choose the best display_type:
- "timeline": chronological items with dates (talks, publications, volunteer work, events)
- "cards": project-like or achievement-like items (open source, portfolio pieces, case studies)
- "list": flat list of items (languages spoken, tools, hobbies, interests)

Return ONLY one of these two JSON shapes:

Shape A (merge into existing section):
{{
  "action": "merge",
  "targetSection": "<existing section key>",
  "item": {{ ...fields matching that section's schema, omit fields that are unknown... }}
}}

Shape B (create new custom section):
{{
  "action": "new_section",
  "section": {{
    "section_id": "<snake_case_id>",
    "title": "<Human Readable Title>",
    "display_type": "cards" | "list" | "timeline",
    "items": [
      {{
        "label": "<short title or name for this item>",
        "value": "<main description or content>",
        "subtitle": "<date range, organization, or role — omit if not applicable>",
        "tags": ["<optional tag>"],
        "url": "<url or null>"
      }}
    ]
  }}
}}

Rules:
- Only suggest merging if the content CLEARLY belongs (e.g., job experience → experience, certification → certifications).
- If the content straddles two sections or represents something new, prefer new_section.
- For new_section, extract ALL items from the user's text (there may be multiple entries described).
- All string fields must have a value or be omitted entirely (no empty strings, no null for strings).
- Return ONLY the JSON object — nothing else."""


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    path_params = event.get('pathParameters') or {}
    path_user_id = unquote(path_params.get('userId', ''))
    upload_id = unquote(path_params.get('uploadId', ''))
    token_sub = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )

    if not path_user_id or path_user_id != token_sub:
        _log('WARNING', 'add_custom_section auth mismatch', correlationId=correlation_id)
        return _response(403, {'error': 'Forbidden'})

    if not upload_id:
        return _response(400, {'error': 'Missing uploadId'})

    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, ValueError):
        return _response(400, {'error': 'Invalid JSON body'})

    text = str(body.get('text', '')).strip()
    if not text:
        return _response(400, {'error': '"text" is required'})
    if len(text) > _MAX_TEXT_CHARS:
        return _response(400, {'error': f'"text" exceeds the {_MAX_TEXT_CHARS}-character limit'})

    title_hint = str(body.get('title', '')).strip()[:_MAX_TITLE_CHARS]

    # Fetch existing parsedData to know which sections are populated
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        result = table.get_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': f'PORTFOLIO#{upload_id}'},
            ProjectionExpression='parsedData, #cat',
            ExpressionAttributeNames={'#cat': 'category'},
        )
        if 'Item' not in result:
            return _response(404, {'error': 'Portfolio not found. Generate a portfolio first.'})

        parsed_data = result['Item'].get('parsedData') or {}
        category = result['Item'].get('category', 'software_engineer')

    except Exception as e:
        _log('ERROR', 'add_custom_section fetch error',
             correlationId=correlation_id, userId=path_user_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})

    # Determine which sections are present
    existing_section_names = {k for k, v in parsed_data.items() if v}

    prompt = _build_prompt(text, title_hint, existing_section_names, category)

    try:
        api_key = _get_openai_key()
        raw = _call_openai(prompt, api_key, max_tokens=1000)

        clean = raw.strip()
        if clean.startswith('```'):
            lines = clean.split('\n')
            clean = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])

        result_json = json.loads(clean)

        if not isinstance(result_json, dict):
            raise ValueError('Expected a JSON object')

        action = result_json.get('action')
        if action not in ('merge', 'new_section'):
            raise ValueError(f'Unexpected action: {action}')

        # Validate/sanitize the new_section shape minimally
        if action == 'new_section':
            section = result_json.get('section', {})
            if not isinstance(section, dict):
                raise ValueError('section must be an object')
            # Ensure section_id is well-formed
            if not section.get('section_id'):
                section['section_id'] = _slug(section.get('title', 'custom_section'))
            if section.get('display_type') not in ('cards', 'list', 'timeline'):
                section['display_type'] = 'list'
            if not isinstance(section.get('items'), list):
                section['items'] = []
            result_json['section'] = section

        _log('INFO', 'add_custom_section complete',
             correlationId=correlation_id, userId=path_user_id,
             action=action, category=category)

        return _response(200, result_json)

    except (json.JSONDecodeError, ValueError) as parse_err:
        _log('ERROR', 'add_custom_section parse error',
             correlationId=correlation_id, userId=path_user_id, error=str(parse_err))
        return _response(500, {'error': 'AI returned invalid format. Please try again.'})
    except Exception as e:
        _log('ERROR', 'add_custom_section error',
             correlationId=correlation_id, userId=path_user_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})
