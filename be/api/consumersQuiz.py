"""
================================================================================
 Module: consumersQuiz.py
 Description:
        Implements the live, teacher-hosted Kahoot-style quiz over Django
        Channels groups. Structurally mirrors consumersDuel.py (group_add/
        group_send, message-driven identify, select_for_update-guarded state
        transitions, single-uvicorn-worker asyncio task caveat) but the state
        machine is host-paced (one shared question stream, advanced only by
        the teacher) rather than duel's per-lane racing.
================================================================================
"""

import json

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "be.settings")
django.setup()

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import transaction
from django.utils import timezone

from .consumersDuel import _check_duel_answer, _serialize_duel_example
from .models import Answer, Example, QuizGame, QuizParticipant, QuizAnswer

# Kahoot-style speed scoring: correct + instant = 1000, correct after the
# window elapses = 500 (floor), wrong = 0. No fixed per-question timer is
# needed for this — the teacher advances manually, time_taken_ms is just
# elapsed time since the question was shown.
QUIZ_BASE_POINTS = 500
QUIZ_SPEED_BONUS_MAX = 500
QUIZ_SPEED_WINDOW_MS = 10000


def _quiz_points(is_correct, time_taken_ms):
    if not is_correct:
        return 0
    bonus_fraction = max(0.0, 1 - (time_taken_ms / QUIZ_SPEED_WINDOW_MS))
    return QUIZ_BASE_POINTS + round(QUIZ_SPEED_BONUS_MAX * bonus_fraction)


class QuizConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.code = self.scope['url_route']['kwargs']['code'].upper()
        self.group_name = f"quiz_{self.code}"
        self.game_id = None
        self.participant_id = None
        self.role = None
        await self.accept()

    async def disconnect(self, close_code):
        if self.role == 'participant' and self.participant_id is not None:
            await database_sync_to_async(_mark_quiz_connected)(self.participant_id, False)
        if self.game_id is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            state = await database_sync_to_async(_serialize_quiz_game_by_id)(self.game_id)
            if state:
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'quiz_message', 'payload': {'type': 'state', **state},
                })

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except (TypeError, ValueError):
            return

        if self.role is None:
            await self._identify(data)
            return

        action = data.get('action')
        if action == 'answer' and self.role == 'participant':
            await self._handle_answer(data.get('answer'))
        elif action == 'start_game' and self.role == 'host':
            await self._start_game()
        elif action == 'reveal' and self.role == 'host':
            await self._reveal()
        elif action == 'next_question' and self.role == 'host':
            await self._next_question()

    async def _identify(self, data):
        teacher_id = data.get('teacher_id')
        student_id = data.get('student_id')
        session_id = data.get('session_id')

        if teacher_id:
            game_id = await database_sync_to_async(_resolve_quiz_host)(self.code, teacher_id)
            if game_id is None:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'Nepodarilo sa pripojiť ako moderátor'}))
                await self.close()
                return
            self.role = 'host'
            self.game_id = game_id
        else:
            resolved = await database_sync_to_async(_resolve_quiz_participant)(self.code, student_id, session_id)
            if resolved is None:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'Nepodarilo sa pripojiť ku kvízu'}))
                await self.close()
                return
            self.role = 'participant'
            self.game_id, self.participant_id = resolved
            await database_sync_to_async(_mark_quiz_connected)(self.participant_id, True)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        state = await database_sync_to_async(_serialize_quiz_game_by_id)(self.game_id)
        await self.channel_layer.group_send(self.group_name, {
            'type': 'quiz_message', 'payload': {'type': 'state', **state},
        })

        if self.role == 'participant':
            # Reconnect mid-question/review — resend what this participant should
            # currently be looking at (nothing if they already answered this question).
            resume = await database_sync_to_async(_quiz_resume_payload)(self.game_id, self.participant_id)
            if resume:
                await self.send(text_data=json.dumps(resume))

    async def _handle_answer(self, answer_payload):
        result = await database_sync_to_async(_apply_quiz_answer)(self.game_id, self.participant_id, answer_payload)
        if result is None:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'Nepodarilo sa odoslať odpoveď'}))
            return
        await self.send(text_data=json.dumps({
            'type': 'answer_ack', 'is_correct': result['is_correct'], 'points_awarded': result['points_awarded'],
        }))
        await self.channel_layer.group_send(self.group_name, {
            'type': 'quiz_message',
            'payload': {'type': 'answer_count', 'answered_count': result['answered_count']},
        })

    async def _start_game(self):
        payload = await database_sync_to_async(_start_quiz_question)(self.game_id)
        if payload:
            await self.channel_layer.group_send(self.group_name, {'type': 'quiz_message', 'payload': payload})

    async def _reveal(self):
        payload = await database_sync_to_async(_reveal_quiz_question)(self.game_id)
        if payload:
            await self.channel_layer.group_send(self.group_name, {'type': 'quiz_message', 'payload': payload})

    async def _next_question(self):
        payload = await database_sync_to_async(_advance_quiz_question)(self.game_id)
        if payload:
            await self.channel_layer.group_send(self.group_name, {'type': 'quiz_message', 'payload': payload})

    async def quiz_message(self, event):
        await self.send(text_data=json.dumps(event['payload']))


# ─── Sync DB helpers (wrapped via database_sync_to_async above) ─────────────

def _resolve_quiz_host(code, teacher_id):
    try:
        game = QuizGame.objects.get(code=code)
    except QuizGame.DoesNotExist:
        return None
    if str(game.teacher_id) != str(teacher_id):
        return None
    return game.id


