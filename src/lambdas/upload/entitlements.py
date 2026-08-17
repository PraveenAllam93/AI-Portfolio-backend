"""
Shared plan / entitlement helpers for the auth Lambda bundle.

Every Lambda under src/lambdas/auth ships in ONE zip (see the Terraform
`archive_file.get_portfolio` data source, whose source_dir is src/lambdas/auth
and whose output feeds ~20 aws_lambda_function resources). So this module is
importable from any of them with no packaging work — the same trick
username_utils.py uses.

`src/lambdas/upload/entitlements.py` is a deliberate copy: the presigned-URL
Lambda is packaged from its own source_dir and cannot import this file. Keep the
two in sync (same pattern as shared/resume_models.py vs
ai_processing/resume_models.py).

Model
-----
A user's plan lives on their profile record:

    PK = USER#{userId}   SK = PROFILE
    { plan, planStatus, planExpiresAt, planUpdatedAt, ... }

A MISSING profile, or a profile with no `plan`, resolves to FREE. That is what
makes this change require no backfill: every account that exists today — and
every anonymous guest, who has no profile record at all — is already on the free
plan the moment this deploys. Payments (added later) only ever have to write
`plan` onto this one record; nothing else in the system needs to know.

Daily counters are separate records with a TTL:

    PK = USER#{userId}   SK = QUOTA#{YYYY-MM-DD}#{action}
    { count, ttl }

They are consumed with a single conditional UpdateItem, so the check and the
increment are atomic — a user hammering the ✦ AI button cannot race past the
limit with concurrent Lambda invocations. This is the same pattern
generate_project_image.py used for its private IMAGE_GEN# counter, generalized
so every metered action shares one implementation.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import boto3

dynamodb = boto3.resource('dynamodb')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

FREE = 'free'
PRO = 'pro'

# Adding a third tier ('ultra', …) is a new key here plus its price mapping in
# whatever payment webhook sets `plan` — no other file needs to change.
#
# `None` means unlimited. Daily limits are counted in UTC days.
PLANS: dict = {
    FREE: {
        'label': 'Free',
        'portfolios': 1,
        'templates': 'free_only',
        'ai_analyze_per_day': 2,
        'ai_enhance_per_day': 3,
        'publishes_per_day': 2,
        'project_images_per_day': 1,
        'analytics': False,
    },
    PRO: {
        'label': 'Pro',
        'portfolios': None,
        'templates': 'all',
        'ai_analyze_per_day': 50,
        'ai_enhance_per_day': 200,
        'publishes_per_day': 20,
        'project_images_per_day': 20,
        'analytics': True,
    },
}

# Anything not in PLANS (corrupt data, a plan name from a future deploy that was
# rolled back) degrades to free rather than crashing or granting paid access.
DEFAULT_PLAN = FREE

# ---------------------------------------------------------------------------
# Free template allowlist
# ---------------------------------------------------------------------------

# One template per profession is free, except software engineering which gets
# three (it has 23 templates, vs 2 for several other professions).
#
# MUST stay in sync with the frontend: TEMPLATE_META `tier` in
# src/lib/templates/index.ts and TEMPLATES_BY_PROFESSION in the upload wizard.
# The frontend decides what to STAR; this set decides what is actually allowed,
# and it is the only one of the two that a client cannot tamper with.
FREE_TEMPLATES: frozenset = frozenset({
    # software_engineer
    'nebula', 'codex', 'neon',
    # designer  (displayed as "Luxe Studio")
    'designer',
    # marketing (displayed as "Campaign")
    'marketing',
    # finance
    'sterling',
    # civil_engineer
    'blueprint',
    # mechanical_engineer
    'torque',
    # accountant
    'meridian',
    # hr
    'haven',
    # sales
    'clarion',
})

# ---------------------------------------------------------------------------
# Metered actions — the {action} half of the QUOTA# sort key
# ---------------------------------------------------------------------------

ACTION_AI_ANALYZE = 'ai_analyze'
ACTION_AI_ENHANCE = 'ai_enhance'
ACTION_PUBLISH = 'publish'
ACTION_PROJECT_IMAGE = 'project_image'

# action -> the PLANS key holding its daily allowance
_ACTION_LIMIT_KEY: dict = {
    ACTION_AI_ANALYZE: 'ai_analyze_per_day',
    ACTION_AI_ENHANCE: 'ai_enhance_per_day',
    ACTION_PUBLISH: 'publishes_per_day',
    ACTION_PROJECT_IMAGE: 'project_images_per_day',
}

# Human-readable, used in the 402 body the frontend renders in the upgrade modal.
_ACTION_LABEL: dict = {
    ACTION_AI_ANALYZE: 'AI suggestion runs',
    ACTION_AI_ENHANCE: 'AI enhancements',
    ACTION_PUBLISH: 'publishes',
    ACTION_PROJECT_IMAGE: 'project image generations',
}


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "entitlements",
        "message": message,
        **kwargs,
    }))


def _table():
    return dynamodb.Table(DYNAMODB_TABLE)


# ---------------------------------------------------------------------------
# Plan resolution
# ---------------------------------------------------------------------------


def get_plan(user_id: str) -> str:
    """
    Resolve a user's plan name. Never raises and never fails open to a paid
    plan: any missing record, unknown plan name, or DynamoDB error yields FREE.

    A read failure downgrading a paying user to free limits for one request is
    an annoyance; a read failure granting a free user unlimited AI spend is a
    cost incident. The bias is deliberate.
    """
    if not user_id:
        return DEFAULT_PLAN
    try:
        result = _table().get_item(
            Key={'PK': f'USER#{user_id}', 'SK': 'PROFILE'},
            ProjectionExpression='#p, planStatus, planExpiresAt',
            ExpressionAttributeNames={'#p': 'plan'},
        )
    except Exception as e:
        _log('ERROR', 'Plan read failed — defaulting to free',
             userId=user_id, error=str(e))
        return DEFAULT_PLAN

    item = result.get('Item') or {}
    plan = item.get('plan') or DEFAULT_PLAN

    if plan not in PLANS:
        _log('WARNING', 'Unknown plan on profile — defaulting to free',
             userId=user_id, plan=str(plan))
        return DEFAULT_PLAN

    # A lapsed subscription that the billing webhook has not yet reconciled
    # (missed webhook, provider outage) must not keep paid access forever.
    expires_at = item.get('planExpiresAt')
    if plan != FREE and expires_at:
        try:
            expiry = datetime.fromisoformat(str(expires_at))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= datetime.now(timezone.utc):
                return DEFAULT_PLAN
        except (ValueError, TypeError):
            # Unparseable expiry — treat the plan as active and let billing fix
            # the record. Logged so it is visible rather than silent.
            _log('WARNING', 'Unparseable planExpiresAt',
                 userId=user_id, planExpiresAt=str(expires_at))

    return plan


def limits_for(plan: str) -> dict:
    """The full limit dict for a plan name, falling back to free."""
    return PLANS.get(plan, PLANS[DEFAULT_PLAN])


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def template_allowed(plan: str, template_id: str) -> bool:
    """True when `plan` may select `template_id`."""
    if limits_for(plan).get('templates') == 'all':
        return True
    return template_id in FREE_TEMPLATES


# ---------------------------------------------------------------------------
# Portfolio count
# ---------------------------------------------------------------------------


def portfolio_upload_ids(user_id: str) -> set:
    """
    The uploadIds of every real portfolio the user owns.

    Returns IDs rather than a bare count so callers that ALSO track in-flight
    uploads (the presigned-URL Lambda) can union the two sets instead of adding
    them. A resume part-way through the pipeline can have its PORTFOLIO# record
    written while its UPLOAD# record is still in a non-terminal status; adding
    the counts would score that single portfolio as two and lock a free user out
    of their own account.

    NOTE: `SK begins_with('PORTFOLIO#')` also matches immutable version
    snapshots, whose SK is PORTFOLIO#{uploadId}#VERSION#{v}. Counting those
    would make one portfolio look like several as soon as it is published twice.
    list_portfolios.py filters them the same way.
    """
    from boto3.dynamodb.conditions import Key

    table = _table()
    ids = set()
    query_kwargs = {
        'KeyConditionExpression': (
            Key('PK').eq(f'USER#{user_id}') & Key('SK').begins_with('PORTFOLIO#')
        ),
        'ProjectionExpression': 'SK, uploadId',
    }
    while True:
        resp = table.query(**query_kwargs)
        for item in resp.get('Items', []):
            sk = item.get('SK', '')
            if '#VERSION#' in sk:
                continue
            ids.add(item.get('uploadId') or sk.replace('PORTFOLIO#', ''))
        last_key = resp.get('LastEvaluatedKey')
        if not last_key:
            break
        query_kwargs['ExclusiveStartKey'] = last_key
    return ids


def count_portfolios(user_id: str) -> int:
    """Number of real portfolios the user owns."""
    return len(portfolio_upload_ids(user_id))


# Upload states that are still moving through the pipeline. Used for the
# CONCURRENCY cap (MAX_ACTIVE_UPLOADS), which limits how many resumes may be in
# the pipeline at once regardless of plan.
_IN_FLIGHT_STATUSES = frozenset({
    'PENDING_UPLOAD', 'VALIDATING', 'VALIDATED',
    'EXTRACTING_TEXT', 'AWAITING_SELECTION', 'QUEUED_FOR_AI',
    'AI_PROCESSING', 'GENERATING',
})

# Upload states that occupy a PLAN slot — deliberately narrower than in-flight.
#
# A slot is only taken once generation has actually been committed, because only
# then is the upload guaranteed to become a portfolio (and only then has it cost
# anything). Everything earlier — PENDING_UPLOAD through AWAITING_SELECTION — is
# a resume sitting on the profession/template screen that the user may never
# finish.
#
# Why this matters: those earlier records have no PORTFOLIO# entry, so they are
# invisible on the dashboard. Counting them meant a user who abandoned the
# template screen was told "you've used your portfolio — delete it to start
# over" with nothing on screen to delete, and no way out until the record aged
# out. On a 1-portfolio plan a single abandoned upload locked the account.
#
# Nothing is lost by excluding them: start_generation re-checks the cap at the
# moment generation begins, so an abandoned upload can never be used to sneak
# past the limit — it just stops blocking the user in the meantime. Flooding is
# still bounded by the separate MAX_ACTIVE_UPLOADS concurrency cap.
_SLOT_STATUSES = frozenset({'QUEUED_FOR_AI', 'AI_PROCESSING', 'GENERATING'})

# Past this age an in-flight record is treated as abandoned and stops counting
# for BOTH caps. Applied to every in-flight status, not just the user-paused
# ones: a pipeline that dies mid-run (failed AI call, Lambda timeout) leaves a
# record stuck at AI_PROCESSING/GENERATING forever, and that used to be a
# permanent ghost slot with no way for the user to clear it.
_STALE_UPLOAD_EXPIRY_HOURS = float(os.environ.get('STALE_UPLOAD_EXPIRY_HOURS', 24))


def _parse_iso(value):
    """Parse a stored ISO-8601 timestamp; return None if missing/unparseable."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _is_stale(item, now) -> bool:
    """True when an in-flight record has sat idle past the expiry window."""
    last_touched = _parse_iso(item.get('updatedAt')) or _parse_iso(item.get('createdAt'))
    if last_touched is None:
        return False  # no timestamp — count it to stay safe
    return (now - last_touched).total_seconds() / 3600.0 >= _STALE_UPLOAD_EXPIRY_HOURS


