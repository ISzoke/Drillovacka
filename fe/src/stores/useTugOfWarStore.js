/**
 * ================================================================================
 * File: useTugOfWarStore.js
 * Description:
 *       Pinia store for the team "tug of war" live game — REST create/join
 *       plus the WebSocket connection to /ws/tug-of-war/<code>/. Mirrors
 *       useQuizStore's host/participant role split (teacher starts the round
 *       and can shuffle teams / reveal the worst performers) combined with
 *       useDuelStore's self-paced answer/rope flow.
 * ================================================================================
 */

import { defineStore } from 'pinia';
import { ref } from 'vue';
import { useAuthStore } from './useAuthStore';
import { getSessionId } from '@/utils/sessionManager';
import { createTugOfWar, joinTugOfWar, getTugOfWarState } from '@/api/apiClient';

const MAX_RECONNECT_ATTEMPTS = 15;
const RECONNECT_BASE_DELAY_MS = 1000;

function myTowIdentity(asHost) {
  const auth = useAuthStore();
  if (asHost) {
    return { teacher_id: auth.id };
  }
  if (auth.isAuthenticated && auth.role === 'student' && auth.id) {
    return { student_id: auth.id, session_id: null };
  }
  return { student_id: null, session_id: getSessionId() };
}

export const useTugOfWarStore = defineStore('tugOfWar', () => {
  let ws = null;
  let reconnectTimer = null;
  let reconnectAttempts = 0;

  const code = ref(null);
  const role = ref(null); // 'host' | 'participant'
  const participantId = ref(null);
  const myTeam = ref(null);

  const roomState = ref(null); // latest 'state' broadcast: status, end_mode, rope_position, team_a[], team_b[], ...
  const currentQuestion = ref(null); // { id, example, input_type }
  const lastResult = ref(null); // { isCorrect, at }
  const results = ref(null); // { top: {A,B}, worst: {A,B} } — worst only present once host reveals it
  const connectionStatus = ref('idle'); // idle | connecting | open | reconnecting | closed
  const errorMessage = ref(null);

  async function createGame({ taskId, endMode, timeLimitSeconds, targetDiff, maxTeamSize }) {
    const auth = useAuthStore();
    const data = await createTugOfWar(auth.id, { taskId, endMode, timeLimitSeconds, targetDiff, maxTeamSize });
    code.value = data.code;
    roomState.value = data;
    return data;
  }

  async function joinGame(joinCode, team, displayName) {
    const identity = myTowIdentity(false);
    const data = await joinTugOfWar(identity.student_id, joinCode, team, displayName);
    code.value = data.code;
    roomState.value = data;
    if (data.you) {
      participantId.value = data.you.participant_id;
      myTeam.value = data.you.team;
    }
    return data;
  }

  async function refreshState(existingCode) {
    const data = await getTugOfWarState(existingCode || code.value);
    roomState.value = data;
    return data;
  }

  function connect(targetCode, asHost) {
    if (targetCode) code.value = targetCode;
    if (!code.value) return;
    role.value = asHost ? 'host' : 'participant';

    if (ws) {
      ws.close();
      ws = null;
    }
    clearTimeout(reconnectTimer);

    connectionStatus.value = reconnectAttempts > 0 ? 'reconnecting' : 'connecting';

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    ws = new WebSocket(`${protocol}//${host}/ws/tug-of-war/${code.value}/`);

    ws.onopen = () => {
      reconnectAttempts = 0;
      connectionStatus.value = 'open';
      ws.send(JSON.stringify(myTowIdentity(asHost)));
    };

    ws.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }
      _handleMessage(data);
    };

    ws.onerror = () => {
      errorMessage.value = 'Spojenie so serverom bolo prerušené.';
    };

    ws.onclose = () => {
      connectionStatus.value = 'closed';
      const finished = roomState.value?.status === 'finished';
      if (!finished && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts += 1;
        const delay = RECONNECT_BASE_DELAY_MS * Math.min(reconnectAttempts, 5);
        reconnectTimer = setTimeout(() => connect(undefined, role.value === 'host'), delay);
      }
    };
  }

  function _patchParticipantCount(team, participantIdToPatch, correctCount, wrongCount) {
    if (!roomState.value) return;
    const key = team === 'A' ? 'team_a' : 'team_b';
    const list = roomState.value[key];
    if (!list) return;
    const idx = list.findIndex((p) => p.id === participantIdToPatch);
    if (idx === -1) return;
    const updated = [...list];
    updated[idx] = { ...updated[idx], correct_count: correctCount, wrong_count: wrongCount };
    roomState.value = { ...roomState.value, [key]: updated };
  }

  function _handleMessage(data) {
    switch (data.type) {
      case 'error':
        errorMessage.value = data.error;
        break;

      case 'state':
        roomState.value = data;
        break;

      case 'game_start': {
        if (roomState.value) roomState.value = { ...roomState.value, status: 'active', started_at: data.started_at };
        const q = participantId.value != null ? data.questions?.[String(participantId.value)] : null;
        if (q) currentQuestion.value = q;
        break;
      }

      case 'resume':
        currentQuestion.value = data.example;
        break;

      case 'answer_result':
        if (data.participant_id === participantId.value) {
          lastResult.value = { isCorrect: data.is_correct, at: Date.now() };
          currentQuestion.value = data.finished ? null : data.next_example;
        }
        _patchParticipantCount(data.team, data.participant_id, data.correct_count, data.wrong_count);
        if (roomState.value) {
          roomState.value = {
            ...roomState.value,
            rope_position: data.rope_position,
            status: data.finished ? 'finished' : roomState.value.status,
            winner_team: data.finished ? data.winner_team : roomState.value.winner_team,
          };
        }
        if (data.finished && data.results) results.value = data.results;
        break;

      case 'game_over':
        if (roomState.value) {
          roomState.value = {
            ...roomState.value,
            status: 'finished',
            winner_team: data.winner_team,
            rope_position: data.rope_position,
          };
        }
        if (data.results) results.value = data.results;
        break;

      case 'worst_performers':
        results.value = { ...(results.value || {}), worst: data.worst };
        break;
    }
  }

  function submitAnswer(answer) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'answer', answer }));
    }
  }

  function startGame() {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'start_game' }));
  }

  function randomizeTeams() {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'randomize_teams' }));
  }

  function revealWorst() {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'reveal_worst' }));
  }

  function disconnectSocket() {
    clearTimeout(reconnectTimer);
    reconnectAttempts = MAX_RECONNECT_ATTEMPTS; // suppress auto-reconnect on an intentional leave
    if (ws) {
      ws.close();
      ws = null;
    }
  }

  return {
    code, role, participantId, myTeam,
    roomState, currentQuestion, lastResult, results,
    connectionStatus, errorMessage,
    createGame, joinGame, refreshState, connect, submitAnswer, startGame, randomizeTeams, revealWorst, disconnectSocket,
  };
});
