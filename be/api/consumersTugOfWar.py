"""
================================================================================
 Module: consumersTugOfWar.py
 Description:
        Implements the team version of the "duel" tug-of-war game — up to
        max_team_size students per side (default 30), each solving their OWN
        randomized queue of examples at their own pace (unlike duel's fixed
        1v1/2v2 lanes). Every correct answer pulls the shared rope toward that
        student's team. Host-paced start like consumersQuiz.py (the teacher
        starts the round and can shuffle teams before start), but the actual
        race is continuous and self-paced like consumersDuel.py, with an
        optional time-limit background timer reused from that same pattern.
================================================================================
"""

import asyncio
import json
import random

import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "be.settings")
django.setup()

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from .consumersDuel import _check_duel_answer, _serialize_duel_example, _spawn_background_task
from .models import Example, TugOfWarGame, TugOfWarParticipant, TugOfWarAnswer

QUESTIONS_PER_PLAYER = 200  # sampled with replacement — plenty for any time limit at typed pace


class TugOfWarConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.code = self.scope['url_route']['kwargs']['code'].upper()
        self.group_name = f"tow_{self.code}"
        self.game_id = None
        self.participant_id = None
        self.role = None
        await self.accept()

    async def disconnect(self, close_code):
        if self.role == 'participant' and self.participant_id is not None:
            await database_sync_to_async(_mark_tow_connected)(self.participant_id, False)
        if self.game_id is not None:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            state = await database_sync_to_async(_serialize_tow_game_by_id)(self.game_id)
            if state:
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'tow_message', 'payload': {'type': 'state', **state},
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
        elif action == 'randomize_teams' and self.role == 'host':
            await self._randomize_teams()
        elif action == 'reveal_worst' and self.role == 'host':
            await self._reveal_worst()

    async def _identify(self, data):
        teacher_id = data.get('teacher_id')
        student_id = data.get('student_id')
        session_id = data.get('session_id')

        if teacher_id:
            game_id = await database_sync_to_async(_resolve_tow_host)(self.code, teacher_id)
            if game_id is None:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'Nepodarilo sa pripojiť ako moderátor'}))
                await self.close()
                return
            self.role = 'host'
            self.game_id = game_id
        else:
            resolved = await database_sync_to_async(_resolve_tow_participant)(self.code, student_id, session_id)
            if resolved is None:
                await self.send(text_data=json.dumps({'type': 'error', 'error': 'Nepodarilo sa pripojiť k hre'}))
                await self.close()
                return
            self.role = 'participant'
            self.game_id, self.participant_id = resolved
            await database_sync_to_async(_mark_tow_connected)(self.participant_id, True)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        state = await database_sync_to_async(_serialize_tow_game_by_id)(self.game_id)
        await self.channel_layer.group_send(self.group_name, {
            'type': 'tow_message', 'payload': {'type': 'state', **state},
        })

        if self.role == 'participant' and state and state.get('status') == 'active':
            # Reconnect mid-game — resend this participant's current question privately.
            current = await database_sync_to_async(_current_question_for_tow_participant)(self.participant_id)
            if current:
                await self.send(text_data=json.dumps({'type': 'resume', 'example': current}))

    async def _handle_answer(self, answer_payload):
        result = await database_sync_to_async(_apply_tow_answer)(self.game_id, self.participant_id, answer_payload)
        if result:
            await self.channel_layer.group_send(self.group_name, {'type': 'tow_message', 'payload': result})

    async def _start_game(self):
        game, questions = await database_sync_to_async(_start_tow_game)(self.game_id)
        if game is None:
            return
        await self.channel_layer.group_send(self.group_name, {
            'type': 'tow_message',
            'payload': {'type': 'game_start', 'started_at': game.started_at.isoformat(), 'questions': questions},
        })
        if game.end_mode == 'time':
            _spawn_background_task(_run_tow_timer(self.group_name, self.game_id))

    async def _randomize_teams(self):
        state = await database_sync_to_async(_randomize_tow_teams)(self.game_id)
        if state:
            await self.channel_layer.group_send(self.group_name, {
                'type': 'tow_message', 'payload': {'type': 'state', **state},
            })

    async def _reveal_worst(self):
        payload = await database_sync_to_async(_reveal_tow_worst)(self.game_id)
        if payload:
            await self.channel_layer.group_send(self.group_name, {'type': 'tow_message', 'payload': payload})

    async def tow_message(self, event):
        await self.send(text_data=json.dumps(event['payload']))


