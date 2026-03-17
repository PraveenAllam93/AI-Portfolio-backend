"""
Lambda: Manual Portfolio Content Patch

PATCH /portfolio/{userId}/content — Cognito-authenticated.

Allows the portfolio owner to overwrite a specific text field in their
portfolioContent, or change the active template. Both trigger an async
portfolio HTML rebuild.

Request body (one of):
  { "field": "bio", "value": "New bio text..." }
  { "templateId": "bold" }

Allowlisted fields and their max lengths (portfolioContent top-level only):
  bio          — 1000 chars
  headline     — 200 chars
  uniqueValue  — 500 chars

Security notes:
  - userId in path MUST match the Cognito token sub — enforced before any
    DynamoDB access. Cross-user writes are impossible at the code level.
  - Only fields in _ALLOWED_FIELDS can be written — no arbitrary key injection.
  - Value length is capped per field to prevent oversized DynamoDB items.
  - templateId validated against VALID_TEMPLATE_IDS frozenset.
  - ConditionExpression ensures the PORTFOLIO#current record exists before
    any update is applied (prevents phantom creates).
  - The portfolio generator always HTML-escapes values before rendering,
    so no raw user input ever reaches the HTML as unescaped text.
  - IAM for this Lambda: UpdateItem scoped to USER#* leading keys only.
"""

import json
import os
from datetime import datetime, timezone
from urllib.parse import unquote

import boto3

dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

MAIN_TABLE = os.environ.get('MAIN_TABLE')
PORTFOLIO_LAMBDA_NAME = os.environ.get('PORTFOLIO_LAMBDA_NAME')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

# Only these portfolioContent keys may be patched — field → max length.
_ALLOWED_FIELDS: dict[str, int] = {
    'bio': 1000,
    'headline': 200,
    'uniqueValue': 500,
}

# Template IDs — keep in sync with portfolio/handler.py, upload/handler.py
VALID_TEMPLATE_IDS = frozenset({
    'modern', 'minimal', 'bold', 'creative', 'executive',
    'nebula', 'aurora', 'luxury',
})


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
# Handler
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    # ------------------------------------------------------------------
    # Authorization: path userId must exactly match the token's sub claim.
    # ------------------------------------------------------------------
    path_params = event.get('pathParameters') or {}
    path_user_id = unquote(path_params.get('userId', ''))
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

    has_template = 'templateId' in body
    has_field = 'field' in body

    if has_template and has_field:
        return _response(400, {
            'error': 'Provide either templateId or field+value, not both'
        })

    if not has_template and not has_field:
        valid = ', '.join(sorted(_ALLOWED_FIELDS))
        return _response(400, {
            'error': f'Provide templateId or field (one of: {valid})'
        })

    # ------------------------------------------------------------------
    # Route: templateId change
    # ------------------------------------------------------------------
    if has_template:
        return _patch_template(body, path_user_id, correlation_id)

    # ------------------------------------------------------------------
    # Route: portfolioContent field patch
    # ------------------------------------------------------------------
    return _patch_field(body, path_user_id, correlation_id)


# ---------------------------------------------------------------------------
# Template switch
# ---------------------------------------------------------------------------


def _patch_template(body: dict, user_id: str, correlation_id: str) -> dict:
    template_id = body.get('templateId', '')
    if template_id not in VALID_TEMPLATE_IDS:
        valid = ', '.join(sorted(VALID_TEMPLATE_IDS))
        return _response(400, {
            'error': f'templateId must be one of: {valid}'
        })

    try:
        table = dynamodb.Table(MAIN_TABLE)
        table.update_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PORTFOLIO#current',
            },
            UpdateExpression=(
                'SET templateId = :tid, #updatedAt = :updatedAt'
            ),
            ConditionExpression='attribute_exists(#pk)',
            ExpressionAttributeNames={
                '#pk': 'PK',
                '#updatedAt': 'updatedAt',
            },
            ExpressionAttributeValues={
                ':tid': template_id,
                ':updatedAt': datetime.now(timezone.utc).isoformat(),
            },
        )

        _trigger_rebuild(user_id)

        _log('INFO', 'Template updated',
             correlationId=correlation_id,
             userId=user_id,
             templateId=template_id)

        return _response(200, {
            'templateId': template_id,
            'status': 'saved',
        })

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _response(404, {
            'error': 'Portfolio not found. Generate a portfolio first.'
        })
    except Exception as e:
        _log('ERROR', 'Patch template error',
             correlationId=correlation_id,
             userId=user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})


# ---------------------------------------------------------------------------
# Content field patch
# ---------------------------------------------------------------------------


def _patch_field(body: dict, user_id: str, correlation_id: str) -> dict:
    field = body.get('field', '')
    value = body.get('value')

    if field not in _ALLOWED_FIELDS:
        valid = ', '.join(sorted(_ALLOWED_FIELDS))
        return _response(400, {'error': f'field must be one of: {valid}'})

    if not isinstance(value, str):
        return _response(400, {'error': f'{field} must be a string'})

    max_len = _ALLOWED_FIELDS[field]
    if len(value) > max_len:
        return _response(400, {
            'error': f'{field} exceeds the {max_len}-character limit'
        })

    try:
        table = dynamodb.Table(MAIN_TABLE)

        # Nested Map update: SET portfolioContent.{field} = :value
        # ConditionExpression prevents silent creation if PORTFOLIO#current
        # doesn't exist yet (e.g. AI processing hasn't completed).
        table.update_item(
            Key={
                'PK': f'USER#{user_id}',
                'SK': 'PORTFOLIO#current',
            },
            UpdateExpression=(
                'SET #pc.#field = :value, #updatedAt = :updatedAt'
            ),
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

        _trigger_rebuild(user_id)

        _log('INFO', 'Portfolio field patched',
             correlationId=correlation_id,
             userId=user_id,
             field=field)

        return _response(200, {
            'field': field,
            'value': value,
            'status': 'saved',
        })

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _response(404, {
            'error': 'Portfolio not found. Generate a portfolio first.'
        })
    except Exception as e:
        _log('ERROR', 'Patch portfolio error',
             correlationId=correlation_id,
             userId=user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})


# ---------------------------------------------------------------------------
# Shared rebuild trigger
# ---------------------------------------------------------------------------


def _trigger_rebuild(user_id: str) -> None:
    """Async-invoke the portfolio generator to re-render HTML."""
    if PORTFOLIO_LAMBDA_NAME:
        lambda_client.invoke(
            FunctionName=PORTFOLIO_LAMBDA_NAME,
            InvocationType='Event',
            Payload=json.dumps({
                'userId': user_id,
                'trigger': 'patch',
            }),
        )
