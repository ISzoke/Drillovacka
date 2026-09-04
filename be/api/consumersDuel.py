"""
================================================================================
 Module: consumersDuel.py
 Description:
        Implements the real-time "duel" (tug-of-war) game — 1v1 / 2v2 typed-answer
        races over Django Channels groups. First consumer in the project to use
        channel_layer groups (broadcast to multiple clients per game), rather than
        the one-client-one-connection pattern used by the speech consumers.
================================================================================
"""

import asyncio
import json
import random
import re

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

from .answerChecker import AnswerChecker
from .models import Answer, DuelGame, DuelParticipant, Example, StudentExample

DISCONNECT_GRACE_SECONDS = 30
QUESTIONS_PER_LANE = 200  # sampled with replacement — plenty for any time limit at typed pace

# asyncio only holds a *weak* reference to a task started with create_task() —
# with nothing else referencing it, the loop is free to garbage-collect it
# mid-run (rare, GC-timing-dependent, but a live game with a stuck rope/timer
# is exactly what it looks like). Keep a strong ref here until each finishes.
_background_tasks = set()


def _spawn_background_task(coro):
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task

# Bot pacing: "medium" answers at the real average solve time for the task
# (same metric shown to students on the task detail page, see get_task_stats'
# global_avg_time). "easy"/"hard" scale that pace; a jitter factor is layered
# on top so the bot doesn't feel metronomic. Bot answers are always correct —
# difficulty is expressed purely through speed, not mistakes.
BOT_DEFAULT_AVG_MS = 8000  # placeholder pace until the task has real solved-attempt data
BOT_DIFFICULTY_PACE = {'easy': 1.5, 'medium': 1.0, 'hard': 0.6}
BOT_DIFFICULTY_XP_MULTIPLIER = {'easy': 0.75, 'medium': 1.0, 'hard': 2.0}
BOT_MIN_DELAY_SECONDS = 1.2


class DuelConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.code = self.scope['url_route']['kwargs']['code'].upper()
        self.group_name = f"duel_{self.code}"
        self.game_id = None
        self.participant_id = None
        await self.accept()

    async def disconnect(self, close_code):
        if self.participant_id is None:
            return
        await database_sync_to_async(_mark_duel_connected)(self.participant_id, False)
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        state = await database_sync_to_async(_serialize_duel_game_by_id)(self.game_id)
        if state:
            await self.channel_layer.group_send(self.group_name, {
                'type': 'duel_message', 'payload': {'type': 'state', **state},
            })

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except (TypeError, ValueError):
            return

        if self.participant_id is None:
            await self._identify(data)
            return

        if data.get('action') == 'answer':
            await self._handle_answer(data.get('answer'))
        elif data.get('action') == 'fill_with_bot':
            await self._fill_with_bot(data.get('difficulty'))

    async def _identify(self, data):
        student_id = data.get('student_id')
        session_id = data.get('session_id')
        resolved = await database_sync_to_async(_resolve_duel_participant)(self.code, student_id, session_id)
        if resolved is None:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'Nepodarilo sa pripojiť k hre'}))
            await self.close()
            return

        self.game_id, self.participant_id = resolved
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await database_sync_to_async(_mark_duel_connected)(self.participant_id, True)

        game, started = await database_sync_to_async(_maybe_start_duel_game)(self.game_id)
        state = await database_sync_to_async(_serialize_duel_game_by_id)(self.game_id)
        await self.channel_layer.group_send(self.group_name, {
            'type': 'duel_message', 'payload': {'type': 'state', **state},
        })

        if started:
            await self._broadcast_game_start(game)
        elif game.status == 'active':
            # Reconnect mid-game — resend this participant's current question privately.
            current = await database_sync_to_async(_current_question_for_participant)(self.participant_id)
            if current:
                await self.send(text_data=json.dumps({'type': 'resume', 'example': current}))

    async def _fill_with_bot(self, difficulty):
        """
        Lets whoever is still waiting alone in a 1v1 room (created the normal
        way, sharing a code that nobody used) start against a bot instead of
        abandoning the room — same game, same code, no need to go back home.
        """
        if difficulty not in ('easy', 'medium', 'hard'):
            difficulty = 'medium'
        bot_participant_id = await database_sync_to_async(_add_bot_to_waiting_game)(
            self.game_id, self.participant_id, difficulty
        )
        if bot_participant_id is None:
            await self.send(text_data=json.dumps({'type': 'error', 'error': 'Nepodarilo sa pridať robota'}))
            return

        state = await database_sync_to_async(_serialize_duel_game_by_id)(self.game_id)
        await self.channel_layer.group_send(self.group_name, {
            'type': 'duel_message', 'payload': {'type': 'state', **state},
        })

        game, started = await database_sync_to_async(_maybe_start_duel_game)(self.game_id)
        if started:
            await self._broadcast_game_start(game)

    async def _broadcast_game_start(self, game):
        questions = await database_sync_to_async(_first_questions_by_slot)(self.game_id)
        await self.channel_layer.group_send(self.group_name, {
            'type': 'duel_message',
            'payload': {'type': 'game_start', 'started_at': game.started_at.isoformat(), 'questions': questions},
        })
        _spawn_background_task(_run_duel_timer(self.group_name, self.game_id))
        if game.vs_bot:
            bot_participant_id = await database_sync_to_async(_get_bot_participant_id)(self.game_id)
            if bot_participant_id is not None:
                _spawn_background_task(_run_bot_player(self.group_name, self.game_id, bot_participant_id, game.bot_difficulty))

    async def _handle_answer(self, answer_payload):
        result = await database_sync_to_async(_apply_duel_answer)(self.game_id, self.participant_id, answer_payload)
        if result:
            await self.channel_layer.group_send(self.group_name, {'type': 'duel_message', 'payload': result})

    async def duel_message(self, event):
        await self.send(text_data=json.dumps(event['payload']))


