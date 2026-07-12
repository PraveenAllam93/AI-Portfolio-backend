"""
Lambda: Claim Guest Portfolio

POST /guest/claim — Cognito-authenticated as the NEWLY-CREATED real user.

Migrates everything an anonymous "Try for free" guest produced onto the real
account that just signed up, then (optionally) publishes the portfolio the user
chose to make live. Finally deletes all guest resources.

Flow (the guest is a real Cognito user whose email is on the reserved guest
domain — see GUEST_EMAIL_DOMAIN):

  1. Auth: caller is the real user (claims.sub). The real user must NOT itself
     be a guest.
  2. Ownership gate: the guestUserId asserted by the caller MUST resolve to a
     Cognito user whose email is on the guest domain. This makes it impossible
     to "claim" (and thereby steal + delete) a real account's data by passing
     an arbitrary sub.
  3. Re-key every USER#{guestSub} DynamoDB item onto USER#{realSub}. Any
     embedded reference to the guest sub (S3 asset URLs, portfolioPath) is
     rewritten to the real sub.
  4. Copy the guest's portfolio-bucket objects ({guestSub}/*) to {realSub}/*
     so uploaded images survive.
  5. Re-run the portfolio generator under the real user: the chosen uploadId is
     published live (target=publish); any other guest drafts are re-rendered as
     drafts under the real account.
  6. Delete all guest resources: DynamoDB items, S3 objects (portfolio +
     validated + quarantine), and the guest Cognito user.

Security notes:
  - realSub comes from the verified Cognito token; guestSub is validated to be a
    guest-domain account before ANY data is touched or deleted.
  - Least-privilege IAM: this Lambda is the only one permitted cross-user
    DynamoDB access, and it gates every operation on the guest-domain check.
"""

import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')
cognito = boto3.client('cognito-idp')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
PORTFOLIO_BUCKET = os.environ.get('PORTFOLIO_BUCKET')
VALIDATED_BUCKET = os.environ.get('VALIDATED_BUCKET')
QUARANTINE_BUCKET = os.environ.get('QUARANTINE_BUCKET')
PORTFOLIO_LAMBDA_NAME = os.environ.get('PORTFOLIO_LAMBDA_NAME')
USER_POOL_ID = os.environ.get('USER_POOL_ID')
GUEST_EMAIL_DOMAIN = os.environ.get('GUEST_EMAIL_DOMAIN', 'guest.aifolio.internal')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({"level": level, "function": "claim_guest",
                      "message": message, **kwargs}))


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


