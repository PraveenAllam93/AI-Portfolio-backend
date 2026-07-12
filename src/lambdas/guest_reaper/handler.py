"""
Lambda: Guest Reaper

Scheduled (EventBridge) cleanup of abandoned "Try for free" guest accounts.

A guest is a real Cognito user whose email is `guest-<uuid>@GUEST_EMAIL_DOMAIN`,
created when someone clicks "Try for free" without signing up. If the guest
never converts to a real account, their user + data would linger (Cognito MAU
cost + storage). This reaper deletes any guest older than GUEST_TTL_HOURS along
with all of their DynamoDB items and S3 objects.

Guests who DO convert are deleted immediately by the claim Lambda; this is the
backstop for the ones who simply leave.

Security notes:
  - Only ever touches accounts on the reserved guest domain — real users are
    never matched (the ListUsers prefix filter + the domain suffix check both
    gate on the guest identity).
  - Least-privilege IAM: Cognito list/delete, DynamoDB query/delete, S3
    list/delete scoped to the three pipeline buckets.
"""

import json
import os
from datetime import datetime, timezone, timedelta

import boto3
from boto3.dynamodb.conditions import Key

cognito = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

USER_POOL_ID = os.environ.get('USER_POOL_ID')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
VALIDATED_BUCKET = os.environ.get('VALIDATED_BUCKET')
QUARANTINE_BUCKET = os.environ.get('QUARANTINE_BUCKET')
GUEST_EMAIL_DOMAIN = os.environ.get('GUEST_EMAIL_DOMAIN', 'guest.aifolio.internal')
GUEST_TTL_HOURS = float(os.environ.get('GUEST_TTL_HOURS', 72))


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "guest_reaper",
                      "message": message, **kwargs}))


def _delete_prefix(bucket: str, sub: str) -> None:
    if not bucket:
        return
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=f'{sub}/'):
        keys = [{'Key': o['Key']} for o in page.get('Contents', [])]
        if keys:
            s3_client.delete_objects(Bucket=bucket, Delete={'Objects': keys})


def _delete_dynamo_items(table, sub: str) -> int:
    count = 0
    kwargs = {
        'KeyConditionExpression': Key('PK').eq(f'USER#{sub}'),
        'ProjectionExpression': 'PK, SK',
    }
    while True:
        resp = table.query(**kwargs)
        for item in resp.get('Items', []):
            table.delete_item(Key={'PK': item['PK'], 'SK': item['SK']})
            count += 1
        last = resp.get('LastEvaluatedKey')
        if not last:
            break
        kwargs['ExclusiveStartKey'] = last
    return count


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'
    if not USER_POOL_ID:
        _log('ERROR', 'USER_POOL_ID not configured', correlationId=correlation_id)
        return {'reaped': 0}

    cutoff = datetime.now(timezone.utc) - timedelta(hours=GUEST_TTL_HOURS)
    table = dynamodb.Table(DYNAMODB_TABLE)
    reaped = 0
    scanned = 0

    paginator = cognito.get_paginator('list_users')
    # All guest emails start with "guest-" — prefix filter keeps the listing to
    # guest accounts only. The domain suffix is re-checked per user below.
    page_iter = paginator.paginate(
        UserPoolId=USER_POOL_ID,
        Filter='email ^= "guest-"',
    )

    for page in page_iter:
        for user in page.get('Users', []):
            scanned += 1
            attrs = {a['Name']: a.get('Value', '') for a in user.get('Attributes', [])}
            email = (attrs.get('email') or '').lower()
            sub = attrs.get('sub')
            created = user.get('UserCreateDate')

            if not sub or not email.endswith('@' + GUEST_EMAIL_DOMAIN):
                continue
            if created is None:
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created > cutoff:
                continue  # still within the grace window

            # --- Reap: DynamoDB, S3, then the Cognito user itself ---
            try:
                n = _delete_dynamo_items(table, sub)
                for bucket in (PORTFOLIO_BUCKET, VALIDATED_BUCKET, QUARANTINE_BUCKET):
                    _delete_prefix(bucket, sub)
                cognito.admin_delete_user(UserPoolId=USER_POOL_ID, Username=user['Username'])
                reaped += 1
                _log('INFO', 'Reaped stale guest', correlationId=correlation_id,
                     guestSub=sub, itemsDeleted=n, createdAt=created.isoformat())
            except Exception as e:  # noqa: BLE001
                _log('ERROR', 'Failed to reap guest', correlationId=correlation_id,
                     guestSub=sub, error=str(e))

    _log('INFO', 'Reap run complete', correlationId=correlation_id,
         scanned=scanned, reaped=reaped, ttlHours=GUEST_TTL_HOURS)
    return {'scanned': scanned, 'reaped': reaped}