# ─── Sync DB helpers (wrapped via database_sync_to_async above) ─────────────

def _resolve_duel_participant(code, student_id, session_id):
    try:
        game = DuelGame.objects.get(code=code)
    except DuelGame.DoesNotExist:
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


def _mark_duel_connected(participant_id, connected):
    DuelParticipant.objects.filter(id=participant_id).update(
        connected=connected,
        disconnected_at=None if connected else timezone.now(),
    )


def _serialize_duel_example(example):
    return {'id': example.id, 'example': example.example, 'input_type': example.input_type}


def _serialize_duel_game_by_id(game_id):
    from .views import _serialize_duel_game
    try:
        game = DuelGame.objects.select_related('task').get(id=game_id)
    except DuelGame.DoesNotExist:
        return None
    return _serialize_duel_game(game)


def _maybe_start_duel_game(game_id):
    with transaction.atomic():
        game = DuelGame.objects.select_for_update().select_related('task').get(id=game_id)
        if game.status != 'waiting':
            return game, False

        participants = list(game.participants.all())
        required = 2 if game.mode == '1v1' else 4
        if len(participants) < required or not all(p.connected for p in participants):
            return game, False

        example_ids = list(game.task.example_set.values_list('id', flat=True))
        slots = sorted(set(p.slot for p in participants))
        game.question_orders = {str(s): random.choices(example_ids, k=QUESTIONS_PER_LANE) for s in slots}
        game.status = 'active'
        game.started_at = timezone.now()
        game.save(update_fields=['question_orders', 'status', 'started_at'])
        return game, True


def _first_questions_by_slot(game_id):
    game = DuelGame.objects.get(id=game_id)
    result = {}
    for slot_key, order in game.question_orders.items():
        if order:
            result[slot_key] = _serialize_duel_example(Example.objects.get(id=order[0]))
    return result


def _add_bot_to_waiting_game(game_id, requester_participant_id, difficulty):
    """Converts a still-waiting 1v1 room into a bot game by filling the open
    slot. Returns the new bot participant's id, or None if it can't be done
    (already started, already has a bot, is a 2v2 room, or a race lost to a
    real second player claiming the slot first)."""
    from .views import _BOT_DISPLAY_NAMES

    with transaction.atomic():
        game = DuelGame.objects.select_for_update().get(id=game_id)
        if game.status != 'waiting' or game.mode != '1v1':
            return None
        if not game.participants.filter(id=requester_participant_id).exists():
            return None
        if game.participants.filter(is_bot=True).exists():
            return None

        taken = set(game.participants.values_list('team', 'slot'))
        open_slot = next((ts for ts in (('A', 1), ('B', 1)) if ts not in taken), None)
        if open_slot is None:
            return None

        game.vs_bot = True
        game.bot_difficulty = difficulty
        game.save(update_fields=['vs_bot', 'bot_difficulty'])

        bot = DuelParticipant.objects.create(
            game=game, team=open_slot[0], slot=open_slot[1], is_bot=True, connected=True,
            display_name=_BOT_DISPLAY_NAMES.get(difficulty, 'Robot'),
        )
        return bot.id


def _get_bot_participant_id(game_id):
    bot = DuelParticipant.objects.filter(game_id=game_id, is_bot=True).first()
    return bot.id if bot else None


def _bot_delay_seconds(task_id, difficulty):
    avg_ms = (
        StudentExample.objects
        .filter(task_id=task_id, solved=True, duration__gt=0)
        .aggregate(avg=Avg('duration'))
    )['avg'] or BOT_DEFAULT_AVG_MS
    pace = BOT_DIFFICULTY_PACE.get(difficulty, 1.0)
    jittered_ms = avg_ms * pace * random.uniform(0.8, 1.25)
    return max(BOT_MIN_DELAY_SECONDS, jittered_ms / 1000)


