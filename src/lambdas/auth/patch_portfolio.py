"""
Lambda: Manual Portfolio Content Patch

PATCH /portfolio/{userId}/content — Cognito-authenticated.

Supports two body shapes:

Shape A — scalar portfolioContent field:
  { "field": "bio", "value": "New bio text..." }

Shape B — parsedData section (array, string, or list):
  { "section": "projects", "data": [...] }
  { "section": "design_philosophy", "data": "string value" }
  { "section": "software_proficiency", "data": ["Python", "Go", ...] }

Allowlisted scalar fields (portfolioContent top-level):
  bio          — 1000 chars
  headline     — 200 chars
  uniqueValue  — 500 chars

Allowlisted array sections (parsedData keys):
  experience, projects, skills, education, certifications, achievements,
  awards, campaigns, financial_modeling, investment_portfolios

Allowlisted string sections (parsedData keys):
  design_philosophy  — 2000 chars

Allowlisted list sections (parsedData keys, list of strings):
  software_proficiency  — 50 items, 200 chars each

Security notes:
  - userId in path MUST match the Cognito token sub.
  - Only allowlisted fields/sections can be written.
  - String values capped per field to prevent oversized DynamoDB items.
  - ConditionExpression ensures the PORTFOLIO#current record exists.
  - The portfolio generator always HTML-escapes values before rendering.
  - IAM: UpdateItem scoped to USER#* leading keys only.
"""

import json
import os
from datetime import datetime, timezone
from urllib.parse import unquote

import boto3

dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PORTFOLIO_LAMBDA_NAME = os.environ.get('PORTFOLIO_LAMBDA_NAME')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

# ---------------------------------------------------------------------------
# Allowlists
# ---------------------------------------------------------------------------

# Shape A: scalar portfolioContent fields -> max character length
_ALLOWED_FIELDS: dict[str, int] = {
    'bio': 1000,
    'headline': 200,
    'uniqueValue': 500,
}

# Shape B: array sections in parsedData -> max item count
_ALLOWED_ARRAY_SECTIONS: dict[str, int] = {
    'experience': 50,
    'projects': 50,
    'skills': 30,
    'education': 20,
    'certifications': 50,
    'achievements': 50,
    'awards': 30,
    'campaigns': 30,
    'financial_modeling': 30,
    'investment_portfolios': 30,
}

# Shape B: string sections in parsedData -> max character length
_ALLOWED_STRING_SECTIONS: dict[str, int] = {
    'design_philosophy': 2000,
}

# Shape B: list-of-strings sections in parsedData -> (max items, max chars per item)
_ALLOWED_LIST_SECTIONS: dict[str, tuple] = {
    'software_proficiency': (50, 200),
}

# Shape B: object sections in parsedData -> allowed top-level keys
_ALLOWED_OBJECT_SECTIONS: dict[str, set] = {
    'profile': {'full_name', 'headline', 'email', 'phone', 'location', 'summary', 'social_links'},
}

# Max character length for any single string value within an array item
_MAX_ITEM_STRING_CHARS = 2000


# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "patch_portfolio",
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
# Validation helpers
# ---------------------------------------------------------------------------


def _sanitize_item(item: object) -> dict:
    """
    Recursively cap all string values in a dict item at _MAX_ITEM_STRING_CHARS.
    Raises ValueError for non-dict items.
    """
    if not isinstance(item, dict):
        raise ValueError('Each item in a section must be a JSON object')

    def _cap(val):
        if isinstance(val, str):
            return val[:_MAX_ITEM_STRING_CHARS]
        if isinstance(val, list):
            return [_cap(v) for v in val]
        if isinstance(val, dict):
            return {k: _cap(v) for k, v in val.items()}
        return val

    return {k: _cap(v) for k, v in item.items()}


# ---------------------------------------------------------------------------
# DynamoDB helpers
# ---------------------------------------------------------------------------


def _trigger_rebuild(path_user_id: str) -> None:
    """Invoke the portfolio generator to rebuild the draft asynchronously."""
    if PORTFOLIO_LAMBDA_NAME:
        lambda_client.invoke(
            FunctionName=PORTFOLIO_LAMBDA_NAME,
            InvocationType='Event',
            Payload=json.dumps({
                'userId': path_user_id,
                'trigger': 'manual_patch',
                'target': 'draft',
            }),
        )


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
        _log('WARNING', 'Patch auth mismatch', correlationId=correlation_id)
        return _response(403, {'error': 'Forbidden'})

    # ------------------------------------------------------------------
    # Parse body
    # ------------------------------------------------------------------
    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, ValueError):
        return _response(400, {'error': 'Invalid JSON body'})

    has_field = 'field' in body
    has_section = 'section' in body

    if not has_field and not has_section:
        return _response(400, {'error': 'Request must include either "field" or "section"'})

    if has_field and has_section:
        return _response(400, {'error': 'Provide either "field" or "section", not both'})

    if has_field:
        return _handle_field_patch(body, path_user_id, correlation_id)

    return _handle_section_patch(body, path_user_id, correlation_id)


