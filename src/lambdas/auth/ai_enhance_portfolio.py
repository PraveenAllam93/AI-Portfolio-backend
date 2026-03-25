"""
Lambda: AI Portfolio Field/Section Enhancer

POST /portfolio/{userId}/ai-enhance -- Cognito-authenticated.

Supports three body shapes:

Shape A -- scalar portfolioContent field (existing):
  { "field": "bio", "instruction": "Make it more concise" }

Shape B -- parsedData section item enhance:
  { "section": "experience", "itemIndex": 0, "enhanceField": "description", "instruction": "..." }

Shape C -- skills section enhance (full context):
  { "section": "skills", "instruction": "..." }

Responses:
  Shape A: { "field": "bio", "suggestedValue": "..." }
  Shape B: { "section": "experience", "itemIndex": 0, "enhanceField": "description", "suggestedValue": "..." }
  Shape C: { "section": "skills", "suggestedValue": [...skill_groups...] }

Security notes:
  - userId in path MUST match the Cognito token sub.
  - Only explicitly allowlisted fields/sections can be enhanced.
  - User instruction is capped at 300 chars to limit prompt injection surface.
  - AI response returned as suggestion only -- never stored without explicit user save.
"""

import json
import os
import urllib.request
import decimal
from urllib.parse import unquote

import boto3

dynamodb = boto3.resource('dynamodb')
secrets_client = boto3.client('secretsmanager')


