#!/usr/bin/env python3
"""
================================================================================
 Script: load_test_games.py
 Purpose:
        Load-test the duel (tug-of-war) and live-quiz (Kahoot-style) WebSocket
        games — simulates many concurrent players creating/joining games,
        connecting over WS and answering, so you can see how much concurrent
        traffic a single uvicorn worker + Redis channel layer can handle
        before latency/errors climb, and whether memory grows without
        bound over a sustained run.

 IMPORTANT — safety:
        This generates real load (REST + WebSocket + DB writes). Point it at
        your LOCAL docker stack first (default: http://localhost:8000). Only
        run it against the live VPS deliberately, at a small scale, off-peak,
        with someone watching `docker stats`/`htop` live and ready to Ctrl+C —
        never as a first test. This script never deletes anything; games it
        creates are ordinary rows, same as real play.

 Requires: aiohttp, websockets (both already in be/requirements.txt).

 Usage examples:
        # 20 concurrent 1v1 duels against local stack, using task id 5
        python3 load_test_games.py duel --base-url http://localhost:8000 \
            --task-id 5 --games 20 --mode 1v1

        # 8 concurrent 2v2 duels, ramped up over 30s instead of all at once
        python3 load_test_games.py duel --task-id 5 --games 8 --mode 2v2 --ramp 30

        # Kahoot-style quiz: 1 quiz, 60 simulated students, teacher id 1
        python3 load_test_games.py quiz --task-id 5 --teacher-id 1 --players 60
================================================================================
"""

import argparse
import asyncio
import json
import random
import statistics
import string
import time
import uuid

import aiohttp
import websockets


def rand_session_id():
    return str(uuid.uuid4())


async def new_anonymous_session(session, base_url, metrics):
    """The backend's get_user_identity() requires session_id to already exist
    as an AnonymousSession row — real clients get one from POST /session/init/
    (see fe/src/api/apiClient.js's initSession, called from App.vue on first
    load) before ever touching duel/quiz endpoints. Mirror that here."""
    sid = rand_session_id()
    try:
        async with session.post(f"{base_url}/api/session/init/", json={'session_id': sid}) as resp:
            if resp.status not in (200, 201):
                metrics.rest_errors += 1
                return None
            data = await resp.json()
            return data.get('session_id', sid)
    except aiohttp.ClientError:
        metrics.rest_errors += 1
        return None


def ws_base_url(base_url):
    return base_url.replace('https://', 'wss://').replace('http://', 'ws://').rstrip('/')