def _resolve_quiz_participant(code, student_id, session_id):
    try:
        game = QuizGame.objects.get(code=code)
    except QuizGame.DoesNotExist:
        return None
    participants = game.participants.all()
    if student_id:
        participant = participants.filter(student_id=student_id).first()
    elif session_id:
        participant = participants.filter(anonymous_session__session_id=session_id).first()
    else:
        participant = None
    if not participant:
        return None
    return game.id, participant.id


def _mark_quiz_connected(participant_id, connected):
    QuizParticipant.objects.filter(id=participant_id).update(
        connected=connected,
        disconnected_at=None if connected else timezone.now(),
    )


def _serialize_quiz_game_by_id(game_id):
    from .views import _serialize_quiz_game
    try:
        game = QuizGame.objects.select_related('task').get(id=game_id)
    except QuizGame.DoesNotExist:
        return None
    return _serialize_quiz_game(game)


def _quiz_leaderboard(game):
    return sorted(
        [{'id': p.id, 'display_name': p.display_name, 'score': p.score} for p in game.participants.all()],
        key=lambda p: -p['score']
    )


def _quiz_resume_payload(game_id, participant_id):
    try:
        game = QuizGame.objects.get(id=game_id)
        participant = QuizParticipant.objects.get(id=participant_id)
    except (QuizGame.DoesNotExist, QuizParticipant.DoesNotExist):
        return None

    idx = game.current_question_index
    if game.status == 'question':
        if idx >= len(game.question_order) or QuizAnswer.objects.filter(participant=participant, question_index=idx).exists():
            return None
        example = Example.objects.get(id=game.question_order[idx])
        return {
            'type': 'question', 'index': idx, 'total': len(game.question_order),
            'example': _serialize_duel_example(example),
            'started_at': game.question_started_at.isoformat() if game.question_started_at else None,
        }

    if game.status == 'review':
        example = Example.objects.get(id=game.question_order[idx])
        correct_answer = Answer.objects.get(example_id=example.id).answer
        return {
            'type': 'review', 'index': idx, 'correct_answer': correct_answer,
            'answered_count': QuizAnswer.objects.filter(participant__game=game, question_index=idx).count(),
            'participant_count': game.participants.count(),
            'leaderboard': _quiz_leaderboard(game),
        }

    return None


def _apply_quiz_answer(game_id, participant_id, answer_payload):
    with transaction.atomic():
        game = QuizGame.objects.select_for_update().get(id=game_id)
        participant = QuizParticipant.objects.select_for_update().get(id=participant_id)

        if game.status != 'question':
            return None
        idx = game.current_question_index
        if idx >= len(game.question_order):
            return None
        if QuizAnswer.objects.filter(participant=participant, question_index=idx).exists():
            return None

        example = Example.objects.get(id=game.question_order[idx])
        is_correct = _check_duel_answer(example, answer_payload)
        elapsed_ms = 0
        if game.question_started_at:
            elapsed_ms = max(0, int((timezone.now() - game.question_started_at).total_seconds() * 1000))
        points = _quiz_points(is_correct, elapsed_ms)

        QuizAnswer.objects.create(
            participant=participant, question_index=idx, example=example,
            is_correct=is_correct, time_taken_ms=elapsed_ms, points_awarded=points,
        )
        participant.score += points
        participant.save(update_fields=['score'])

        answered_count = QuizAnswer.objects.filter(participant__game=game, question_index=idx).count()

    return {'is_correct': is_correct, 'points_awarded': points, 'answered_count': answered_count}


def _start_quiz_question(game_id):
    with transaction.atomic():
        game = QuizGame.objects.select_for_update().get(id=game_id)
        if game.status != 'waiting' or not game.question_order:
            return None
        game.status = 'question'
        game.current_question_index = 0
        game.question_started_at = timezone.now()
        game.started_at = timezone.now()
        game.save(update_fields=['status', 'current_question_index', 'question_started_at', 'started_at'])
        example = Example.objects.get(id=game.question_order[0])
    return {
        'type': 'question', 'index': 0, 'total': len(game.question_order),
        'example': _serialize_duel_example(example), 'started_at': game.question_started_at.isoformat(),
    }


def _reveal_quiz_question(game_id):
    with transaction.atomic():
        game = QuizGame.objects.select_for_update().get(id=game_id)
        if game.status != 'question':
            return None
        game.status = 'review'
        game.save(update_fields=['status'])
        idx = game.current_question_index
        example = Example.objects.get(id=game.question_order[idx])
        correct_answer = Answer.objects.get(example_id=example.id).answer
        answered_count = QuizAnswer.objects.filter(participant__game=game, question_index=idx).count()
        participant_count = game.participants.count()
        leaderboard = _quiz_leaderboard(game)
    return {
        'type': 'review', 'index': idx, 'correct_answer': correct_answer,
        'answered_count': answered_count, 'participant_count': participant_count,
        'leaderboard': leaderboard,
    }


def _advance_quiz_question(game_id):
    with transaction.atomic():
        game = QuizGame.objects.select_for_update().get(id=game_id)
        if game.status != 'review':
            return None

        next_index = game.current_question_index + 1
        if next_index >= len(game.question_order):
            game.status = 'finished'
            game.ended_at = timezone.now()
            game.save(update_fields=['status', 'ended_at'])
            return {'type': 'game_over', 'leaderboard': _quiz_leaderboard(game)}

        game.current_question_index = next_index
        game.status = 'question'
        game.question_started_at = timezone.now()
        game.save(update_fields=['current_question_index', 'status', 'question_started_at'])
        example = Example.objects.get(id=game.question_order[next_index])
    return {
        'type': 'question', 'index': next_index, 'total': len(game.question_order),
        'example': _serialize_duel_example(example), 'started_at': game.question_started_at.isoformat(),
    }