def _current_bot_example(game_id, participant_id):
    try:
        participant = DuelParticipant.objects.select_related('game').get(id=participant_id)
    except DuelParticipant.DoesNotExist:
        return None
    if participant.game.status != 'active':
        return None
    order = participant.game.question_orders.get(str(participant.slot), [])
    if participant.current_index >= len(order):
        return None
    return participant.game.task_id, Example.objects.get(id=order[participant.current_index])


def _bot_answer_payload(example):
    """Mirrors _check_duel_answer's parsing per input_type — the bot always
    submits the actual correct answer; difficulty only affects timing."""
    correct_answer = Answer.objects.get(example_id=example.id).answer
    input_type = (example.input_type or '').upper()

    if input_type == 'FRAC':
        match = re.match(r"\\frac\{(\d+)\}\{(\d+)\}", correct_answer)
        return [match.group(1), match.group(2)] if match else None

    if input_type == 'VAR':
        variables = [v.strip() for v in correct_answer.split(';') if v.strip()]
        return [v.split('=')[1].strip() for v in variables]

    return correct_answer


def _current_question_for_participant(participant_id):
    try:
        participant = DuelParticipant.objects.select_related('game').get(id=participant_id)
    except DuelParticipant.DoesNotExist:
        return None
    order = participant.game.question_orders.get(str(participant.slot), [])
    if participant.current_index >= len(order):
        return None
    return _serialize_duel_example(Example.objects.get(id=order[participant.current_index]))


def _check_duel_answer(example, answer_payload):
    """
    Pure correctness check mirroring InlineAnswerChecker/FractionAnswerChecker/
    VariableAnswerChecker's comparison branches — deliberately NOT calling their
    verifyAnswer()/updateRecord(), which requires a pre-existing StudentExample
    row (practice-session bookkeeping that duel questions don't have).
    """
    correct_answer = Answer.objects.get(example_id=example.id).answer
    input_type = (example.input_type or '').upper()

    if input_type in ('INLINE', 'WORD'):
        student_norm = str(answer_payload or '').replace(' ', '').replace(',', '.')
        correct_norm = correct_answer.replace(' ', '').replace(',', '.')

        if not AnswerChecker.is_valid_answer(correct_norm):
            def _norm_text(s):
                s = s.strip().lower()
                for a, b in (('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'),
                             ('č', 'c'), ('š', 's'), ('ž', 'z'), ('ľ', 'l')):
                    s = s.replace(a, b)
                if s in ('ano', 'je', 'yes', 'true', '1', 'pravda'):
                    return 'ano'
                if s in ('nie', 'nie je', 'neni', 'no', 'false', '0', 'nepravda'):
                    return 'nie'
                return s
            return bool(student_norm) and _norm_text(student_norm) == _norm_text(correct_norm)

        if not student_norm or not AnswerChecker.is_valid_answer(student_norm):
            return False
        return AnswerChecker.compareAnswers(float(student_norm), float(correct_norm))

    if input_type == 'FRAC':
        match = re.match(r"\\frac\{(\d+)\}\{(\d+)\}", correct_answer)
        if not match:
            return False
        correct_value = float(match.group(1)) / float(match.group(2))
        try:
            num, den = answer_payload[0], answer_payload[1]
        except (TypeError, IndexError, KeyError):
            return False
        if not (AnswerChecker.is_valid_answer(str(num)) and AnswerChecker.is_valid_answer(str(den))):
            return False
        student_value = float(str(num).replace(',', '.')) / float(str(den).replace(',', '.'))
        return AnswerChecker.compareAnswers(correct_value, student_value)

    if input_type == 'VAR':
        correct_variables = [v.strip() for v in correct_answer.split(';') if v.strip()]
        correct_values = [float(v.split('=')[1].strip().replace(',', '.')) for v in correct_variables]
        if not isinstance(answer_payload, list) or len(answer_payload) < len(correct_values):
            return False
        for i, correct_value in enumerate(correct_values):
            value = answer_payload[i]
            if not value or not AnswerChecker.is_valid_answer(str(value)):
                return False
            if not AnswerChecker.compareAnswers(correct_value, float(str(value).replace(',', '.'))):
                return False
        return True

    return False