def _upload_ids_with_status(user_id: str, statuses: frozenset) -> set:
    """
    uploadIds whose live status is in `statuses` and which are not stale.

    Reads the live `status` attribute rather than GSI1PK, which is never updated
    after record creation and so cannot be trusted for this.
    """
    from boto3.dynamodb.conditions import Key

    now = datetime.now(timezone.utc)
    table = _table()
    ids = set()
    query_kwargs = {
        'KeyConditionExpression': (
            Key('PK').eq(f'USER#{user_id}') & Key('SK').begins_with('UPLOAD#')
        ),
        'ProjectionExpression': 'SK, uploadId, #s, createdAt, updatedAt',
        'ExpressionAttributeNames': {'#s': 'status'},
    }
    while True:
        resp = table.query(**query_kwargs)
        for item in resp.get('Items', []):
            if item.get('status') in statuses and not _is_stale(item, now):
                sk = item.get('SK', '')
                ids.add(item.get('uploadId') or sk.replace('UPLOAD#', ''))
        last_key = resp.get('LastEvaluatedKey')
        if not last_key:
            break
        query_kwargs['ExclusiveStartKey'] = last_key
    return ids


def active_upload_ids(user_id: str) -> set:
    """Uploads anywhere in the pipeline — feeds the concurrency cap."""
    return _upload_ids_with_status(user_id, _IN_FLIGHT_STATUSES)


