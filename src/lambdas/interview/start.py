"""
Lambda: POST /interview/start
Creates a new interview session, generates topic plan, and returns the first question.
"""

import json
import uuid
from datetime import datetime, timezone

from interview_utils import (
    _log,
    get_user_profile,
    generate_topic_plan,
    generate_questions_batch,
    generate_base_question,
    create_session,
    sanitize_role_info,
    response,
)

VALID_DIFFICULTIES = {'easy', 'medium', 'hard', 'mix'}
VALID_MODES = {'non-follow-up', 'follow-up'}
VALID_SOURCES = {'resume', 'role'}
VALID_QUESTION_COUNTS = {7, 15, 25}


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    def log(level, msg, **kw):
        _log(level, 'interview_start', msg, correlationId=correlation_id, **kw)

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
        difficulty = str(body.get('difficulty', 'medium')).lower()
        total_questions = int(body.get('totalQuestions', 15))
        mode = str(body.get('mode', 'non-follow-up')).lower()
        source = str(body.get('source', 'resume')).lower()
        role_info = sanitize_role_info(body.get('roleInfo', ''))

        # Input validation
        if difficulty not in VALID_DIFFICULTIES:
            return response(400, {'error': f'difficulty must be one of {sorted(VALID_DIFFICULTIES)}'})
        if total_questions not in VALID_QUESTION_COUNTS:
            return response(400, {'error': f'totalQuestions must be one of {sorted(VALID_QUESTION_COUNTS)}'})
        if mode not in VALID_MODES:
            return response(400, {'error': f'mode must be one of {sorted(VALID_MODES)}'})
        if source not in VALID_SOURCES:
            return response(400, {'error': f'source must be one of {sorted(VALID_SOURCES)}'})
        if source == 'role' and not role_info:
            return response(400, {'error': 'roleInfo is required when source is "role"'})

        # Fetch user profile (if source=resume)
        user_profile = None
        if source == 'resume':
            user_profile = get_user_profile(user_id)
            if not user_profile:
                return response(400, {
                    'error': 'No completed resume found. Please upload and process a resume first, or choose "Job Role" as the source.'
                })

        log('INFO', 'Starting interview session', userId=user_id[:8], mode=mode, difficulty=difficulty)

        # Generate topic plan
        topic_plan = generate_topic_plan(
            profile=user_profile,
            difficulty=difficulty,
            total_questions=total_questions,
            source=source,
            role_info=role_info,
            correlation_id=correlation_id,
        )

        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        first_topic = topic_plan[0]['topic'] if topic_plan else 'General'

        if mode == 'non-follow-up':
            # Generate ALL questions upfront
            questions = generate_questions_batch(
                profile=user_profile,
                topic_plan=topic_plan,
                difficulty=difficulty,
                source=source,
                role_info=role_info,
                correlation_id=correlation_id,
            )
            if not questions:
                return response(500, {'error': 'Failed to generate questions. Please try again.'})

            first_question = questions[0]['question']
            first_topic = questions[0].get('topic', first_topic)

            session = {
                'sessionId': session_id,
                'userId': user_id,
                'mode': mode,
                'difficulty': difficulty,
                'totalQuestions': total_questions,
                'source': source,
                'roleInfo': role_info,
                'status': 'active',
                'questionsAsked': 0,
                'topicPlan': topic_plan,
                'currentTopicIndex': 0,
                'currentFollowUpCount': 0,
                'questions': questions,           # pre-generated list
                'currentQuestion': first_question,
                'currentTopic': first_topic,
                'history': [],
                'skillScores': {},
                'userProfile': user_profile or {},
                'createdAt': now,
                'updatedAt': now,
            }
        else:
            # FOLLOW-UP: generate only the first base question
            first_question = generate_base_question(
                profile=user_profile,
                topic=first_topic,
                difficulty=difficulty,
                source=source,
                role_info=role_info,
                asked_questions=[],
                correlation_id=correlation_id,
            )

            session = {
                'sessionId': session_id,
                'userId': user_id,
                'mode': mode,
                'difficulty': difficulty,
                'totalQuestions': total_questions,
                'source': source,
                'roleInfo': role_info,
                'status': 'active',
                'questionsAsked': 0,
                'topicPlan': topic_plan,
                'currentTopicIndex': 0,
                'currentFollowUpCount': 0,
                'questions': [],                  # dynamic — not pre-generated
                'currentQuestion': first_question,
                'currentTopic': first_topic,
                'history': [],
                'skillScores': {},
                'userProfile': user_profile or {},
                'createdAt': now,
                'updatedAt': now,
            }

        create_session(user_id, session)

        log('INFO', 'Session created', sessionId=session_id[:8])

        return response(200, {
            'sessionId': session_id,
            'question': first_question,
            'questionNumber': 1,
            'totalQuestions': total_questions,
            'topic': first_topic,
        })

    except (ValueError, KeyError, TypeError) as e:
        return response(400, {'error': str(e)})
    except Exception as e:
        _log('ERROR', 'interview_start', 'Unhandled error', correlationId=correlation_id, error=str(e))
        return response(500, {'error': 'Failed to start interview. Please try again.'})