def _apply_duel_answer(game_id, participant_id, answer_payload):
    with transaction.atomic():
        game = DuelGame.objects.select_for_update().get(id=game_id)
        participant = DuelParticipant.objects.select_for_update().get(id=participant_id)

        if game.status != 'active':
            return None

        order = game.question_orders.get(str(participant.slot), [])
        if participant.current_index >= len(order):
            return None

        example = Example.objects.get(id=order[participant.current_index])
        is_correct = _check_duel_answer(example, answer_payload)

        participant.current_index += 1
        if is_correct:
            participant.correct_count += 1
        participant.save(update_fields=['current_index', 'correct_count'])

        sign = 1 if participant.team == 'A' else -1
        game.rope_position += sign if is_correct else -sign

        finished = abs(game.rope_position) >= game.target_steps
        winner = None
        if finished:
            winner = 'A' if game.rope_position > 0 else 'B'
            game.status = 'finished'
            game.winner_team = winner
            game.ended_at = timezone.now()
            game.save(update_fields=['rope_position', 'status', 'winner_team', 'ended_at'])
        else:
            game.save(update_fields=['rope_position'])

        next_example = None
        if not finished and participant.current_index < len(order):
            next_example = _serialize_duel_example(Example.objects.get(id=order[participant.current_index]))

    # Outside the transaction: XP awarding has its own DB writes and shouldn't
    # hold the game/participant row locks any longer than necessary.
    xp_data = None
    if is_correct and participant.student_id:
        from .xp_service import award_xp
        xp_multiplier = BOT_DIFFICULTY_XP_MULTIPLIER.get(game.bot_difficulty, 1.0) if game.vs_bot else 1.0
        xp_data = award_xp(participant.student_id, None, xp_multiplier=xp_multiplier)

    return {
        'type': 'answer_result',
        'team': participant.team,
        'slot': participant.slot,
        'is_correct': is_correct,
        'rope_position': game.rope_position,
        'finished': finished,
        'winner_team': winner,
        'next_example': next_example,
        # Same shape award_xp() returns everywhere else — lets the frontend
        # feed it straight into useGamificationStore.handleXPUpdate().
        'xp': xp_data,
    }


def _duel_timeout_winner(game, participants):
    if game.rope_position > 0:
        return 'A'
    if game.rope_position < 0:
        return 'B'
    a_correct = sum(p.correct_count for p in participants if p.team == 'A')
    b_correct = sum(p.correct_count for p in participants if p.team == 'B')
    if a_correct != b_correct:
        return 'A' if a_correct > b_correct else 'B'
    return random.choice(['A', 'B'])  # still tied — "no draws" rule needs a deterministic pick


def _tick_duel_game(game_id):
    now = timezone.now()
    with transaction.atomic():
        game = DuelGame.objects.select_for_update().get(id=game_id)
        if game.status != 'active':
            return None

        participants = list(game.participants.all())
        winner = None
        for team in ('A', 'B'):
            team_participants = [p for p in participants if p.team == team]
            if team_participants and all(
                (not p.connected) and p.disconnected_at
                and (now - p.disconnected_at).total_seconds() > DISCONNECT_GRACE_SECONDS
                for p in team_participants
            ):
                winner = 'B' if team == 'A' else 'A'
                break

        if winner is None:
            elapsed = (now - game.started_at).total_seconds()
            if elapsed < game.time_limit_seconds:
                return None
            winner = _duel_timeout_winner(game, participants)

        game.status = 'finished'
        game.winner_team = winner
        game.ended_at = now
        game.save(update_fields=['status', 'winner_team', 'ended_at'])

    return {'type': 'game_over', 'winner_team': winner, 'rope_position': game.rope_position}


async def _run_duel_timer(group_name, game_id):
    """
    Owned by whichever consumer instance's connect() transitioned the game to
    'active' (see _maybe_start_duel_game's select_for_update single-winner guard).
    NOTE: this only works correctly with exactly one uvicorn worker process, same
    as the rest of this deployment today — an asyncio task is process-local, so a
    future multi-process deployment would need an external scheduler instead.
    """
    channel_layer = get_channel_layer()
    try:
        while True:
            await asyncio.sleep(1)
            result = await database_sync_to_async(_tick_duel_game)(game_id)
            if result is not None:
                await channel_layer.group_send(group_name, {'type': 'duel_message', 'payload': result})
                return
    except asyncio.CancelledError:
        return


async def _run_bot_player(group_name, game_id, participant_id, difficulty):
    """
    Companion to _run_duel_timer: owned by the same consumer instance that
    started the game (same single-worker constraint applies). Answers the
    bot's own lane one question at a time — correct answer, delay only.
    """
    channel_layer = get_channel_layer()
    try:
        while True:
            current = await database_sync_to_async(_current_bot_example)(game_id, participant_id)
            if current is None:
                return
            task_id, example = current
            delay = await database_sync_to_async(_bot_delay_seconds)(task_id, difficulty)
            await asyncio.sleep(delay)
            answer_payload = await database_sync_to_async(_bot_answer_payload)(example)
            result = await database_sync_to_async(_apply_duel_answer)(game_id, participant_id, answer_payload)
            if result is None:
                return
            await channel_layer.group_send(group_name, {'type': 'duel_message', 'payload': result})
            if result['finished']:
                return
    except asyncio.CancelledError:
        return