# ─── Sync DB helpers (wrapped via database_sync_to_async above) ─────────────

def _resolve_tow_host(code, teacher_id):
    try:
        game = TugOfWarGame.objects.get(code=code)
    except TugOfWarGame.DoesNotExist:
        return None
    if str(game.teacher_id) != str(teacher_id):
        return None
    return game.id


def _resolve_tow_participant(code, student_id, session_id):
    try:
        game = TugOfWarGame.objects.get(code=code)
    except TugOfWarGame.DoesNotExist:
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


def _mark_tow_connected(participant_id, connected):
    TugOfWarParticipant.objects.filter(id=participant_id).update(
        connected=connected,
        disconnected_at=None if connected else timezone.now(),
    )


def _serialize_tow_game_by_id(game_id):
    from .views import _serialize_tow_game
    try:
        game = TugOfWarGame.objects.select_related('task').get(id=game_id)
    except TugOfWarGame.DoesNotExist:
        return None
    return _serialize_tow_game(game)


def _current_question_for_tow_participant(participant_id):
    try:
        participant = TugOfWarParticipant.objects.get(id=participant_id)
    except TugOfWarParticipant.DoesNotExist:
        return None
    order = participant.question_order
    if participant.current_index >= len(order):
        return None
    return _serialize_duel_example(Example.objects.get(id=order[participant.current_index]))


def _start_tow_game(game_id):
    with transaction.atomic():
        game = TugOfWarGame.objects.select_for_update().select_related('task').get(id=game_id)
        if game.status != 'waiting':
            return None, None

        participants = list(game.participants.select_for_update())
        if not any(p.team == 'A' for p in participants) or not any(p.team == 'B' for p in participants):
            return None, None

        example_ids = list(game.task.example_set.values_list('id', flat=True))
        now = timezone.now()
        questions = {}
        for p in participants:
            p.question_order = random.choices(example_ids, k=QUESTIONS_PER_PLAYER)
            p.current_index = 0
            p.current_question_started_at = now
            p.save(update_fields=['question_order', 'current_index', 'current_question_started_at'])
            questions[str(p.id)] = _serialize_duel_example(Example.objects.get(id=p.question_order[0]))

        game.status = 'active'
        game.started_at = now
        game.save(update_fields=['status', 'started_at'])
        return game, questions


def _randomize_tow_teams(game_id):
    with transaction.atomic():
        game = TugOfWarGame.objects.select_for_update().get(id=game_id)
        if game.status != 'waiting':
            return None
        participants = list(game.participants.select_for_update())
        random.shuffle(participants)
        half = len(participants) // 2
        for i, p in enumerate(participants):
            p.team = 'A' if i < half else 'B'
        TugOfWarParticipant.objects.bulk_update(participants, ['team'])

    from .views import _serialize_tow_game
    return _serialize_tow_game(TugOfWarGame.objects.select_related('task').get(id=game_id))


def _tow_ranked_team(game, team):
    participants = TugOfWarParticipant.objects.filter(game=game, team=team)
    stats = []
    for p in participants:
        avg_ms = p.answers.filter(is_correct=True).aggregate(avg=Avg('time_taken_ms'))['avg']
        stats.append({
            'id': p.id, 'display_name': p.display_name, 'is_student': p.student_id is not None,
            'correct_count': p.correct_count, 'wrong_count': p.wrong_count,
            'avg_time_ms': round(avg_ms) if avg_ms is not None else None,
        })
    # Best first: most correct, then fastest average time on correct answers.
    stats.sort(key=lambda s: (-s['correct_count'], s['avg_time_ms'] if s['avg_time_ms'] is not None else float('inf')))
    return stats


