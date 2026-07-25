"""
Lambda: POST /interview/answer
Evaluates the user's answer and returns feedback + the next question (or completion signal).
"""

import json

from interview_utils import (
    _log,
    sanitize_answer,
    evaluate_answer,
    generate_base_question,
    generate_follow_up_question,
    compute_report,
    get_session,
    update_session,
    get_interview_profile,
    update_interview_profile,
    MAX_FOLLOW_UPS_PER_TOPIC,
    response,
)


def lambda_handler(event, context):
    correlation_id = context.aws_request_id if context else 'local'

    def log(level, msg, **kw):
        _log(level, 'interview_answer', msg, correlationId=correlation_id, **kw)

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
        raw_answer = body.get('answer', '')

        if not session_id:
            return response(400, {'error': 'sessionId is required'})

        # Raw answer validation — allow empty string (user submitted nothing)
        if not isinstance(raw_answer, str):
            return response(400, {'error': 'answer must be a string'})

        # Load and verify session ownership
        session = get_session(user_id, session_id)
        if not session:
            return response(404, {'error': 'Session not found'})
        if session.get('userId') != user_id:
            return response(403, {'error': 'Forbidden'})
        if session.get('status') != 'active':
            return response(400, {'error': 'Session is no longer active'})

        questions_asked = int(session.get('questionsAsked', 0))
        total_questions = int(session.get('totalQuestions', 15))
        current_question = session.get('currentQuestion', '')
        current_topic = session.get('currentTopic', '')
        mode = session.get('mode', 'non-follow-up')
        difficulty = session.get('difficulty', 'medium')
        history = list(session.get('history', []))
        skill_scores = dict(session.get('skillScores', {}))
        topic_plan = list(session.get('topicPlan', []))
        current_topic_index = int(session.get('currentTopicIndex', 0))
        current_follow_up_count = int(session.get('currentFollowUpCount', 0))
        user_profile = session.get('userProfile') or {}
        source = session.get('source', 'resume')
        role_info = session.get('roleInfo', '')

        log('INFO', 'Evaluating answer', sessionId=session_id[:8], questionNum=questions_asked + 1)

        # Evaluate the answer (prompt injection mitigated in evaluate_answer)
        evaluation = evaluate_answer(
            question=current_question,
            raw_answer=raw_answer,
            topic=current_topic,
            difficulty=difficulty,
            correlation_id=correlation_id,
        )

        # Record in history — store raw answer too for user's own reference,
        # but it is NEVER re-fed into subsequent LLM prompts directly
        history_entry = {
            'question': current_question,
            'answer': sanitize_answer(raw_answer),
            'topic': current_topic,
            'score': evaluation['score'],
            'strengths': evaluation['strengths'],
            'weaknesses': evaluation['weaknesses'],
            'idealAnswer': evaluation['idealAnswer'],
        }
        history.append(history_entry)

        # Update skill scores
        if current_topic not in skill_scores:
            skill_scores[current_topic] = []
        skill_scores[current_topic].append(evaluation['score'])

        questions_asked += 1
        is_complete = questions_asked >= total_questions

        if is_complete:
            # Final question answered — generate report, close session, update profile
            report = compute_report(history, skill_scores)
            update_session(user_id, session_id, {
                'status': 'completed',
                'questionsAsked': questions_asked,
                'history': history,
                'skillScores': skill_scores,
                'report': report,
            })
            update_interview_profile(user_id, history, skill_scores)
            log('INFO', 'Session completed', sessionId=session_id[:8], totalAnswered=questions_asked)
            return response(200, {
                'feedback': {
                    'score': evaluation['score'],
                    'strengths': evaluation['strengths'],
                    'weaknesses': evaluation['weaknesses'],
                    'idealAnswer': evaluation['idealAnswer'],
                },
                'isComplete': True,
                'sessionId': session_id,
            })

        # Determine next question
        if mode == 'non-follow-up':
            questions_list = session.get('questions', [])
            next_q_data = questions_list[questions_asked] if questions_asked < len(questions_list) else None
            if not next_q_data:
                # Fallback — shouldn't happen if generation succeeded
                return response(500, {'error': 'Question list exhausted unexpectedly'})
            next_question = next_q_data['question']
            next_topic = next_q_data.get('topic', current_topic)
            new_topic_index = current_topic_index
            new_follow_up_count = 0

        else:
            # FOLLOW-UP MODE — adaptive question generation
            # Check if current topic quota is filled (base + MAX_FOLLOW_UPS_PER_TOPIC)
            topic_total_allowed = (topic_plan[current_topic_index]['count']
                                   if current_topic_index < len(topic_plan) else 1)
            topic_questions_done = current_follow_up_count + 1  # +1 because we just answered

            if (current_follow_up_count >= MAX_FOLLOW_UPS_PER_TOPIC
                    or topic_questions_done >= topic_total_allowed):
                # Move to next topic
                new_topic_index = current_topic_index + 1
                if new_topic_index >= len(topic_plan):
                    new_topic_index = len(topic_plan) - 1  # safety clamp
                new_follow_up_count = 0
                next_topic = topic_plan[new_topic_index]['topic']
                asked_questions = [h['question'] for h in history]
                interview_profile = get_interview_profile(user_id)
                next_question = generate_base_question(
                    profile=user_profile if source == 'resume' else None,
                    topic=next_topic,
                    difficulty=difficulty,
                    source=source,
                    role_info=role_info,
                    asked_questions=asked_questions,
                    interview_profile=interview_profile,
                    correlation_id=correlation_id,
                )
            else:
                # Continue with follow-up in same topic
                new_topic_index = current_topic_index
                new_follow_up_count = current_follow_up_count + 1
                next_topic = current_topic
                next_question = generate_follow_up_question(
                    topic=current_topic,
                    prev_question=current_question,
                    weaknesses=evaluation['weaknesses'],
                    score=evaluation['score'],
                    difficulty=difficulty,
                    follow_up_count=current_follow_up_count,
                    correlation_id=correlation_id,
                )

        update_session(user_id, session_id, {
            'questionsAsked': questions_asked,
            'history': history,
            'skillScores': skill_scores,
            'currentQuestion': next_question,
            'currentTopic': next_topic,
            'currentTopicIndex': new_topic_index,
            'currentFollowUpCount': new_follow_up_count,
        })

        log('INFO', 'Next question generated', sessionId=session_id[:8], nextTopic=next_topic)

        return response(200, {
            'feedback': {
                'score': evaluation['score'],
                'strengths': evaluation['strengths'],
                'weaknesses': evaluation['weaknesses'],
                'idealAnswer': evaluation['idealAnswer'],
            },
            'nextQuestion': {
                'question': next_question,
                'questionNumber': questions_asked + 1,
                'topic': next_topic,
            },
            'isComplete': False,
        })

    except (ValueError, KeyError, TypeError) as e:
        # Log the real cause; return a generic message (no internal detail leak).
        _log('WARNING', 'interview_answer', 'Bad request', correlationId=correlation_id, error=str(e))
        return response(400, {'error': 'Invalid request. Please check your input and try again.'})
    except Exception as e:
        _log('ERROR', 'interview_answer', 'Unhandled error', correlationId=correlation_id, error=str(e))
        return response(500, {'error': 'Failed to process answer. Please try again.'})