class _DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns numbers as Decimal — serialize them as int/float."""

    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def _rekey_item(item: dict, guest_sub: str, real_sub: str) -> dict:
    """Rewrite a DynamoDB item from the guest namespace to the real user.

    A blanket string replace of the guest sub is safe: the sub is a UUID that
    only appears in the PK, userId, portfolioPath and S3 asset URLs — never in
    free-text resume content — so there are no false positives.
    """
    raw = json.dumps(item, cls=_DecimalEncoder)
    raw = raw.replace(guest_sub, real_sub)
    new_item = json.loads(raw)
    # PK is rewritten by the replace above; be explicit and defensive anyway.
    new_item['PK'] = f'USER#{real_sub}'
    new_item['userId'] = real_sub
    if new_item.get('SK', '').startswith('PORTFOLIO#'):
        new_item['isGuest'] = False
    return new_item


def _is_guest_account(sub: str) -> bool:
    """True only if `sub` is a Cognito user whose email is on the guest domain."""
    if not USER_POOL_ID:
        return False
    try:
        resp = cognito.admin_get_user(UserPoolId=USER_POOL_ID, Username=sub)
    except cognito.exceptions.UserNotFoundException:
        return False
    except Exception as e:  # noqa: BLE001
        _log('ERROR', 'admin_get_user failed', sub=sub, error=str(e))
        return False
    email = ''
    for attr in resp.get('UserAttributes', []):
        if attr.get('Name') == 'email':
            email = (attr.get('Value') or '').lower()
            break
    return email.endswith('@' + GUEST_EMAIL_DOMAIN)


def _query_all(table, guest_sub: str) -> list:
    items = []
    kwargs = {'KeyConditionExpression': Key('PK').eq(f'USER#{guest_sub}')}
    while True:
        resp = table.query(**kwargs)
        items.extend(resp.get('Items', []))
        last = resp.get('LastEvaluatedKey')
        if not last:
            break
        kwargs['ExclusiveStartKey'] = last
    return items


def _copy_prefix(bucket: str, guest_sub: str, real_sub: str) -> None:
    """Copy every object under {guest_sub}/ to {real_sub}/ within one bucket."""
    if not bucket:
        return
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=f'{guest_sub}/'):
        for obj in page.get('Contents', []):
            src_key = obj['Key']
            dest_key = real_sub + src_key[len(guest_sub):]
            s3_client.copy_object(
                Bucket=bucket,
                Key=dest_key,
                CopySource={'Bucket': bucket, 'Key': src_key},
            )


def _delete_prefix(bucket: str, guest_sub: str) -> None:
    """Delete every object under {guest_sub}/ within one bucket."""
    if not bucket:
        return
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=f'{guest_sub}/'):
        keys = [{'Key': o['Key']} for o in page.get('Contents', [])]
        if keys:
            s3_client.delete_objects(Bucket=bucket, Delete={'Objects': keys})


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'
    try:
        claims = event['requestContext']['authorizer']['claims']
        real_sub = claims['sub']
        real_email = (claims.get('email') or '').lower()

        body = json.loads(event.get('body') or '{}')
        guest_sub = (body.get('guestUserId') or '').strip()
        publish_upload_id = (body.get('uploadId') or '').strip() or None

        _log('INFO', 'Claim requested', correlationId=correlation_id,
             realSub=real_sub, guestSub=guest_sub, publishUploadId=publish_upload_id)

        # --- Guard 1: caller must be a real account, not a guest ---
        if real_email.endswith('@' + GUEST_EMAIL_DOMAIN):
            return _response(403, {'error': 'A real account is required to claim a portfolio.'})

        # --- Guard 2: guestUserId present and distinct ---
        if not guest_sub or guest_sub == real_sub:
            return _response(400, {'error': 'Invalid guest session.'})

        # --- Guard 3: the target MUST be a guest-domain account ---
        # Prevents claiming (and deleting) a real user's data via a forged sub.
        if not _is_guest_account(guest_sub):
            _log('WARNING', 'Refusing to claim non-guest account',
                 correlationId=correlation_id, guestSub=guest_sub)
            return _response(403, {'error': 'That session cannot be claimed.'})

        table = dynamodb.Table(DYNAMODB_TABLE)
        guest_items = _query_all(table, guest_sub)
        if not guest_items:
            _log('INFO', 'Nothing to claim', correlationId=correlation_id, guestSub=guest_sub)
            # Nothing to migrate — still clean up the empty guest user below.
            _cleanup_guest(guest_sub, correlation_id)
            return _response(200, {'claimed': [], 'published': None})

        # --- Copy S3 assets first (portfolio bucket holds uploaded images) ---
        _copy_prefix(PORTFOLIO_BUCKET, guest_sub, real_sub)

        # --- Re-key every DynamoDB item onto the real user ---
        upload_ids = []
        for item in guest_items:
            sk = item.get('SK', '')
            new_item = _rekey_item(item, guest_sub, real_sub)
            if sk.startswith('PORTFOLIO#') and '#VERSION#' not in sk:
                upload_id = item.get('uploadId')
                if upload_id:
                    upload_ids.append(upload_id)
                # If this is the chosen portfolio, mark it live; the generator
                # publish invocation below produces the public v1.
                new_item['isLive'] = (item.get('uploadId') == publish_upload_id)
            table.put_item(Item=new_item)

        # --- Re-render under the real account ---
        published = None
        for upload_id in upload_ids:
            is_publish = upload_id == publish_upload_id
            payload = {'userId': real_sub, 'uploadId': upload_id}
            if is_publish:
                payload['target'] = 'publish'
                published = upload_id
            else:
                payload['target'] = 'draft'
                payload['finalizeUpload'] = True
            try:
                lambda_client.invoke(
                    FunctionName=PORTFOLIO_LAMBDA_NAME,
                    InvocationType='Event',  # async — frontend polls for COMPLETE
                    Payload=json.dumps(payload),
                )
            except Exception as e:  # noqa: BLE001
                _log('ERROR', 'Failed to invoke generator during claim',
                     correlationId=correlation_id, uploadId=upload_id, error=str(e))

        # --- Delete all guest resources (data already migrated) ---
        _cleanup_guest(guest_sub, correlation_id, table=table, guest_items=guest_items)

        _log('INFO', 'Claim complete', correlationId=correlation_id,
             realSub=real_sub, claimed=upload_ids, published=published)

        return _response(200, {'claimed': upload_ids, 'published': published})

    except Exception as e:  # noqa: BLE001
        _log('ERROR', 'Claim error', correlationId=correlation_id, error=str(e))
        return _response(500, {'error': 'Failed to claim portfolio.'})


def _cleanup_guest(guest_sub: str, correlation_id: str, table=None, guest_items=None):
    """Delete guest DynamoDB items, S3 objects, and the Cognito user.

    Best-effort: a failure here is logged but does not fail the claim — the 72h
    reaper is the backstop for any orphaned guest user.
    """
    if table is not None and guest_items is not None:
        for item in guest_items:
            try:
                table.delete_item(Key={'PK': item['PK'], 'SK': item['SK']})
            except Exception as e:  # noqa: BLE001
                _log('ERROR', 'Failed to delete guest item',
                     correlationId=correlation_id, sk=item.get('SK'), error=str(e))

    for bucket in (PORTFOLIO_BUCKET, VALIDATED_BUCKET, QUARANTINE_BUCKET):
        try:
            _delete_prefix(bucket, guest_sub)
        except Exception as e:  # noqa: BLE001
            _log('ERROR', 'Failed to delete guest S3 prefix',
                 correlationId=correlation_id, bucket=bucket, error=str(e))

    if USER_POOL_ID:
        try:
            cognito.admin_delete_user(UserPoolId=USER_POOL_ID, Username=guest_sub)
        except Exception as e:  # noqa: BLE001
            _log('ERROR', 'Failed to delete guest Cognito user',
                 correlationId=correlation_id, guestSub=guest_sub, error=str(e))
