"""
Lambda: User Profile

GET   /profile — read the caller's profile (username, display name)
PATCH /profile — change username and/or display name

Both Cognito-authenticated. The userId always comes from the verified token
sub, never from the request — there is no path parameter to tamper with, so a
user can only ever read or edit their own profile.

Renaming is rate limited (USERNAME_CHANGE_COOLDOWN_DAYS). Portfolio URLs embed
the username, so every rename breaks links that are already in the wild; the
cooldown keeps that from becoming routine. The old handle is left as a TTL'd
tombstone by username_utils.rename so those links survive the transition.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import boto3

import username_utils as uu

dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
cognito = boto3.client('cognito-idp')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
USER_POOL_ID = os.environ.get('USER_POOL_ID')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')
COOLDOWN_DAYS = int(os.environ.get('USERNAME_CHANGE_COOLDOWN_DAYS', '30'))

MAX_NAME_LENGTH = 100


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "profile",
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
        },
        'body': json.dumps(body),
    }


def _sync_cognito_username(user_id: str, username: str, correlation_id: str) -> bool:
    """
    Mirror the handle onto Cognito's preferred_username.

    DynamoDB is authoritative for uniqueness and for URL resolution, but login
    by username goes through a ListUsers filter on this attribute — so if this
    sync fails the user can still be reached at their portfolio URL, they just
    cannot log in with the NEW handle until it succeeds. Their email always
    works, so this is degraded rather than locked out.

    Returns False on failure; the caller logs it rather than failing the whole
    request, since the rename itself is already durable.
    """
    if not USER_POOL_ID:
        _log('ERROR', 'USER_POOL_ID not configured; skipping Cognito sync',
             correlationId=correlation_id)
        return False

    try:
        cognito.admin_update_user_attributes(
            UserPoolId=USER_POOL_ID,
            Username=user_id,
            UserAttributes=[{'Name': 'preferred_username', 'Value': username}],
        )
        return True
    except Exception as e:
        _log('ERROR', 'Cognito preferred_username sync failed',
             correlationId=correlation_id, userId=user_id,
             username=username, error=str(e))
        return False


def _token_sub(event) -> str:
    return (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    user_id = _token_sub(event)
    if not user_id:
        return _response(403, {'error': 'Forbidden'})

    method = (event.get('httpMethod') or '').upper()

    if method == 'GET':
        return _get(user_id, correlation_id)
    if method == 'PATCH':
        return _patch(event, user_id, correlation_id)

    return _response(405, {'error': 'Method not allowed'})


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


def _get(user_id: str, correlation_id: str) -> dict:
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        profile = uu.get_profile(table, user_id)
    except Exception as e:
        _log('ERROR', 'Profile read failed',
             correlationId=correlation_id, userId=user_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})

    if not profile:
        # Guests, and any account created before usernames existed.
        return _response(200, {'username': None, 'name': '', 'canChangeUsernameAt': None})

    return _response(200, {
        'username': profile.get('username'),
        'name': profile.get('name', ''),
        'canChangeUsernameAt': _next_change_allowed(profile),
    })


def _next_change_allowed(profile: dict) -> str | None:
    """ISO timestamp when the username may next be changed, or None if now."""
    last = profile.get('usernameUpdatedAt')
    if not last:
        return None
    try:
        last_dt = datetime.fromisoformat(last)
    except ValueError:
        return None
    next_dt = last_dt + timedelta(days=COOLDOWN_DAYS)
    return next_dt.isoformat() if next_dt > datetime.now(timezone.utc) else None


# ---------------------------------------------------------------------------
# PATCH
# ---------------------------------------------------------------------------


def _patch(event, user_id: str, correlation_id: str) -> dict:
    try:
        body = json.loads(event.get('body') or '{}')
    except (json.JSONDecodeError, ValueError):
        return _response(400, {'error': 'Invalid JSON body'})

    wants_username = 'username' in body
    wants_name = 'name' in body

    if not wants_username and not wants_name:
        return _response(400, {'error': 'Provide "username" and/or "name".'})

    table = dynamodb.Table(DYNAMODB_TABLE)

    try:
        profile = uu.get_profile(table, user_id)
    except Exception as e:
        _log('ERROR', 'Profile read failed during patch',
             correlationId=correlation_id, userId=user_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})

    if not profile:
        return _response(404, {'error': 'Profile not found.'})

    if wants_name:
        name = body.get('name')
        if not isinstance(name, str):
            return _response(400, {'error': 'name must be a string.'})
        name = name.strip()[:MAX_NAME_LENGTH]
        try:
            table.update_item(
                Key=uu.profile_key(user_id),
                UpdateExpression='SET #n = :n',
                ExpressionAttributeNames={'#n': 'name'},
                ExpressionAttributeValues={':n': name},
            )
        except Exception as e:
            _log('ERROR', 'Display name update failed',
                 correlationId=correlation_id, userId=user_id, error=str(e))
            return _response(500, {'error': 'Internal server error'})

    if not wants_username:
        return _response(200, {'status': 'saved', 'username': profile.get('username')})

    # ---- username change -------------------------------------------------
    new_raw = body.get('username')
    if not isinstance(new_raw, str):
        return _response(400, {'error': 'username must be a string.'})

    ok, error = uu.validate(new_raw)
    if not ok:
        return _response(400, {'error': error})

    new_username = uu.normalize(new_raw)
    current = profile.get('username')

    if new_username == current:
        return _response(200, {'status': 'saved', 'username': current})

    # No current handle (a claimed guest, or any pre-username account): this is
    # a first claim, not a rename — no cooldown applies and there is nothing to
    # tombstone.
    if not current:
        try:
            uu.claim(table, new_username, user_id, name=profile.get('name', ''))
        except uu.UsernameTaken:
            return _response(409, {'error': 'That username is already taken.'})
        except Exception as e:
            _log('ERROR', 'First username claim failed',
                 correlationId=correlation_id, userId=user_id, error=str(e))
            return _response(500, {'error': 'Internal server error'})

        synced = _sync_cognito_username(user_id, new_username, correlation_id)
        _log('INFO', 'Username claimed for existing account',
             correlationId=correlation_id, userId=user_id,
             username=new_username, cognitoSynced=synced)
        return _response(200, {'status': 'saved', 'username': new_username})

    blocked_until = _next_change_allowed(profile)
    if blocked_until:
        return _response(429, {
            'error': f'Username can only be changed once every {COOLDOWN_DAYS} days.',
            'canChangeUsernameAt': blocked_until,
        })

    try:
        uu.rename(dynamodb_client, DYNAMODB_TABLE, user_id, current, new_username)
    except uu.UsernameTaken:
        return _response(409, {'error': 'That username is already taken.'})
    except Exception as e:
        _log('ERROR', 'Username rename failed',
             correlationId=correlation_id, userId=user_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})

    synced = _sync_cognito_username(user_id, new_username, correlation_id)

    _log('INFO', 'Username changed',
         correlationId=correlation_id, userId=user_id,
         oldUsername=current, newUsername=new_username, cognitoSynced=synced)

    return _response(200, {'status': 'saved', 'username': new_username})
