"""
Lambda: POST /interview/exit
Immediately stops the session and generates the final report from answers collected so far.
"""

import json

from interview_utils import (
    _log,
    compute_report,
    get_session,
    update_session,
    update_interview_profile,
    response,
)


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    def log(level, msg, **kw):
        _log(level, 'interview_exit', msg, correlationId=correlation_id, **kw)

    try:
        user_id = (
            event.get('requestContext', {})
            .get('authorizer', {})
            .get('claims', {})
            .get('sub', '')
        )
        if not user_id:
            return response(401, {'error': 'Unauthorized'})

        body = json.loads(event.get('body') or '{}')
        session_id = str(body.get('sessionId', ''))

        if not session_id:
            return response(400, {'error': 'sessionId is required'})

        session = get_session(user_id, session_id)
        if not session:
            return response(404, {'error': 'Session not found'})
        if session.get('userId') != user_id:
            return response(403, {'error': 'Forbidden'})

        # If already completed (e.g. double exit call), just return existing report
        if session.get('status') == 'completed' and session.get('report'):
            return response(200, {
                'sessionId': session_id,
                'report': session['report'],
            })

        history = list(session.get('history', []))
        skill_scores = dict(session.get('skillScores', {}))

        report = compute_report(history, skill_scores)

        update_session(user_id, session_id, {
            'status': 'completed',
            'report': report,
        })
        update_interview_profile(user_id, history, skill_scores)

        log('INFO', 'Session exited', sessionId=session_id[:8], answeredSoFar=len(history))

        return response(200, {
            'sessionId': session_id,
            'report': report,
        })

    except Exception as e:
        _log('ERROR', 'interview_exit', 'Unhandled error', correlationId=correlation_id, error=str(e))
        return response(500, {'error': 'Failed to exit session. Please try again.'})
