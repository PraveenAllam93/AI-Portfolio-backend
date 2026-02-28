"""
Lambda: Manual Portfolio Content Patch

PATCH /portfolio/{userId}/content — Cognito-authenticated.

Allows the portfolio owner to overwrite a specific text field in their
portfolioContent, then asynchronously triggers a portfolio HTML rebuild.

Request body:
  { "field": "bio", "value": "New bio text..." }

Allowlisted fields and their max lengths (portfolioContent top-level only):
  bio          — 1000 chars
  headline     — 200 chars
  uniqueValue  — 500 chars

Security notes:
  - userId in path MUST match the Cognito token sub — enforced before any
    DynamoDB access. Cross-user writes are impossible at the code level.
  - Only fields in _ALLOWED_FIELDS can be written — no arbitrary key injection.
  - Value length is capped per field to prevent oversized DynamoDB items.
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

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PORTFOLIO_LAMBDA_NAME = os.environ.get('PORTFOLIO_LAMBDA_NAME')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

# Field name → max character length allowed.
# Only these portfolioContent keys may be patched — any other field is rejected.
_ALLOWED_FIELDS: dict[str, int] = {
    'bio': 1000,
    'headline': 200,
    'uniqueValue': 500,
}

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
    # Parse and validate body
    # ------------------------------------------------------------------
    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, ValueError):
        return _response(400, {'error': 'Invalid JSON body'})

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

    # ------------------------------------------------------------------
    # Update the nested portfolioContent field in DynamoDB
    # ------------------------------------------------------------------
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)

        # Nested Map update: SET portfolioContent.{field} = :value
        # ConditionExpression prevents silent creation if PORTFOLIO#current
        # doesn't exist yet (e.g. AI processing hasn't completed).
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

        # Trigger async HTML rebuild — user sees updated portfolio shortly after.
        if PORTFOLIO_LAMBDA_NAME:
            lambda_client.invoke(
                FunctionName=PORTFOLIO_LAMBDA_NAME,
                InvocationType='Event',  # async
                Payload=json.dumps({
                    'userId': path_user_id,
                    'trigger': 'manual_patch',
                }),
            )

        _log('INFO', 'Portfolio field patched',
             correlationId=correlation_id,
             userId=path_user_id,
             field=field)

        return _response(200, {'field': field, 'value': value, 'status': 'saved'})

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _response(404, {'error': 'Portfolio not found. Generate a portfolio first.'})

    except Exception as e:
        _log('ERROR', 'Patch portfolio error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})
