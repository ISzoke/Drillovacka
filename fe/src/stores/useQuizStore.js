/**
 * ================================================================================
 * File: useQuizStore.js
 * Description:
 *       Pinia store for the live, teacher-hosted Kahoot-style quiz — REST
 *       create/join plus the WebSocket connection to /ws/quiz/<code>/.
 *       Structurally mirrors useDuelStore.js (reconnect-with-backoff), but
 *       adds a host/participant role split: the teacher drives pacing
 *       (start/reveal/next), participants only answer.
 * ================================================================================
 */

import { defineStore } from 'pinia';
import { ref } from 'vue';
import { useAuthStore } from './useAuthStore';
import { getSessionId } from '@/utils/sessionManager';
import { createQuiz, joinQuiz, getQuizState } from '@/api/apiClient';

const MAX_RECONNECT_ATTEMPTS = 15;
const RECONNECT_BASE_DELAY_MS = 1000;

function myQuizIdentity(asHost) {
  const auth = useAuthStore();
  if (asHost) {
    return { teacher_id: auth.id };
  }
  if (auth.isAuthenticated && auth.role === 'student' && auth.id) {
    return { student_id: auth.id, session_id: null };
  }
  return { student_id: null, session_id: getSessionId() };
}

export const useQuizStore = defineStore('quiz', () => {
  let ws = null;
  let reconnectTimer = null;
  let reconnectAttempts = 0;

  const code = ref(null);
  const role = ref(null); // 'host' | 'participant'
  const participantId = ref(null);

  const roomState = ref(null); // latest 'state' broadcast: status, task_name, current_question_index, total_questions, leaderboard
  const currentQuestion = ref(null); // { id, example, input_type }
  const questionIndex = ref(null);
  const totalQuestions = ref(null);
  const answeredCount = ref(0); // live "X/Y answered" counter while status === 'question'
  const reviewData = ref(null); // { index, correct_answer, answered_count, participant_count, leaderboard }
  const lastResult = ref(null); // { isCorrect, pointsAwarded, at } — my own answer_ack
  const connectionStatus = ref('idle'); // idle | connecting | open | reconnecting | closed
  const errorMessage = ref(null);

  async function createGame(taskId) {
    const auth = useAuthStore();
    const data = await createQuiz(auth.id, taskId);
    code.value = data.code;
    roomState.value = data;
    return data;
  }

  async function joinGame(joinCode, displayName) {
    const identity = myQuizIdentity(false);
    const data = await joinQuiz(identity.student_id, joinCode, displayName);
    code.value = data.code;
    roomState.value = data;
    if (data.you) participantId.value = data.you.participant_id;
    return data;
  }

  async function refreshState(existingCode) {
    const data = await getQuizState(existingCode || code.value);
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
    ws = new WebSocket(`${protocol}//${host}/ws/quiz/${code.value}/`);

    ws.onopen = () => {
      reconnectAttempts = 0;
      connectionStatus.value = 'open';
      ws.send(JSON.stringify(myQuizIdentity(asHost)));
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

  function _handleMessage(data) {
    switch (data.type) {
      case 'error':
        errorMessage.value = data.error;
        break;

      case 'state':
        roomState.value = data;
        break;

      case 'question':
        currentQuestion.value = data.example;
        questionIndex.value = data.index;
        totalQuestions.value = data.total;
        answeredCount.value = 0;
        reviewData.value = null;
        lastResult.value = null;
        if (roomState.value) {
          roomState.value = { ...roomState.value, status: 'question', current_question_index: data.index };
        }
        break;

      case 'answer_ack':
        lastResult.value = { isCorrect: data.is_correct, pointsAwarded: data.points_awarded, at: Date.now() };
        break;

      case 'answer_count':
        answeredCount.value = data.answered_count;
        break;

      case 'review':
        reviewData.value = data;
        currentQuestion.value = null;
        if (roomState.value) {
          roomState.value = { ...roomState.value, status: 'review', leaderboard: data.leaderboard };
        }
        break;

      case 'game_over':
        currentQuestion.value = null;
        reviewData.value = null;
        if (roomState.value) {
          roomState.value = { ...roomState.value, status: 'finished', leaderboard: data.leaderboard };
        }
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

  function reveal() {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'reveal' }));
  }

  function nextQuestion() {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'next_question' }));
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
    code, role, participantId,
    roomState, currentQuestion, questionIndex, totalQuestions, answeredCount, reviewData, lastResult,
    connectionStatus, errorMessage,
    createGame, joinGame, refreshState, connect, submitAnswer, startGame, reveal, nextQuestion, disconnectSocket,
  };
});