def committed_upload_ids(user_id: str) -> set:
    """
    Uploads that have been committed to generation — these occupy a plan slot.

    Narrower than active_upload_ids on purpose; see _SLOT_STATUSES.
    """
    return _upload_ids_with_status(user_id, _SLOT_STATUSES)


def used_portfolio_slots(user_id: str, exclude_upload_id: str | None = None) -> int:
    """
    How many of the plan's portfolio slots are already spoken for.

    The union of finished portfolios and uploads already committed to
    generation — a union, not a sum, because mid-pipeline an upload owns both an
    UPLOAD# and a PORTFOLIO# record and must not be counted twice.

    Uploads still awaiting the user's profession/template choice are NOT counted
    (see _SLOT_STATUSES): they are invisible on the dashboard, so counting them
    blocked users with nothing they could delete to recover.

    `exclude_upload_id` drops the upload the caller is currently acting on.
    start_generation MUST pass it: it flips its own record to QUEUED_FOR_AI, so
    without this a user's very first portfolio could be rejected as their second.
    """
    slots = portfolio_upload_ids(user_id) | committed_upload_ids(user_id)
    slots.discard(exclude_upload_id)
    return len(slots)


def portfolio_limit_response(plan: str, used: int, limit: int) -> dict:
    """The 402 for 'you already have as many portfolios as your plan allows'."""
    return limit_response(
        {
            'name': 'portfolios',
            'label': 'portfolios',
            'plan': plan,
            'limit': limit,
            'used': used,
            'resetsAt': None,
        },
        (
            f'Your plan includes {limit} portfolio'
            f'{"" if limit == 1 else "s"}. '
            'Delete the existing one or upgrade to add more.'
        ),
    )