def _tow_results(game):
    ranked_a = _tow_ranked_team(game, 'A')
    ranked_b = _tow_ranked_team(game, 'B')
    return {
        'top': {'A': ranked_a[:3], 'B': ranked_b[:3]},
        'worst': {'A': list(reversed(ranked_a))[:3], 'B': list(reversed(ranked_b))[:3]},
    }


def _apply_tow_answer(game_id, participant_id, answer_payload):
    with transaction.atomic():
        game = TugOfWarGame.objects.select_for_update().get(id=game_id)
        participant = TugOfWarParticipant.objects.select_for_update().get(id=participant_id)

        if game.status != 'active':
            return None

        order = participant.question_order
        if participant.current_index >= len(order):
            return None

        example = Example.objects.get(id=order[participant.current_index])
        is_correct = _check_duel_answer(example, answer_payload)

        now = timezone.now()
        elapsed_ms = 0
        if participant.current_question_started_at:
            elapsed_ms = max(0, int((now - participant.current_question_started_at).total_seconds() * 1000))
        TugOfWarAnswer.objects.create(
            participant=participant, example=example, is_correct=is_correct, time_taken_ms=elapsed_ms,
        )

        participant.current_index += 1
        if is_correct:
            participant.correct_count += 1
        else:
            participant.wrong_count += 1
        participant.current_question_started_at = now
        participant.save(update_fields=['current_index', 'correct_count', 'wrong_count', 'current_question_started_at'])

        # Only correct answers pull the rope — a wrong guess just costs the
        # question, it doesn't drag the team's own rope backward.
        if is_correct:
            sign = 1 if participant.team == 'A' else -1
            game.rope_position += sign

        finished = False
        winner = None
        if game.end_mode == 'target' and game.target_diff and abs(game.rope_position) >= game.target_diff:
            finished = True
            winner = 'A' if game.rope_position > 0 else 'B'
            game.status = 'finished'
            game.winner_team = winner
            game.ended_at = now
            game.save(update_fields=['rope_position', 'status', 'winner_team', 'ended_at'])
        else:
            game.save(update_fields=['rope_position'])

        next_example = None
        if not finished and participant.current_index < len(order):
            next_example = _serialize_duel_example(Example.objects.get(id=order[participant.current_index]))

        results = _tow_results(game) if finished else None

    return {
        'type': 'answer_result',
        'participant_id': participant_id,
        'team': participant.team,
        'is_correct': is_correct,
        'rope_position': game.rope_position,
        'correct_count': participant.correct_count,
        'wrong_count': participant.wrong_count,
        'finished': finished,
        'winner_team': winner,
        'next_example': next_example,
        'results': results,
    }


def _tick_tow_game(game_id):
    now = timezone.now()
    with transaction.atomic():
        game = TugOfWarGame.objects.select_for_update().get(id=game_id)
        if game.status != 'active':
            return None
        elapsed = (now - game.started_at).total_seconds()
        if elapsed < game.time_limit_seconds:
            return None

        winner = 'A' if game.rope_position > 0 else 'B' if game.rope_position < 0 else None
        game.status = 'finished'
        game.winner_team = winner
        game.ended_at = now
        game.save(update_fields=['status', 'winner_team', 'ended_at'])
        results = _tow_results(game)

    return {'type': 'game_over', 'winner_team': winner, 'rope_position': game.rope_position, 'results': results}


def _reveal_tow_worst(game_id):
    try:
        game = TugOfWarGame.objects.get(id=game_id)
    except TugOfWarGame.DoesNotExist:
        return None
    if game.status != 'finished':
        return None
    return {'type': 'worst_performers', 'worst': _tow_results(game)['worst']}


async def _run_tow_timer(group_name, game_id):
    """Owned by the consumer instance whose host started the round — same
    single-uvicorn-worker constraint as _run_duel_timer (see consumersDuel.py)."""
    channel_layer = get_channel_layer()
    try:
        while True:
            await asyncio.sleep(1)
            result = await database_sync_to_async(_tick_tow_game)(game_id)
            if result is not None:
                await channel_layer.group_send(group_name, {'type': 'tow_message', 'payload': result})
                return
    except asyncio.CancelledError:
        return