class _DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns numeric types as Decimal; convert to int/float for JSON."""
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
OPENAI_SECRET_NAME = os.environ.get('OPENAI_SECRET_NAME')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

# Shape A: scalar portfolioContent fields
_ALLOWED_FIELDS: set = {'bio', 'headline', 'uniqueValue'}

_MAX_INSTRUCTION_CHARS = 300

_FIELD_MAX_SEND_CHARS: dict = {
    'bio': 1000,
    'headline': 200,
    'uniqueValue': 500,
}

_FIELD_LABELS: dict = {
    'bio': 'professional bio (3-4 sentences for the About section of a portfolio website)',
    'headline': 'one-line professional headline',
    'uniqueValue': 'unique value proposition (2 sentences describing what makes this person stand out)',
}

# Shape B: array section item fields that can be AI-enhanced
_SECTION_ITEM_FIELDS: dict = {
    'experience':            ['description', 'key_points'],
    'projects':              ['description', 'responsibilities', 'measurable_outcomes'],
    'achievements':          ['description'],
    'certifications':        ['name'],
    'education':             ['grade_or_score'],
    'awards':                ['title'],
    'campaigns':             ['performance_metrics'],
    'financial_modeling':    ['outcome'],
    'investment_portfolios': ['performance_return'],
}

# Shape C: context sections per category for skills enhancement
_SKILLS_CONTEXT_SECTIONS: dict = {
    'software_engineer': ['experience', 'projects', 'certifications'],
    'designer':          ['experience', 'projects', 'awards', 'certifications'],
    'marketing':         ['experience', 'campaigns', 'certifications'],
    'finance':           ['experience', 'financial_modeling', 'investment_portfolios', 'certifications'],
}
_SKILLS_CONTEXT_DEFAULT = ['experience', 'certifications']

_CONTEXT_MAX_CHARS = 2000

_openai_api_key = None


# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------


def _log(level, message, **kwargs):
    print(json.dumps({
        "level": level,
        "function": "ai_enhance_portfolio",
        "message": message,
        **kwargs,
    }))


# ---------------------------------------------------------------------------
# Response helper
# ---------------------------------------------------------------------------


def _response(status, body):
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body, cls=_DecimalEncoder),
    }


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------


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


def _call_openai(prompt, api_key, max_tokens=400):
    request_body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional portfolio content editor. "
                    "Follow user instructions precisely and return only the "
                    "requested text or JSON with no surrounding commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
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


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

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

    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, ValueError):
        return _response(400, {'error': 'Invalid JSON body'})

    instruction = str(body.get('instruction', '')).strip()
    if not instruction:
        return _response(400, {'error': 'instruction is required'})
    if len(instruction) > _MAX_INSTRUCTION_CHARS:
        return _response(400, {
            'error': f'instruction exceeds the {_MAX_INSTRUCTION_CHARS}-character limit'
        })

    if 'field' in body:
        return _handle_field_enhance(body, path_user_id, instruction, correlation_id)
    if 'section' in body:
        return _handle_section_enhance(body, path_user_id, instruction, correlation_id)

    return _response(400, {'error': 'Request must include either "field" or "section"'})


# ---------------------------------------------------------------------------
# Shape A: scalar field enhance
# ---------------------------------------------------------------------------


def _handle_field_enhance(body, path_user_id, instruction, correlation_id):
    field = body.get('field', '')

    if field not in _ALLOWED_FIELDS:
        return _response(400, {
            'error': f'field must be one of: {", ".join(sorted(_ALLOWED_FIELDS))}'
        })

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        result = table.get_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': 'PORTFOLIO#current'},
            ProjectionExpression='portfolioContent',
        )

        if 'Item' not in result:
            return _response(404, {'error': 'Portfolio not found. Generate a portfolio first.'})

        portfolio_content = result['Item'].get('portfolioContent') or {}
        current_value = str(portfolio_content.get(field) or '')

        max_chars = _FIELD_MAX_SEND_CHARS.get(field, 500)
        field_label = _FIELD_LABELS.get(field, field)

        prompt = (
            f"You are editing a portfolio website. "
            f"The current {field_label} reads:\n\n"
            f'"{current_value[:max_chars]}"\n\n'
            f"User instruction: {instruction}\n\n"
            f"Rewrite the {field_label} following the instruction precisely. "
            f"Return ONLY the rewritten text -- no quotes, no explanation, no prefix."
        )

        api_key = _get_openai_key()
        suggested = _call_openai(prompt, api_key, max_tokens=400)

        _log('INFO', 'AI enhance field complete',
             correlationId=correlation_id,
             userId=path_user_id,
             field=field)

        return _response(200, {'field': field, 'suggestedValue': suggested})

    except Exception as e:
        _log('ERROR', 'AI enhance field error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})


# ---------------------------------------------------------------------------
# Shape B/C: section enhance
# ---------------------------------------------------------------------------


def _handle_section_enhance(body, path_user_id, instruction, correlation_id):
    section = body.get('section', '')

    if section != 'skills' and section not in _SECTION_ITEM_FIELDS:
        allowed = sorted(list(_SECTION_ITEM_FIELDS.keys()) + ['skills'])
        return _response(400, {'error': f'section must be one of: {", ".join(allowed)}'})

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        result = table.get_item(
            Key={'PK': f'USER#{path_user_id}', 'SK': 'PORTFOLIO#current'},
            ProjectionExpression='parsedData, #cat',
            ExpressionAttributeNames={'#cat': 'category'},
        )

        if 'Item' not in result:
            return _response(404, {'error': 'Portfolio not found. Generate a portfolio first.'})

        parsed_data = result['Item'].get('parsedData') or {}
        category = result['Item'].get('category', 'software_engineer')

    except Exception as e:
        _log('ERROR', 'AI enhance fetch error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})

    if section == 'skills':
        return _enhance_skills(parsed_data, category, instruction, path_user_id, correlation_id)

    # Shape B: item field enhance
    enhance_field = body.get('enhanceField', '')
    if enhance_field not in _SECTION_ITEM_FIELDS[section]:
        allowed_fields = _SECTION_ITEM_FIELDS[section]
        return _response(400, {
            'error': f'enhanceField for "{section}" must be one of: {", ".join(allowed_fields)}'
        })

    item_index = body.get('itemIndex')
    if not isinstance(item_index, int) or item_index < 0:
        return _response(400, {'error': 'itemIndex must be a non-negative integer'})

    section_data = parsed_data.get(section, [])
    if not isinstance(section_data, list) or item_index >= len(section_data):
        return _response(400, {
            'error': f'itemIndex {item_index} is out of range for section "{section}"'
        })

    item = section_data[item_index]
    return _enhance_item(section, item, enhance_field, instruction, path_user_id, item_index, correlation_id)


def _enhance_item(section, item, enhance_field, instruction, path_user_id, item_index, correlation_id):
    # Identity for context
    identity_parts = []
    for key in ('role', 'company', 'title', 'name', 'campaign_name', 'model_type', 'portfolio_type', 'degree'):
        if item.get(key):
            identity_parts.append(str(item[key]))
    identity = ' -- '.join(identity_parts[:2]) if identity_parts else f'Item {item_index + 1}'

    current_value = item.get(enhance_field, '')
    is_list_field = isinstance(current_value, list)
    current_text = '\n'.join(str(v) for v in current_value) if is_list_field else str(current_value or '')
    field_label = enhance_field.replace('_', ' ')

    if is_list_field:
        prompt = (
            f"You are editing a portfolio website. "
            f"Context: {section} item -- {identity}\n\n"
            f"Current {field_label} (one point per line):\n{current_text[:1500]}\n\n"
            f"User instruction: {instruction}\n\n"
            f"Rewrite the {field_label} as concise bullet points (one per line). "
            f"Return ONLY the bullet points, one per line, no numbers, no dashes, no extra commentary."
        )
        max_tokens = 500
    else:
        prompt = (
            f"You are editing a portfolio website. "
            f"Context: {section} item -- {identity}\n\n"
            f"Current {field_label}:\n{current_text[:1500]}\n\n"
            f"User instruction: {instruction}\n\n"
            f"Rewrite the {field_label} following the instruction precisely. "
            f"Return ONLY the rewritten text -- no quotes, no explanation, no prefix."
        )
        max_tokens = 400

    try:
        api_key = _get_openai_key()
        suggested_text = _call_openai(prompt, api_key, max_tokens=max_tokens)

        if is_list_field:
            suggested_value = [line.strip() for line in suggested_text.split('\n') if line.strip()]
        else:
            suggested_value = suggested_text

        _log('INFO', 'AI enhance item complete',
             correlationId=correlation_id,
             userId=path_user_id,
             section=section,
             itemIndex=item_index,
             enhanceField=enhance_field)

        return _response(200, {
            'section': section,
            'itemIndex': item_index,
            'enhanceField': enhance_field,
            'suggestedValue': suggested_value,
        })

    except Exception as e:
        _log('ERROR', 'AI enhance item error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})


def _enhance_skills(parsed_data, category, instruction, path_user_id, correlation_id):
    current_skills = parsed_data.get('skills', [])
    current_skills_text = json.dumps(current_skills, ensure_ascii=False, cls=_DecimalEncoder)[:1500]

    context_sections = _SKILLS_CONTEXT_SECTIONS.get(category, _SKILLS_CONTEXT_DEFAULT)
    context_parts = []
    for ctx_section in context_sections:
        ctx_data = parsed_data.get(ctx_section)
        if ctx_data:
            ctx_text = json.dumps(ctx_data, ensure_ascii=False, cls=_DecimalEncoder)[:_CONTEXT_MAX_CHARS]
            context_parts.append(f"--- {ctx_section} ---\n{ctx_text}")

    context_block = '\n\n'.join(context_parts) if context_parts else 'No additional context.'

    prompt = (
        f"You are editing a portfolio website. The user wants to improve their skills section.\n\n"
        f"Current skills (JSON array of skill groups):\n{current_skills_text}\n\n"
        f"Context from other portfolio sections:\n{context_block}\n\n"
        f"User instruction: {instruction}\n\n"
        f"Return an improved skills section as a valid JSON array of skill group objects. "
        f'Each object must have "category" (string) and "skills" (array of strings). '
        f"Return ONLY the JSON array -- no explanation, no markdown code blocks."
    )

    try:
        api_key = _get_openai_key()
        suggested_text = _call_openai(prompt, api_key, max_tokens=800)

        clean = suggested_text.strip()
        if clean.startswith('```'):
            lines = clean.split('\n')
            clean = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
        suggested_groups = json.loads(clean)

        if not isinstance(suggested_groups, list):
            raise ValueError('Expected a JSON array')

        _log('INFO', 'AI enhance skills complete',
             correlationId=correlation_id,
             userId=path_user_id,
             category=category)

        return _response(200, {
            'section': 'skills',
            'suggestedValue': suggested_groups,
        })

    except (json.JSONDecodeError, ValueError) as parse_err:
        _log('ERROR', 'AI enhance skills JSON parse error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(parse_err))
        return _response(500, {'error': 'AI returned invalid skills format. Please try again.'})
    except Exception as e:
        _log('ERROR', 'AI enhance skills error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})
