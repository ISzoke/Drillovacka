/**
 * ================================================================================
 * File: useDuelStore.js
 * Description:
 *       Pinia store for the "duel" (tug-of-war) live game — REST create/join
 *       plus the WebSocket connection to /ws/duel/<code>/. Unlike
 *       useRecorderStore's WS (one-shot, no reconnect needed), this socket
 *       needs reconnect-with-backoff so the server-side disconnect grace
 *       period actually has a chance to be used by the client.
 * ================================================================================
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useAuthStore } from './useAuthStore';
import { useGamificationStore } from './useGamificationStore';
import { getSessionId } from '@/utils/sessionManager';
import { createDuel, joinDuel, getDuelState } from '@/api/apiClient';

const MAX_RECONNECT_ATTEMPTS = 15;
const RECONNECT_BASE_DELAY_MS = 1000;

function myIdentity() {
  const auth = useAuthStore();
  if (auth.isAuthenticated && auth.role === 'student' && auth.id) {
    return { student_id: auth.id, session_id: null };
  }
  return { student_id: null, session_id: getSessionId() };
}

export const useDuelStore = defineStore('duel', () => {
  const gamStore = useGamificationStore();

  let ws = null;
  let reconnectTimer = null;
  let reconnectAttempts = 0;

  const code = ref(null);
  const myTeam = ref(null);
  const mySlot = ref(null);

  const roomState = ref(null);
  const currentQuestion = ref(null);
  const lastResult = ref(null);
  const connectionStatus = ref('idle'); // idle | connecting | open | reconnecting | closed
  const errorMessage = ref(null);

  const isMyLane = (team, slot) => team === myTeam.value && slot === mySlot.value;

  const myTeamGamePosition = computed(() => roomState.value?.rope_position ?? 0);

  async function createGame({ taskId, mode, visibility, timeLimitSeconds, vsBot, botDifficulty, displayName }) {
    const identity = myIdentity();
    const data = await createDuel(identity.student_id, { mode, visibility, taskId, timeLimitSeconds, vsBot, botDifficulty, displayName });
    _applyRoomResponse(data);
    return data;
  }

  async function joinGame(joinCode, displayName) {
    const identity = myIdentity();
    const data = await joinDuel(identity.student_id, joinCode, displayName);
    _applyRoomResponse(data);
    return data;
  }

  async function refreshState(existingCode) {
    const data = await getDuelState(existingCode || code.value);
    roomState.value = data;
    return data;
  }

  function _applyRoomResponse(data) {
    code.value = data.code;
    roomState.value = data;
    if (data.you) {
      myTeam.value = data.you.team;
      mySlot.value = data.you.slot;
    }
  }

  function connect(targetCode) {
    if (targetCode) code.value = targetCode;
    if (!code.value) return;

    if (ws) {
      ws.close();
      ws = null;
    }
    clearTimeout(reconnectTimer);

    connectionStatus.value = reconnectAttempts > 0 ? 'reconnecting' : 'connecting';

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    ws = new WebSocket(`${protocol}//${host}/ws/duel/${code.value}/`);

    ws.onopen = () => {
      reconnectAttempts = 0;
      connectionStatus.value = 'open';
      const identity = myIdentity();
      ws.send(JSON.stringify(identity));
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
        reconnectTimer = setTimeout(() => connect(), delay);
      }
    };
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
        const q = mySlot.value != null ? data.questions?.[String(mySlot.value)] : null;
        if (q) currentQuestion.value = q;
        break;
      }

      case 'resume':
        currentQuestion.value = data.example;
        break;

      case 'answer_result':
        if (isMyLane(data.team, data.slot)) {
          lastResult.value = { isCorrect: data.is_correct, at: Date.now() };
          currentQuestion.value = data.finished ? null : data.next_example;
          if (data.xp) gamStore.handleXPUpdate(data.xp);
        }
        if (roomState.value) {
          roomState.value = {
            ...roomState.value,
            rope_position: data.rope_position,
            status: data.finished ? 'finished' : roomState.value.status,
            winner_team: data.finished ? data.winner_team : roomState.value.winner_team,
          };
        }
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
        break;
    }
  }

  function submitAnswer(answer) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'answer', answer }));
    }
  }

  function fillWithBot(difficulty) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'fill_with_bot', difficulty }));
    }
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
    code, myTeam, mySlot,
    roomState, currentQuestion, lastResult, connectionStatus, errorMessage,
    myTeamGamePosition,
    createGame, joinGame, refreshState, connect, submitAnswer, fillWithBot, disconnectSocket,
  };
});
