"""
Lambda: Username Availability Check

GET /username/check?username=xyz — PUBLIC (no auth).

Feedback for the signup form only. This endpoint is advisory: the answer can go
stale between the keystroke and the submit, so it is NOT the thing that
enforces uniqueness. The conditional put in the PreSignUp trigger is.

Public by necessity — the caller has no account yet. That makes it a username
enumeration surface, which is acceptable here because usernames are published
in portfolio URLs and are public by design. It reveals nothing about emails or
account existence. API Gateway throttling caps the scrape rate.
"""

import json
import os

import boto3

import username_utils as uu

dynamodb = boto3.resource('dynamodb')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "check_username",
        "message": message,
        **kwargs,
    }))


def _response(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'X-Content-Type-Options': 'nosniff',
            'Cache-Control': 'no-store',
        },
        'body': json.dumps(body),
    }


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    params = event.get('queryStringParameters') or {}
    raw = params.get('username', '')

    ok, error = uu.validate(raw)
    if not ok:
        return _response(200, {'available': False, 'reason': error})

    username = uu.normalize(raw)

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        taken = uu.is_taken(table, username)
    except Exception as e:
        _log('ERROR', 'Availability check failed',
             correlationId=correlation_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})

    return _response(200, {
        'username': username,
        'available': not taken,
        'reason': 'That username is already taken.' if taken else '',
    })
