"""
Lambda@Edge: Portfolio Access Gate

Attached to the CloudFront distribution on the Origin Request event.
Fires only on cache misses — zero added latency for cached responses.

Rules:
  - /draft/ paths   → always 403 (owners preview through edit page, never public URL)
  - /v{N}/ paths    → allowed only if portfolio isLive=true AND version == activeVersion
  - everything else → pass through unchanged (error.html, assets, etc.)

Deployment note: must be deployed in us-east-1 and referenced by a versioned ARN.
"""

import json
import re
import boto3

# Matches /{userId}/{uploadId}/(v{N}|draft)/index.html
_PATTERN = re.compile(r'^/([^/]+)/([^/]+)/(v\d+|draft)/index\.html$')

# Lambda@Edge does not support environment variables.
# These values are baked in at deploy time via Terraform templatefile().
_TABLE = '${dynamodb_table}'
_REGION = '${dynamodb_region}'

_dynamodb = boto3.client('dynamodb', region_name=_REGION)


def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    uri = request['uri']

    match = _PATTERN.match(uri)
    if not match:
        return request  # not a portfolio path — pass through

    user_id, upload_id, version = match.groups()

    # Draft is owner-only; owners use the edit-page preview, not a public URL.
    if version == 'draft':
        return _forbidden()

    # Check DynamoDB for isLive + activeVersion.
    try:
        result = _dynamodb.get_item(
            TableName=_TABLE,
            Key={
                'PK': {'S': f'USER#{user_id}'},
                'SK': {'S': f'PORTFOLIO#{upload_id}'},
            },
            ProjectionExpression='isLive, activeVersion',
        )
        item = result.get('Item', {})
    except Exception:
        # On any DynamoDB error, deny rather than allow (fail closed).
        return _forbidden()

    is_live = item.get('isLive', {}).get('BOOL', False)
    active_version = item.get('activeVersion', {}).get('S', '')

    if is_live and version == active_version:
        return request  # public access allowed

    return _forbidden()


def _forbidden():
    return {
        'status': '403',
        'statusDescription': 'Forbidden',
        'headers': {
            'content-type': [{'key': 'Content-Type', 'value': 'text/html; charset=utf-8'}],
            'cache-control': [{'key': 'Cache-Control', 'value': 'no-store'}],
            'x-content-type-options': [{'key': 'X-Content-Type-Options', 'value': 'nosniff'}],
        },
        'body': (
            '<!DOCTYPE html><html><head><title>Not Available</title></head>'
            '<body style="font-family:sans-serif;text-align:center;padding:4rem;">'
            '<h1 style="color:#111">Portfolio Not Available</h1>'
            '<p style="color:#666">This portfolio is not publicly accessible.</p>'
            '</body></html>'
        ),
    }