def _handle_field_patch(body: dict, path_user_id: str, correlation_id: str) -> dict:
    """Existing behaviour: patch a scalar key in portfolioContent."""
    field = body.get('field', '')
    value = body.get('value')

    if field not in _ALLOWED_FIELDS:
        return _response(400, {
            'error': f'field must be one of: {", ".join(sorted(_ALLOWED_FIELDS))}'
        })

    if not isinstance(value, str):
        return _response(400, {'error': f'{field} must be a string'})

    max_len = _ALLOWED_FIELDS[field]
    if len(value) > max_len:
        return _response(400, {
            'error': f'{field} exceeds the {max_len}-character limit'
        })

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.update_item(
            Key={
                'PK': f'USER#{path_user_id}',
                'SK': 'PORTFOLIO#current',
            },
            UpdateExpression='SET #pc.#field = :value, #updatedAt = :updatedAt',
            ConditionExpression='attribute_exists(#pk)',
            ExpressionAttributeNames={
                '#pk': 'PK',
                '#pc': 'portfolioContent',
                '#field': field,
                '#updatedAt': 'updatedAt',
            },
            ExpressionAttributeValues={
                ':value': value,
                ':updatedAt': datetime.now(timezone.utc).isoformat(),
            },
        )

        _trigger_rebuild(path_user_id)

        _log('INFO', 'Portfolio field patched',
             correlationId=correlation_id,
             userId=path_user_id,
             field=field)

        return _response(200, {'field': field, 'value': value, 'status': 'saved'})

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _response(404, {'error': 'Portfolio not found. Generate a portfolio first.'})
    except Exception as e:
        _log('ERROR', 'Patch portfolio field error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})


_ALL_SECTION_KEYS = {
    'experience', 'projects', 'skills', 'education', 'certifications',
    'achievements', 'awards', 'campaigns', 'financial_modeling',
    'investment_portfolios', 'design_philosophy', 'software_proficiency',
}


def _handle_config_patch(data: object, path_user_id: str, correlation_id: str) -> dict:
    """
    Update sectionOrder and/or hiddenSections at the record root level.
    data = { sectionOrder?: string[], hiddenSections?: string[] }
    """
    if not isinstance(data, dict):
        return _response(400, {'error': 'config data must be an object'})

    update_parts = []
    expr_names = {'#pk': 'PK', '#updatedAt': 'updatedAt'}
    expr_values = {':updatedAt': datetime.now(timezone.utc).isoformat()}

    if 'sectionOrder' in data:
        order = data['sectionOrder']
        if not isinstance(order, list) or not all(isinstance(k, str) for k in order):
            return _response(400, {'error': 'sectionOrder must be an array of strings'})
        # Filter to known sections only to prevent arbitrary DynamoDB key injection
        order = [k for k in order if k in _ALL_SECTION_KEYS]
        update_parts.append('#sectionOrder = :sectionOrder')
        expr_names['#sectionOrder'] = 'sectionOrder'
        expr_values[':sectionOrder'] = order

    if 'hiddenSections' in data:
        hidden = data['hiddenSections']
        if not isinstance(hidden, list) or not all(isinstance(k, str) for k in hidden):
            return _response(400, {'error': 'hiddenSections must be an array of strings'})
        hidden = [k for k in hidden if k in _ALL_SECTION_KEYS]
        update_parts.append('#hiddenSections = :hiddenSections')
        expr_names['#hiddenSections'] = 'hiddenSections'
        expr_values[':hiddenSections'] = hidden

    if not update_parts:
        return _response(400, {'error': 'config data must include sectionOrder or hiddenSections'})

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.update_item(
            Key={
                'PK': f'USER#{path_user_id}',
                'SK': 'PORTFOLIO#current',
            },
            UpdateExpression='SET ' + ', '.join(update_parts) + ', #updatedAt = :updatedAt',
            ConditionExpression='attribute_exists(#pk)',
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

        _trigger_rebuild(path_user_id)

        _log('INFO', 'Portfolio config patched',
             correlationId=correlation_id,
             userId=path_user_id,
             fields=list(data.keys()))

        return _response(200, {'section': 'config', 'status': 'saved'})

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _response(404, {'error': 'Portfolio not found. Generate a portfolio first.'})
    except Exception as e:
        _log('ERROR', 'Patch portfolio config error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})


def _handle_section_patch(body: dict, path_user_id: str, correlation_id: str) -> dict:
    """New behaviour: replace a section in parsedData (or update root-level config)."""
    section = body.get('section', '')
    data = body.get('data')

    # 'config' is a special section stored at the record root (not parsedData)
    if section == 'config':
        return _handle_config_patch(data, path_user_id, correlation_id)

    all_sections = (
        set(_ALLOWED_ARRAY_SECTIONS)
        | set(_ALLOWED_STRING_SECTIONS)
        | set(_ALLOWED_LIST_SECTIONS)
        | set(_ALLOWED_OBJECT_SECTIONS)
    )
    if section not in all_sections:
        return _response(400, {
            'error': f'section must be one of: {", ".join(sorted(all_sections))}'
        })

    try:
        if section in _ALLOWED_ARRAY_SECTIONS:
            max_items = _ALLOWED_ARRAY_SECTIONS[section]
            if not isinstance(data, list):
                return _response(400, {'error': f'data for section "{section}" must be an array'})
            if len(data) > max_items:
                return _response(400, {
                    'error': f'section "{section}" exceeds the {max_items}-item limit'
                })
            sanitized_data = [_sanitize_item(item) for item in data]

        elif section in _ALLOWED_STRING_SECTIONS:
            max_len = _ALLOWED_STRING_SECTIONS[section]
            if not isinstance(data, str):
                return _response(400, {'error': f'data for section "{section}" must be a string'})
            sanitized_data = data[:max_len]

        elif section in _ALLOWED_LIST_SECTIONS:
            max_items, max_item_len = _ALLOWED_LIST_SECTIONS[section]
            if not isinstance(data, list):
                return _response(400, {'error': f'data for section "{section}" must be an array of strings'})
            if len(data) > max_items:
                return _response(400, {
                    'error': f'section "{section}" exceeds the {max_items}-item limit'
                })
            for item in data:
                if not isinstance(item, str):
                    return _response(400, {'error': f'Each item in "{section}" must be a string'})
            sanitized_data = [item[:max_item_len] for item in data]

        else:  # object section (e.g. profile)
            allowed_keys = _ALLOWED_OBJECT_SECTIONS[section]
            if not isinstance(data, dict):
                return _response(400, {'error': f'data for section "{section}" must be an object'})
            sanitized_data = {}
            for k, v in data.items():
                if k not in allowed_keys:
                    continue  # drop unknown keys silently
                if isinstance(v, str):
                    sanitized_data[k] = v[:500]
                elif isinstance(v, dict) and k == 'social_links':
                    _allowed_socials = {'linkedin', 'github', 'gitlab', 'portfolio', 'twitter'}
                    sanitized_data[k] = {
                        sk: str(sv)[:500]
                        for sk, sv in v.items()
                        if sk in _allowed_socials and isinstance(sv, str)
                    }
                # else: drop unexpected types silently

    except ValueError as ve:
        return _response(400, {'error': str(ve)})

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        table.update_item(
            Key={
                'PK': f'USER#{path_user_id}',
                'SK': 'PORTFOLIO#current',
            },
            UpdateExpression='SET parsedData.#section = :data, #updatedAt = :updatedAt',
            ConditionExpression='attribute_exists(#pk)',
            ExpressionAttributeNames={
                '#pk': 'PK',
                '#section': section,
                '#updatedAt': 'updatedAt',
            },
            ExpressionAttributeValues={
                ':data': sanitized_data,
                ':updatedAt': datetime.now(timezone.utc).isoformat(),
            },
        )

        _trigger_rebuild(path_user_id)

        item_count = len(sanitized_data) if isinstance(sanitized_data, list) else 1
        _log('INFO', 'Portfolio section patched',
             correlationId=correlation_id,
             userId=path_user_id,
             section=section,
             itemCount=item_count)

        return _response(200, {'section': section, 'status': 'saved'})

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _response(404, {'error': 'Portfolio not found. Generate a portfolio first.'})
    except Exception as e:
        _log('ERROR', 'Patch portfolio section error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})
