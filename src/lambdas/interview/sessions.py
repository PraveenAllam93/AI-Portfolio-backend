"""
Lambda: GET /interview/sessions
Returns all past interview sessions for the authenticated user, newest first.
"""

from boto3.dynamodb.conditions import Key

from interview_utils import (
    _log,
    _from_dynamodb,
    dynamodb,
    DYNAMODB_TABLE,
    response,
)


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    def log(level, msg, **kw):
        _log(level, 'interview_sessions', msg, correlationId=correlation_id, **kw)

    try:
        user_id = (
            event.get('requestContext', {})
            .get('authorizer', {})
            .get('claims', {})
            .get('sub', '')
        )
        if not user_id:
            return response(401, {'error': 'Unauthorized'})

        table = dynamodb.Table(DYNAMODB_TABLE)
        resp = table.query(
            KeyConditionExpression=(
                Key('PK').eq(f'USER#{user_id}') & Key('SK').begins_with('INTERVIEW#')
            ),
            ProjectionExpression=(
                'sessionId, #st, #mode, difficulty, totalQuestions, questionsAsked, '
                'roleInfo, #src, createdAt, updatedAt, report'
            ),
            ExpressionAttributeNames={
                '#st': 'status',
                '#mode': 'mode',
                '#src': 'source',
            },
            ScanIndexForward=False,  # newest first
        )

        sessions = []
        for item in resp.get('Items', []):
            item = _from_dynamodb(item)
            report = item.get('report') or {}
            sessions.append({
                'sessionId': item.get('sessionId', ''),
                'status': item.get('status', ''),
                'mode': item.get('mode', ''),
                'difficulty': item.get('difficulty', ''),
                'totalQuestions': item.get('totalQuestions', 0),
                'questionsAnswered': item.get('questionsAsked', 0),
                'roleInfo': item.get('roleInfo', ''),
                'source': item.get('source', ''),
                'createdAt': item.get('createdAt', ''),
                'overallScore': report.get('overallScore'),
                'topicScores': report.get('topicScores', {}),
            })

        log('INFO', 'Sessions listed', userId=user_id[:8], count=len(sessions))

        return response(200, {'sessions': sessions})

    except Exception as e:
        _log('ERROR', 'interview_sessions', 'Unhandled error', correlationId=correlation_id, error=str(e))
        return response(500, {'error': 'Failed to fetch sessions. Please try again.'})
