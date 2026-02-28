"""
Lambda: Portfolio Analytics

GET /portfolio/{userId}/analytics — Cognito-authenticated.

Returns aggregated view statistics for the portfolio owner's own portfolio.
Only the owner can access their analytics (path userId must equal token sub).

Response shape:
  {
    "totalViews": 1247,
    "last7Days": 89,
    "last30Days": 312,
    "byCountry": {"IN": 450, "US": 380, ...},
    "bySource":  {"direct": 450, "linkedin": 380, ...},
    "byDevice":  {"desktop": 890, "mobile": 357},
    "timeline":  [{"date": "2026-02-01", "count": 45}, ...]
  }

Security notes:
  - userId in path MUST match the Cognito token sub — enforced at the top
    of the handler before any DynamoDB access.
  - IAM for this Lambda is scoped to dynamodb:Query on PORTFOLIO#* keys.
"""

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

# ---------------------------------------------------------------------------
# Structured logger
# ---------------------------------------------------------------------------


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "get_analytics",
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
    path_user_id = unquote(
        (event.get('pathParameters') or {}).get('userId', '')
    )
    token_sub = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )

    if not path_user_id or path_user_id != token_sub:
        _log('WARNING', 'Analytics auth mismatch',
             correlationId=correlation_id,
             pathUserId=path_user_id[:8] if path_user_id else '',
             tokenSub=token_sub[:8] if token_sub else '')
        return _response(403, {'error': 'Forbidden'})

    try:
        table = dynamodb.Table(DYNAMODB_TABLE)

        # Query all VIEW# records for this portfolio owner.
        # PK = PORTFOLIO#{userId}, SK begins_with VIEW#
        items = []
        kwargs = dict(
            KeyConditionExpression=(
                Key('PK').eq(f'PORTFOLIO#{path_user_id}')
                & Key('SK').begins_with('VIEW#')
            ),
            ProjectionExpression=(
                'viewedAt, country, referrerSource, deviceType, '
                'portfolioVersion, ttfb, cacheHit, visitorHash'
            ),
        )
        while True:
            response = table.query(**kwargs)
            items.extend(response.get('Items', []))
            if 'LastEvaluatedKey' not in response:
                break
            kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

        # ------------------------------------------------------------------
        # Aggregation
        # ------------------------------------------------------------------
        total_views = len(items)

        now_utc = datetime.now(timezone.utc)
        cutoff_7d = (now_utc - timedelta(days=7)).isoformat()
        cutoff_30d = (now_utc - timedelta(days=30)).isoformat()

        last_7d = sum(
            1 for i in items if (i.get('viewedAt') or '') >= cutoff_7d
        )
        last_30d = sum(
            1 for i in items if (i.get('viewedAt') or '') >= cutoff_30d
        )

        by_country = dict(
            Counter(i.get('country', 'unknown') for i in items)
        )
        by_source = dict(
            Counter(i.get('referrerSource', 'other') for i in items)
        )
        by_device = dict(
            Counter(i.get('deviceType', 'unknown') for i in items)
        )

        # Daily timeline for the last 90 days (suitable for a line graph).
        cutoff_90d = (now_utc - timedelta(days=90)).date().isoformat()
        daily: dict[str, int] = {}
        for item in items:
            viewed_at = item.get('viewedAt', '')
            if viewed_at >= cutoff_90d:
                day = viewed_at[:10]  # "YYYY-MM-DD"
                daily[day] = daily.get(day, 0) + 1

        timeline = [
            {'date': d, 'count': c}
            for d, c in sorted(daily.items())
        ]

        # ------------------------------------------------------------------
        # Extended aggregations (fields added in analytics enrichment)
        # All are backward-compatible: old records without these fields
        # simply produce falsy values which are excluded from counts.
        # ------------------------------------------------------------------

        # Hour-of-day breakdown (0–23)
        by_hour: dict[int, int] = {}
        for i in items:
            va = i.get('viewedAt', '')
            if len(va) >= 13:
                try:
                    h = int(va[11:13])
                    by_hour[h] = by_hour.get(h, 0) + 1
                except ValueError:
                    pass

        # Day-of-week breakdown (Mon … Sun)
        by_dow: dict[str, int] = {}
        for i in items:
            va = i.get('viewedAt', '')
            if va:
                try:
                    dow = datetime.fromisoformat(va).strftime('%a')
                    by_dow[dow] = by_dow.get(dow, 0) + 1
                except ValueError:
                    pass

        # Unique visitors — count of distinct daily visitor hashes
        unique_visitors = len(
            {i.get('visitorHash') for i in items if i.get('visitorHash')}
        )

        # Average time-to-first-byte (seconds)
        ttfb_vals = [
            float(i['ttfb'])
            for i in items
            if i.get('ttfb') and float(i['ttfb']) > 0
        ]
        avg_ttfb = (
            round(sum(ttfb_vals) / len(ttfb_vals), 3)
            if ttfb_vals else None
        )

        # Cache hit rate (%)
        cache_hits = sum(1 for i in items if i.get('cacheHit'))
        cache_hit_rate = (
            round(cache_hits / total_views * 100, 1)
            if total_views else 0.0
        )

        # Views per portfolio version
        by_version = dict(
            Counter(i.get('portfolioVersion', 'v1') for i in items)
        )

        # Best time to share: peak hour + peak day-of-week
        best_time = None
        if by_hour:
            best_hour = max(by_hour, key=by_hour.get)
            best_dow = max(by_dow, key=by_dow.get) if by_dow else None
            best_time = {
                'hour': best_hour,
                'dayOfWeek': best_dow,
            }

        _log('INFO', 'Analytics fetched',
             correlationId=correlation_id,
             userId=path_user_id,
             totalViews=total_views)

        return _response(200, {
            'totalViews': total_views,
            'last7Days': last_7d,
            'last30Days': last_30d,
            'byCountry': by_country,
            'bySource': by_source,
            'byDevice': by_device,
            'timeline': timeline,
            'uniqueVisitors': unique_visitors,
            'avgTtfb': avg_ttfb,
            'cacheHitRate': cache_hit_rate,
            'byHour': by_hour,
            'byDayOfWeek': by_dow,
            'byVersion': by_version,
            'bestTimeToShare': best_time,
        })

    except Exception as e:
        _log('ERROR', 'Analytics error',
             correlationId=correlation_id,
             userId=path_user_id,
             error=str(e))
        return _response(500, {'error': 'Internal server error'})
