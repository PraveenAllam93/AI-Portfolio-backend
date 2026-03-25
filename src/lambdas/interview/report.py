"""
Lambda: GET /interview/{sessionId}/report
Returns the final report for a completed interview session.
"""

from urllib.parse import unquote

from interview_utils import (
    _log,
    compute_report,
    get_session,
    response,
)


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    def log(level, msg, **kw):
        _log(level, 'interview_report', msg, correlationId=correlation_id, **kw)

    try:
        user_id = (
            event.get('requestContext', {})
            .get('authorizer', {})
            .get('claims', {})
            .get('sub', '')
        )
        if not user_id:
            return response(401, {'error': 'Unauthorized'})

        path_params = event.get('pathParameters') or {}
        session_id = unquote(path_params.get('sessionId', ''))

        if not session_id:
            return response(400, {'error': 'sessionId path parameter is required'})

        session = get_session(user_id, session_id)
        if not session:
            return response(404, {'error': 'Session not found'})
        if session.get('userId') != user_id:
            return response(403, {'error': 'Forbidden'})

        # Return cached report if available
        if session.get('report'):
            return response(200, {
                'sessionId': session_id,
                'status': session.get('status'),
                'report': session['report'],
                'mode': session.get('mode'),
                'difficulty': session.get('difficulty'),
                'createdAt': session.get('createdAt'),
            })

        # Compute on-the-fly for sessions that completed without explicit exit
        history = list(session.get('history', []))
        skill_scores = dict(session.get('skillScores', {}))
        report = compute_report(history, skill_scores)

        log('INFO', 'Report fetched', sessionId=session_id[:8])

        return response(200, {
            'sessionId': session_id,
            'status': session.get('status'),
            'report': report,
            'mode': session.get('mode'),
            'difficulty': session.get('difficulty'),
            'createdAt': session.get('createdAt'),
        })

    except Exception as e:
        _log('ERROR', 'interview_report', 'Unhandled error', correlationId=correlation_id, error=str(e))
        return response(500, {'error': 'Failed to fetch report. Please try again.'})