class Metrics:
    """Shared, thread-unsafe-but-single-event-loop-safe counters."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.games_started = 0
        self.games_finished = 0
        self.answers_sent = 0
        self.answer_latencies_ms = []
        self.ws_errors = 0
        self.ws_disconnects_unexpected = 0
        self.rest_errors = 0
        self.start_time = time.monotonic()

    def summary(self):
        elapsed = time.monotonic() - self.start_time
        lat = self.answer_latencies_ms
        lines = [
            f"\n=== Load test summary ({elapsed:.1f}s) ===",
            f"games started:     {self.games_started}",
            f"games finished:    {self.games_finished}",
            f"answers sent:      {self.answers_sent}",
            f"rest errors:       {self.rest_errors}",
            f"ws errors:         {self.ws_errors}",
            f"unexpected drops:  {self.ws_disconnects_unexpected}",
        ]
        if lat:
            lat_sorted = sorted(lat)
            p50 = lat_sorted[len(lat_sorted) // 2]
            p95 = lat_sorted[min(len(lat_sorted) - 1, int(len(lat_sorted) * 0.95))]
            lines += [
                f"answer round-trip: avg={statistics.mean(lat):.0f}ms  p50={p50:.0f}ms  "
                f"p95={p95:.0f}ms  max={max(lat):.0f}ms",
            ]
        return '\n'.join(lines)


# ─── Duel scenario ────────────────────────────────────────────────────────

async def _duel_client(session, base_url, code, display_name, metrics, think_ms_range):
    """One simulated player in one duel game: joins (or is already the
    founder), opens the WS, answers every question it's shown at a paced
    (human-like) interval until the game ends."""
    session_id = await new_anonymous_session(session, base_url, metrics)
    if session_id is None:
        return
    try:
        async with session.post(f"{base_url}/api/duel/join/", json={
            'session_id': session_id, 'code': code, 'display_name': display_name,
        }) as resp:
            if resp.status not in (200, 201):
                metrics.rest_errors += 1
                return
            await resp.json()
    except aiohttp.ClientError:
        metrics.rest_errors += 1
        return

    uri = f"{ws_base_url(base_url)}/ws/duel/{code}/"
    try:
        async with websockets.connect(uri, open_timeout=15, close_timeout=5) as ws:
            await ws.send(json.dumps({'session_id': session_id}))
            current_question = None
            question_shown_at = None
            finished = False
            while not finished:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=60)
                except asyncio.TimeoutError:
                    break
                data = json.loads(raw)
                mtype = data.get('type')

                if mtype == 'game_start':
                    # questions keyed by slot string; this client doesn't track its
                    # own slot precisely, so just grab any question to keep answering —
                    # good enough for load purposes (server is authoritative either way).
                    qs = data.get('questions') or {}
                    if qs:
                        current_question = next(iter(qs.values()))
                        question_shown_at = time.monotonic()

                elif mtype == 'resume':
                    current_question = data.get('example')
                    question_shown_at = time.monotonic()

                elif mtype == 'answer_result':
                    if data.get('finished'):
                        finished = True
                        metrics.games_finished += 1
                        break
                    current_question = data.get('next_example')
                    question_shown_at = time.monotonic()

                elif mtype == 'game_over':
                    finished = True
                    metrics.games_finished += 1
                    break

                elif mtype == 'error':
                    metrics.ws_errors += 1
                    break

                if current_question and not finished:
                    await asyncio.sleep(random.uniform(*think_ms_range) / 1000)
                    sent_at = time.monotonic()
                    await ws.send(json.dumps({'action': 'answer', 'answer': str(random.randint(0, 999))}))
                    metrics.answers_sent += 1
                    if question_shown_at:
                        metrics.answer_latencies_ms.append((sent_at - question_shown_at) * 1000)
                    current_question = None
    except (websockets.exceptions.ConnectionClosedError, OSError) as e:
        metrics.ws_disconnects_unexpected += 1
        if metrics.verbose:
            print(f"[unexpected drop] {e!r}")
    except Exception as e:
        metrics.ws_errors += 1
        if metrics.verbose:
            print(f"[ws error] {e!r}")


async def _run_one_duel_game(session, base_url, task_id, mode, time_limit, metrics, think_ms_range):
    founder_session_id = await new_anonymous_session(session, base_url, metrics)
    if founder_session_id is None:
        return
    try:
        async with session.post(f"{base_url}/api/duel/create/", json={
            'session_id': founder_session_id,
            'mode': mode, 'visibility': 'private', 'task_id': task_id,
            'time_limit_seconds': time_limit, 'display_name': 'LoadTest Founder',
        }) as resp:
            if resp.status != 201:
                metrics.rest_errors += 1
                return
            data = await resp.json()
    except aiohttp.ClientError:
        metrics.rest_errors += 1
        return

    metrics.games_started += 1
    code = data['code']
    n_more = (1 if mode == '1v1' else 3)
    tasks = [
        asyncio.create_task(_duel_client(session, base_url, code, f"LoadTest {i}", metrics, think_ms_range))
        for i in range(n_more)
    ]
    # Founder also plays its own lane.
    tasks.append(asyncio.create_task(
        _duel_founder_client(session, base_url, founder_session_id, code, metrics, think_ms_range)
    ))
    await asyncio.gather(*tasks, return_exceptions=True)


async def _duel_founder_client(session, base_url, session_id, code, metrics, think_ms_range):
    """Same play loop as _duel_client, but reuses the founder's own session_id
    (already a participant from /duel/create/, no /duel/join/ needed)."""
    uri = f"{ws_base_url(base_url)}/ws/duel/{code}/"
    try:
        async with websockets.connect(uri, open_timeout=15, close_timeout=5) as ws:
            await ws.send(json.dumps({'session_id': session_id}))
            current_question, question_shown_at, finished = None, None, False
            while not finished:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=60)
                except asyncio.TimeoutError:
                    break
                data = json.loads(raw)
                mtype = data.get('type')
                if mtype == 'game_start':
                    qs = data.get('questions') or {}
                    if qs:
                        current_question = next(iter(qs.values()))
                        question_shown_at = time.monotonic()
                elif mtype == 'resume':
                    current_question = data.get('example')
                    question_shown_at = time.monotonic()
                elif mtype == 'answer_result':
                    if data.get('finished'):
                        finished = True
                        break
                    current_question = data.get('next_example')
                    question_shown_at = time.monotonic()
                elif mtype == 'game_over':
                    finished = True
                    break
                elif mtype == 'error':
                    metrics.ws_errors += 1
                    break
                if current_question and not finished:
                    await asyncio.sleep(random.uniform(*think_ms_range) / 1000)
                    sent_at = time.monotonic()
                    await ws.send(json.dumps({'action': 'answer', 'answer': str(random.randint(0, 999))}))
                    metrics.answers_sent += 1
                    if question_shown_at:
                        metrics.answer_latencies_ms.append((sent_at - question_shown_at) * 1000)
                    current_question = None
    except (websockets.exceptions.ConnectionClosedError, OSError) as e:
        metrics.ws_disconnects_unexpected += 1
        if metrics.verbose:
            print(f"[unexpected drop] {e!r}")
    except Exception as e:
        metrics.ws_errors += 1
        if metrics.verbose:
            print(f"[ws error] {e!r}")


async def run_duel_load(args, metrics):
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        launches = []
        for i in range(args.games):
            if args.ramp > 0:
                await asyncio.sleep(args.ramp / max(args.games, 1))
            launches.append(asyncio.create_task(_run_one_duel_game(
                session, args.base_url, args.task_id, args.mode, args.time_limit,
                metrics, (args.think_min_ms, args.think_max_ms),
            )))
        await asyncio.gather(*launches, return_exceptions=True)


# ─── Quiz scenario ────────────────────────────────────────────────────────

async def _quiz_participant(session, base_url, code, name, metrics, think_ms_range):
    session_id = await new_anonymous_session(session, base_url, metrics)
    if session_id is None:
        return
    try:
        async with session.post(f"{base_url}/api/quiz/join/", json={
            'session_id': session_id, 'code': code, 'display_name': name,
        }) as resp:
            if resp.status not in (200, 201):
                metrics.rest_errors += 1
                return
    except aiohttp.ClientError:
        metrics.rest_errors += 1
        return

    uri = f"{ws_base_url(base_url)}/ws/quiz/{code}/"
    try:
        async with websockets.connect(uri, open_timeout=15, close_timeout=5) as ws:
            await ws.send(json.dumps({'session_id': session_id}))
            question_shown_at = None
            answered_this_question = False
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=90)
                except asyncio.TimeoutError:
                    break
                data = json.loads(raw)
                mtype = data.get('type')
                if mtype in ('question', 'resume'):
                    question_shown_at = time.monotonic()
                    answered_this_question = False
                elif mtype == 'state' and data.get('status') == 'finished':
                    break
                if question_shown_at and not answered_this_question and mtype in ('question', 'resume'):
                    await asyncio.sleep(random.uniform(*think_ms_range) / 1000)
                    sent_at = time.monotonic()
                    await ws.send(json.dumps({'action': 'answer', 'answer': str(random.randint(0, 999))}))
                    metrics.answers_sent += 1
                    metrics.answer_latencies_ms.append((sent_at - question_shown_at) * 1000)
                    answered_this_question = True
    except (websockets.exceptions.ConnectionClosedError, OSError) as e:
        metrics.ws_disconnects_unexpected += 1
        if metrics.verbose:
            print(f"[unexpected drop] {e!r}")
    except Exception as e:
        metrics.ws_errors += 1
        if metrics.verbose:
            print(f"[ws error] {e!r}")


async def _quiz_host(base_url, teacher_id, code, n_questions_estimate, metrics):
    uri = f"{ws_base_url(base_url)}/ws/quiz/{code}/"
    async with websockets.connect(uri, open_timeout=15, close_timeout=5) as ws:
        await ws.send(json.dumps({'teacher_id': teacher_id}))
        await asyncio.sleep(2)  # let participants finish connecting
        await ws.send(json.dumps({'action': 'start_game'}))
        rounds = 0
        while rounds < n_questions_estimate:
            await asyncio.sleep(6)  # time-per-question — matches a realistic host pace
            await ws.send(json.dumps({'action': 'reveal'}))
            await asyncio.sleep(2)
            await ws.send(json.dumps({'action': 'next_question'}))
            rounds += 1
        metrics.games_finished += 1


async def run_quiz_load(args, metrics):
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(f"{args.base_url}/api/quiz/create/", json={
            'teacher_id': args.teacher_id, 'task_id': args.task_id,
        }) as resp:
            if resp.status != 201:
                metrics.rest_errors += 1
                print("Failed to create quiz — check --teacher-id / --task-id.")
                return
            data = await resp.json()
        code = data['code']
        total_questions = min(data.get('total_questions', 10), args.max_questions)
        metrics.games_started += 1

        joiners = []
        for i in range(args.players):
            if args.ramp > 0:
                await asyncio.sleep(args.ramp / max(args.players, 1))
            joiners.append(asyncio.create_task(_quiz_participant(
                session, args.base_url, code, f"LoadTest {i}", metrics,
                (args.think_min_ms, args.think_max_ms),
            )))

        host_task = asyncio.create_task(
            _quiz_host(args.base_url, args.teacher_id, code, total_questions, metrics)
        )
        await asyncio.gather(host_task, *joiners, return_exceptions=True)


# ─── CLI ──────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--base-url', default='http://localhost:8000', help='Point this at your LOCAL stack unless you deliberately intend to load the live VPS.')
    p.add_argument('--task-id', type=int, required=True, help='An existing Task id with examples (any sada works).')
    p.add_argument('--think-min-ms', type=int, default=800, help='Simulated fastest human reaction time before answering.')
    p.add_argument('--think-max-ms', type=int, default=2500, help='Simulated slowest human reaction time before answering.')
    p.add_argument('--ramp', type=float, default=0, help='Seconds to spread client startup over, instead of a thundering herd (0 = all at once).')
    p.add_argument('--verbose', action='store_true', help='Print each unexpected disconnect/error as it happens (diagnostic).')
    sub = p.add_subparsers(dest='scenario', required=True)

    duel = sub.add_parser('duel', help='Simulate concurrent duel (tug-of-war) games.')
    duel.add_argument('--games', type=int, default=10, help='Number of concurrent duel games.')
    duel.add_argument('--mode', choices=['1v1', '2v2'], default='1v1')
    duel.add_argument('--time-limit', type=int, default=120, help='Per-game time limit in seconds.')

    quiz = sub.add_parser('quiz', help='Simulate one live Kahoot-style quiz with many participants.')
    quiz.add_argument('--teacher-id', type=int, required=True, help='An existing Teacher id.')
    quiz.add_argument('--players', type=int, default=30, help='Number of concurrent simulated students.')
    quiz.add_argument('--max-questions', type=int, default=8, help='Cap on how many questions the host advances through (a real task set can have 100+; capped so the test run stays short).')

    return p


async def main_async(args):
    metrics = Metrics(verbose=args.verbose)
    print(f"Target: {args.base_url}  scenario: {args.scenario}")
    if args.scenario == 'duel':
        print(f"{args.games} concurrent {args.mode} duel game(s), ramped over {args.ramp}s")
        await run_duel_load(args, metrics)
    else:
        print(f"1 quiz, {args.players} participant(s), ramped over {args.ramp}s")
        await run_quiz_load(args, metrics)
    print(metrics.summary())


def main():
    args = build_parser().parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == '__main__':
    main()
