"""
Lambda: Get Entitlements

GET /entitlements — Cognito-authenticated.

Returns the caller's plan, its limits, and today's usage, so the frontend can
render locks, star badges, remaining-credit counters and upgrade prompts without
hardcoding a single number. When a limit changes in entitlements.PLANS, the UI
follows on the next deploy with no frontend edit.

The userId always comes from the verified token sub — there is no path
parameter, so a caller can only ever read their own entitlements.

This endpoint is advisory. It tells the UI what to SHOW; it is never what
enforces anything. Every limit is independently re-checked by the Lambda that
performs the action, because a client can call those endpoints directly.
"""

import json
import os

import entitlements as ent

ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')


def _log(level: str, message: str, **kwargs) -> None:
    print(json.dumps({
        "level": level,
        "function": "get_entitlements",
        "message": message,
        **kwargs,
    }))


def _response(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'X-Content-Type-Options': 'nosniff',
            # Plan and usage change as the user works (every publish, every AI
            # call). A cached copy would show stale credit counts, so never
            # allow the browser or any intermediary to reuse this response.
            'Cache-Control': 'no-store',
        },
        'body': json.dumps(body),
    }


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    user_id = (
        event.get('requestContext', {})
        .get('authorizer', {})
        .get('claims', {})
        .get('sub', '')
    )
    if not user_id:
        return _response(403, {'error': 'Forbidden'})

    try:
        plan = ent.get_plan(user_id)
        limits = ent.limits_for(plan)
        used = ent.usage_today(user_id)
        portfolios_used = ent.used_portfolio_slots(user_id)

        return _response(200, {
            'plan': plan,
            'planLabel': limits.get('label', plan),
            'resetsAt': ent.resets_at(),
            'limits': {
                'portfolios': limits.get('portfolios'),
                'aiAnalyzePerDay': limits.get('ai_analyze_per_day'),
                'aiEnhancePerDay': limits.get('ai_enhance_per_day'),
                'publishesPerDay': limits.get('publishes_per_day'),
                'projectImagesPerDay': limits.get('project_images_per_day'),
                'analytics': bool(limits.get('analytics')),
                'allTemplates': limits.get('templates') == 'all',
            },
            'usage': {
                'portfolios': portfolios_used,
                'aiAnalyze': used.get(ent.ACTION_AI_ANALYZE, 0),
                'aiEnhance': used.get(ent.ACTION_AI_ENHANCE, 0),
                'publishes': used.get(ent.ACTION_PUBLISH, 0),
                'projectImages': used.get(ent.ACTION_PROJECT_IMAGE, 0),
            },
            # Sent so the frontend never has to keep its own copy of the free
            # allowlist in sync with the backend's. The star badges are driven
            # straight off this list.
            'freeTemplates': sorted(ent.FREE_TEMPLATES),
        })

    except Exception as e:
        _log('ERROR', 'Entitlements read failed',
             correlationId=correlation_id, userId=user_id, error=str(e))
        return _response(500, {'error': 'Internal server error'})
