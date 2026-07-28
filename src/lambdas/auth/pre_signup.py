"""
Cognito PreSignUp trigger: claim the user's chosen username.

Why here and not in the web app: this is the only place the reservation can be
made atomic with account creation. If the conditional put fails, we raise, and
Cognito refuses to create the user at all — there is no window in which an
account exists without a username, and no window in which two accounts hold
the same one.

Cognito assigns the pool's generated UUID *before* invoking this trigger and
passes it as event['userName']. For a pool with username_attributes = ["email"]
that UUID is exactly the value that becomes the `sub` claim, so it is safe to
use as the userId the username points at.

The handle arrives on the standard `preferred_username` attribute rather than a
custom one, because standard attributes are searchable through ListUsers — that
is what lets the web app resolve a username to an account at login time.

Skipped for:
  - guest accounts (email on GUEST_EMAIL_DOMAIN) — a guest has no username
    until it is claimed onto a real account by claim_guest
  - admin-created and federated users — they never carry preferred_username

Raising from this trigger surfaces the message to the caller, so the text of
every raise here is user-facing.
"""

import json
import os

import boto3

import username_utils as uu

dynamodb = boto3.resource('dynamodb')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
GUEST_EMAIL_DOMAIN = os.environ.get('GUEST_EMAIL_DOMAIN', 'guest.aifolio.internal')


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "pre_signup",
        "message": message,
        **kwargs,
    }))


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'
    trigger = event.get('triggerSource', '')
    attrs = (event.get('request') or {}).get('userAttributes') or {}
    email = (attrs.get('email') or '').lower()
    user_id = event.get('userName') or ''

    # Only self-service sign-ups carry a username.
    if trigger != 'PreSignUp_SignUp':
        _log('INFO', 'Skipping username claim for non-signup trigger',
             correlationId=correlation_id, triggerSource=trigger)
        return event

    # Guests are anonymous by definition; they get a username at claim time.
    if email.endswith('@' + GUEST_EMAIL_DOMAIN):
        _log('INFO', 'Skipping username claim for guest account',
             correlationId=correlation_id)
        return event

    raw_username = attrs.get('preferred_username') or ''
    ok, error = uu.validate(raw_username)
    if not ok:
        _log('WARNING', 'Username rejected at signup',
             correlationId=correlation_id, reason=error)
        raise Exception(error)

    username = uu.normalize(raw_username)
    table = dynamodb.Table(DYNAMODB_TABLE)

    try:
        uu.claim(table, username, user_id, name=attrs.get('name', ''))
    except uu.UsernameTaken:
        _log('WARNING', 'Username already claimed',
             correlationId=correlation_id, username=username)
        raise Exception('That username is already taken. Please choose another.')
    except Exception as e:
        # Never leak internals to the signup form.
        _log('ERROR', 'Username claim failed',
             correlationId=correlation_id, username=username, error=str(e))
        raise Exception('Could not complete signup. Please try again.')

    _log('INFO', 'Username claimed',
         correlationId=correlation_id, username=username, userId=user_id)

    return event