def template_limit_response(plan: str, template_id: str) -> dict:
    """The 402 for 'that template is not on your plan'."""
    return limit_response(
        {
            'name': 'templates',
            'label': 'premium templates',
            'plan': plan,
            'limit': 'free_only',
            'templateId': template_id,
            'resetsAt': None,
        },
        'That template is available on the paid plan.',
    )


# ---------------------------------------------------------------------------
# Daily counters
# ---------------------------------------------------------------------------


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _quota_key(user_id: str, action: str, day: str | None = None) -> dict:
    return {
        'PK': f'USER#{user_id}',
        'SK': f'QUOTA#{day or _utc_day()}#{action}',
    }


def _counter_ttl() -> int:
    """
    Expire the counter well after its day has ended. DynamoDB TTL deletion is
    best-effort and can lag by up to ~48h, so a short TTL risks the record
    vanishing while the day is still live and silently resetting a user's
    allowance. Two days of slack costs nothing and removes that class of bug.
    """
    return int((datetime.now(timezone.utc) + timedelta(days=2)).timestamp())


def resets_at() -> str:
    """ISO timestamp of the next UTC midnight — when daily counters roll over."""
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return tomorrow.isoformat()


def usage(user_id: str, action: str) -> int:
    """Today's consumed count for one action. Returns 0 on any read failure."""
    try:
        result = _table().get_item(
            Key=_quota_key(user_id, action),
            ProjectionExpression='#c',
            ExpressionAttributeNames={'#c': 'count'},
        )
    except Exception as e:
        _log('ERROR', 'Usage read failed', userId=user_id, action=action, error=str(e))
        return 0
    return int((result.get('Item') or {}).get('count', 0))


def usage_today(user_id: str) -> dict:
    """
    Every metered action's consumed count for today, as {action: count}.

    One Query on the QUOTA#{today}# prefix rather than a GetItem per action —
    this runs on every page load of the app, so it stays a single round trip as
    more metered actions are added.
    """
    from boto3.dynamodb.conditions import Key

    counts = {action: 0 for action in _ACTION_LIMIT_KEY}
    prefix = f'QUOTA#{_utc_day()}#'
    try:
        resp = _table().query(
            KeyConditionExpression=(
                Key('PK').eq(f'USER#{user_id}') & Key('SK').begins_with(prefix)
            ),
            ProjectionExpression='SK, #c',
            ExpressionAttributeNames={'#c': 'count'},
        )
    except Exception as e:
        _log('ERROR', 'Usage query failed', userId=user_id, error=str(e))
        return counts

    for item in resp.get('Items', []):
        action = item.get('SK', '').replace(prefix, '')
        if action in counts:
            counts[action] = int(item.get('count', 0))
    return counts


