"""
Lambda@Edge: Portfolio Access Gate

Attached to the CloudFront distribution on the Origin Request event.
Fires only on cache misses — zero added latency for cached responses.

Rules:
  - /u/{username}/... → resolved to the owner's userId, then treated as below
  - /draft/ paths     → always 403 (owners preview through edit page, never public URL)
  - /v{N}/ paths      → allowed only if portfolio isLive=true AND version == activeVersion
  - everything else   → pass through unchanged (error.html, assets, etc.)

Public portfolio URLs are addressed by username, but S3 objects are stored
under the immutable userId. This function is where the two meet: it resolves
USERNAME#{name} -> userId and rewrites the request URI before the origin fetch.
Keeping the translation here (rather than in the S3 key layout) is what makes a
username change a single DynamoDB write instead of a bulk object copy.

Renamed-away usernames remain resolvable as TTL'd tombstones, so links shared
before a rename keep working for the tombstone's lifetime.

Deployment note: must be deployed in us-east-1 and referenced by a versioned ARN.
"""

import json
import re
import boto3

# Matches /{userId}/{uploadId}/(v{N}|draft)/index.html
_PATTERN = re.compile(r'^/([^/]+)/([^/]+)/(v\d+|draft)/index\.html$')

# Matches any /u/{username}/... path — the public form.
# Deliberately matches the whole subtree, not just index.html, so that assets
# referenced with a relative path resolve too. Username charset mirrors
# username_utils._FORMAT_RE, but accepts any case: handles are stored and
# looked up lowercased, so a capitalised URL must resolve to the same portfolio.
_USERNAME_PATTERN = re.compile(
    r'^/u/([A-Za-z0-9][A-Za-z0-9_-]{1,28}[A-Za-z0-9])/(.+)$'
)

# Lambda@Edge does not support environment variables.
# These values are baked in at deploy time via Terraform templatefile().
_TABLE = '${dynamodb_table}'
_REGION = '${dynamodb_region}'

_dynamodb = boto3.client('dynamodb', region_name=_REGION)


def _resolve_username(username):
    """USERNAME#{name} -> userId, or None if unknown. Fails closed on error."""
    try:
        result = _dynamodb.get_item(
            TableName=_TABLE,
            Key={
                'PK': {'S': 'USERNAME#' + username},
                'SK': {'S': 'PROFILE'},
            },
            ProjectionExpression='userId',
        )
    except Exception:
        return None
    return result.get('Item', {}).get('userId', {}).get('S')


def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    uri = request['uri']

    # Public username form: resolve to the owner and rewrite to the S3 layout.
    # An unknown username is denied rather than passed through, so a bad handle
    # cannot be used to probe the raw userId namespace.
    username_match = _USERNAME_PATTERN.match(uri)
    if username_match:
        username, rest = username_match.groups()
        user_id = _resolve_username(username.lower())
        if not user_id:
            return _forbidden()
        uri = '/' + user_id + '/' + rest
        request['uri'] = uri

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
