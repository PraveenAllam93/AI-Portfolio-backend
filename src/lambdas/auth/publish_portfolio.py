"""
Lambda: Publish Portfolio

POST /portfolio/{userId}/publish — Cognito-authenticated.

Triggers an async portfolio rebuild to the published (live) path:
  s3://{bucket}/{userId}/v{version}/index.html

This is the "commit draft to live" action. All edits via patch_portfolio
rebuild only the draft path. Publish makes them publicly visible.

Security notes:
  - userId in path MUST match the Cognito token sub.
  - Only the owner can publish their portfolio.
"""

import json
import os
from urllib.parse import unquote

import boto3

lambda_client = boto3.client('lambda')

PORTFOLIO_LAMBDA_NAME = os.environ.get('PORTFOLIO_LAMBDA_NAME')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')


# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "publish_portfolio",
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
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps(body),
    }


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    # Authorization: path userId must match token sub
    path_user_id = unquote((event.get('pathParameters') or {}).get('userId', ''))
    token_sub = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )

    if not path_user_id or path_user_id != token_sub:
        _log('WARNING', 'Publish auth mismatch', correlationId=correlation_id)
        return _response(403, {'error': 'Forbidden'})

    if not PORTFOLIO_LAMBDA_NAME:
        _log('ERROR', 'PORTFOLIO_LAMBDA_NAME not configured', correlationId=correlation_id)
        return _response(500, {'error': 'Internal server error'})

    try:
        resp = lambda_client.invoke(
            FunctionName=PORTFOLIO_LAMBDA_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'userId': path_user_id,
                'trigger': 'publish',
                'target': 'publish',
            }),
        )

        if resp.get('FunctionError'):
            _log('ERROR', 'Portfolio generator error',
                 correlationId=correlation_id,
                 userId=path_user_id,
                 functionError=resp['FunctionError'])
            return _response(500, {'error': 'Portfolio generation failed'})

        _log('INFO', 'Portfolio published',
             correlationId=correlation_id,
             userId=path_user_id)

        return _response(200, {
            'message': 'Portfolio published successfully.',
            'userId': path_user_id,
        })

    except Exception as e:
        _log('ERROR', 'Publish error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})