def consume_daily(user_id: str, plan: str, action: str) -> tuple[bool, dict]:
    """
    Atomically claim one unit of today's allowance for `action`.

    Returns (True, info) when the caller may proceed, (False, info) when the
    limit is already spent. `info` describes the limit and is safe to hand
    straight to limit_response().

    The check and the increment are a SINGLE conditional UpdateItem, so
    concurrent invocations cannot both pass the last remaining unit — which
    matters because every one of these actions costs an OpenAI call.
    """
    limit = limits_for(plan).get(_ACTION_LIMIT_KEY[action])
    info = {
        'name': action,
        'label': _ACTION_LABEL.get(action, action),
        'plan': plan,
        'limit': limit,
        'resetsAt': resets_at(),
    }

    if limit is None:  # unlimited — nothing to meter
        info['used'] = None
        return True, info

    try:
        result = _table().update_item(
            Key=_quota_key(user_id, action),
            UpdateExpression='ADD #c :one SET #t = if_not_exists(#t, :ttl)',
            ConditionExpression='attribute_not_exists(#c) OR #c < :limit',
            ExpressionAttributeNames={'#c': 'count', '#t': 'ttl'},
            ExpressionAttributeValues={
                ':one': 1,
                ':limit': limit,
                ':ttl': _counter_ttl(),
            },
            ReturnValues='UPDATED_NEW',
        )
        info['used'] = int(result['Attributes']['count'])
        return True, info
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        info['used'] = limit
        return False, info
    except Exception as e:
        # Metering is unavailable. Fail CLOSED for the same reason get_plan
        # fails to free: an unmetered AI endpoint is an unbounded bill.
        _log('ERROR', 'Quota consume failed — denying',
             userId=user_id, action=action, error=str(e))
        info['used'] = limit
        return False, info


def refund_daily(user_id: str, action: str) -> None:
    """
    Give back one unit after a failure that happened BEFORE any billable work.

    Deliberately not called when the OpenAI request itself succeeded but the
    response was unusable (malformed JSON, empty completion) — that call was
    paid for, so the credit is genuinely spent. Never lets the counter go
    negative, and never raises: a failed refund must not mask the original
    error the caller is already handling.
    """
    try:
        _table().update_item(
            Key=_quota_key(user_id, action),
            UpdateExpression='ADD #c :minus_one',
            ConditionExpression='attribute_exists(#c) AND #c > :zero',
            ExpressionAttributeNames={'#c': 'count'},
            ExpressionAttributeValues={':minus_one': -1, ':zero': 0},
        )
    except Exception as e:
        _log('WARNING', 'Quota refund failed (non-fatal)',
             userId=user_id, action=action, error=str(e))


# ---------------------------------------------------------------------------
# Rejection response
# ---------------------------------------------------------------------------


def daily_limit_message(limit_info: dict) -> str:
    """Consistent copy for every metered action that runs out."""
    return (
        f"You've used all {limit_info.get('limit')} "
        f"{limit_info.get('label', 'requests')} included in your plan today. "
        f"They reset at midnight UTC."
    )


def limit_response(limit_info: dict, message: str, upgrade_to: str = PRO) -> dict:
    """
    The single rejection shape every gate returns, so the frontend can drive one
    upgrade modal from any of them.

    402 Payment Required is the accurate status: the request is well-formed and
    the caller is authenticated and authorized — it is the plan that is short.
    403 would be indistinguishable from the ownership checks these same handlers
    already return.
    """
    return {
        'statusCode': 402,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', '*'),
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'X-Content-Type-Options': 'nosniff',
        },
        'body': json.dumps({
            'error': message,
            'code': 'LIMIT_EXCEEDED',
            'limit': limit_info,
            'upgradeTo': upgrade_to,
        }),
    }
