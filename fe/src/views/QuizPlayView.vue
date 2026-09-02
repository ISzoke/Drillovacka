<script setup>
import { useI18n } from 'vue-i18n';
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useQuizStore } from '@/stores/useQuizStore';
import { useToastStore } from '@/stores/useToastStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { getSessionId, getDisplayName, setDisplayName } from '@/utils/sessionManager';
import { initSession } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import FractionInput from '@/components/Input Fields/FractionInput.vue';

const props = defineProps({ code: { type: String, default: null } });
const { t } = useI18n();
const router = useRouter();
const quizStore = useQuizStore();
const toastStore = useToastStore();
const authStore = useAuthStore();

const loading = ref(false);
const manualCode = ref('');
const answerText = ref('');
const fractionInputRef = ref(null);
const hasAnsweredThisQuestion = ref(false);

const isAnonymous = () => !(authStore.isAuthenticated || localStorage.getItem('role') !== null);
const needsNamePrompt = ref(false);
const promptName = ref('');
const showNameInManualForm = computed(() => isAnonymous() && !getDisplayName());

const status = computed(() => quizStore.roomState?.status);
const inputType = computed(() => (quizStore.currentQuestion?.input_type || '').toUpperCase());
const leaderboard = computed(() => quizStore.reviewData?.leaderboard || quizStore.roomState?.leaderboard || []);
const myRank = computed(() => leaderboard.value.findIndex(p => p.id === quizStore.participantId) + 1);
const totalQuestions = computed(() => quizStore.roomState?.total_questions ?? quizStore.totalQuestions);
const currentIndexDisplay = computed(() => (quizStore.questionIndex ?? 0) + 1);

// Same MathJax wrapping convention as components/Example.vue's renderedExample.
const renderedQuestion = computed(() => {
  const text = quizStore.currentQuestion?.example;
  return text ? `\\(${text.replace(/\*/g, '\\cdot')}\\)` : '';
});
const renderedCorrectAnswer = computed(() => {
  const text = quizStore.reviewData?.correct_answer;
  return text ? `\\(${text.replace(/\*/g, '\\cdot')}\\)` : '';
});
function renderMathJax() {
  if (window.MathJax) window.MathJax.typesetPromise();
}
// flush: 'post' — otherwise this can run before Vue patches the DOM with the
// new question text, and MathJax ends up typesetting stale/empty content.
watch(() => quizStore.currentQuestion, () => renderMathJax(), { flush: 'post' });
watch(() => quizStore.reviewData, () => renderMathJax(), { flush: 'post' });

const joinAndConnect = async (code) => {
  loading.value = true;
  needsNamePrompt.value = false;
  try {
    // A QR-code scan or shared link is often the very first page this browser
    // loads — App.vue's own initSession() call races this component's mount
    // and can lose, leaving an anonymous session_id the backend doesn't know
    // about yet. Make sure it exists before joining.
    if (isAnonymous()) {
      await initSession(getSessionId());
      const chosenName = promptName.value.trim();
      if (chosenName) setDisplayName(chosenName);
    }
    await quizStore.joinGame(code, getDisplayName());
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('quizJoinError'), type: 'error', visible: true });
    loading.value = false;
    return;
  }
  quizStore.connect(code, false);
  router.replace({ name: 'quiz-play', params: { code } });
  loading.value = false;
};

const handleManualJoin = () => {
  const code = manualCode.value.trim().toUpperCase();
  if (code) joinAndConnect(code);
};

const handleFractionAnswer = (numerator, denominator) => {
  hasAnsweredThisQuestion.value = true;
  quizStore.submitAnswer([numerator, denominator]);
  fractionInputRef.value?.clearInput();
};

const submitAnswer = () => {
  if (!quizStore.currentQuestion || hasAnsweredThisQuestion.value) return;
  if (inputType.value === 'FRAC') {
    fractionInputRef.value?.getAnswer(); // emits answerSent -> handleFractionAnswer
    return;
  }
  let payload;
  if (inputType.value === 'VAR') {
    payload = answerText.value.split(',').map(v => v.trim());
    answerText.value = '';
  } else {
    payload = answerText.value;
    answerText.value = '';
  }
  hasAnsweredThisQuestion.value = true;
  quizStore.submitAnswer(payload);
};

watch(() => quizStore.currentQuestion, () => {
  hasAnsweredThisQuestion.value = false;
});

watch(() => quizStore.errorMessage, (msg) => {
  if (msg) {
    toastStore.addToast({ message: msg, type: 'error', visible: true });
    quizStore.errorMessage = null;
  }
});

onMounted(() => {
  if (!props.code) return; // manual entry form handles it, name field included when needed
  // First time an anonymous player lands here (e.g. via a shared link or QR
  // code) — let them pick a name. Returning anonymous players skip straight to join.
  if (isAnonymous() && !getDisplayName()) {
    needsNamePrompt.value = true;
    return;
  }
  joinAndConnect(props.code);
});

onUnmounted(() => {
  quizStore.disconnectSocket();
});
</script>

<template>
  <div class="pt-20 px-4 max-w-2xl mx-auto pb-12">

    <Spinner v-if="loading" />

    <!-- First-time anonymous entry via QR/link (code known, name not yet) -->
    <div v-else-if="needsNamePrompt" class="text-center">
      <h1 class="text-2xl font-bold text-primary dark:text-white mb-4">{{ t('yourNameLabel') }}</h1>
      <div class="rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 max-w-sm mx-auto">
        <input
          v-model="promptName"
          type="text"
          maxlength="64"
          :placeholder="t('yourNamePlaceholder')"
          class="w-full px-4 py-3 mb-3 text-center rounded-2xl border-2 border-slate-200 dark:border-slate-600
                 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-secondary"
          @keyup.enter="joinAndConnect(code)"
        />
        <button @click="joinAndConnect(code)"
                class="w-full py-3 font-bold text-lg rounded-2xl transition-all
                       border-b-[6px] active:border-b-[2px] active:translate-y-1
                       bg-secondary text-white border-blue-700 hover:-translate-y-0.5">
          {{ t('duelJoin') }}
        </button>
      </div>
    </div>

    <!-- No code yet — manual entry -->
    <div v-else-if="!quizStore.roomState" class="text-center">
      <h1 class="text-3xl font-bold text-primary dark:text-white mb-6">{{ t('quizHostTitle') }}</h1>
      <div class="rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
        <input
          v-if="showNameInManualForm"
          v-model="promptName"
          type="text"
          maxlength="64"
          :placeholder="t('yourNamePlaceholder')"
          class="w-full px-4 py-3 mb-3 text-center rounded-2xl border-2 border-slate-200 dark:border-slate-600
                 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-secondary"
        />
        <div class="flex gap-2">
          <input
            v-model="manualCode"
            type="text"
            maxlength="8"
            :placeholder="t('quizEnterCode')"
            class="flex-1 px-4 py-3 text-center text-xl font-mono uppercase tracking-widest
                   rounded-2xl border-2 border-slate-200 dark:border-slate-600
                   bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                   focus:outline-none focus:border-secondary transition-colors"
            @keyup.enter="handleManualJoin"
          />
          <button
            @click="handleManualJoin"
            class="px-5 py-3 bg-secondary text-white rounded-2xl font-semibold
                   border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5
                   active:border-b-2 transition-all"
          >
            {{ t('duelJoin') }}
          </button>
        </div>
      </div>
    </div>

    <template v-else>

      <!-- Waiting for host -->
      <div v-if="status === 'waiting'" class="text-center">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-secondary/10 dark:bg-secondary/20 mb-4">
          <span class="text-3xl">⏳</span>
        </div>
        <h1 class="text-2xl font-bold text-primary dark:text-white mb-1">{{ t('quizWaitingForHost') }}</h1>
        <p class="text-gray-500 dark:text-gray-400 text-sm">{{ quizStore.roomState?.task_name }}</p>
      </div>

      <!-- Question -->
      <div v-else-if="status === 'question'">
        <div class="text-sm text-gray-400 text-center mb-2">
          {{ t('quizQuestionOf', { current: currentIndexDisplay, total: totalQuestions }) }}
        </div>
        <div class="rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 text-center">
          <div class="text-2xl font-semibold text-primary dark:text-white mb-5">{{ renderedQuestion }}</div>

          <div v-if="hasAnsweredThisQuestion" class="text-gray-400 py-4">{{ t('quizAnswerSubmitted') }}</div>
          <template v-else>
            <div v-if="inputType === 'FRAC'" class="mb-4" @keyup.enter="submitAnswer">
              <FractionInput ref="fractionInputRef" @answer-sent="handleFractionAnswer" />
            </div>
            <input v-else v-model="answerText" type="text" autofocus
                   class="w-full px-4 py-3 mb-4 text-center text-xl rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-secondary"
                   @keyup.enter="submitAnswer" />

            <button @click="submitAnswer"
                    class="w-full py-3 font-bold text-lg rounded-2xl transition-all
                           border-b-[6px] active:border-b-[2px] active:translate-y-1
                           bg-secondary text-white border-blue-700 hover:-translate-y-0.5">
              {{ t('duelSubmit') }}
            </button>
          </template>
        </div>
      </div>

      <!-- Review -->
      <div v-else-if="status === 'review'" class="text-center">
        <div v-if="quizStore.lastResult" class="mb-4">
          <div class="text-2xl font-bold mb-1" :class="quizStore.lastResult.isCorrect ? 'text-green-500' : 'text-accent'">
            {{ quizStore.lastResult.isCorrect ? t('duelCorrect') : t('duelWrong') }}
          </div>
          <div v-if="quizStore.lastResult.isCorrect" class="text-secondary font-semibold">
            {{ t('quizPointsEarned', { points: quizStore.lastResult.pointsAwarded }) }}
          </div>
        </div>
        <div v-else class="text-gray-400 mb-4">{{ t('quizNoAnswerInTime') }}</div>

        <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 mb-6">
          <div class="text-sm text-gray-400 mb-1">{{ t('quizCorrectAnswerIs') }}</div>
          <div class="text-2xl font-bold text-green-600 dark:text-green-400">{{ renderedCorrectAnswer }}</div>
        </div>

        <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
          <div class="font-bold text-primary dark:text-white mb-3">{{ t('quizLeaderboard') }}</div>
          <div class="space-y-1">
            <div v-for="(p, i) in leaderboard" :key="p.id"
                 class="flex items-center justify-between px-3 py-2 rounded-xl"
                 :class="p.id === quizStore.participantId ? 'bg-secondary/10' : 'bg-slate-50 dark:bg-slate-700/40'">
              <span class="text-slate-600 dark:text-slate-300">
                {{ i + 1 }}. {{ p.display_name }} <span v-if="p.id === quizStore.participantId" class="text-secondary font-semibold">({{ t('quizYou') }})</span>
              </span>
              <span class="font-bold text-primary dark:text-white">{{ p.score }} {{ t('quizPoints') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Finished -->
      <div v-else-if="status === 'finished'" class="text-center">
        <div class="inline-flex items-center justify-center w-20 h-20 rounded-full mb-4"
             :class="myRank === 1 ? 'bg-yellow-100 dark:bg-yellow-900/30' : 'bg-secondary/10'">
          <span class="text-4xl">{{ myRank === 1 ? '🏆' : '🎉' }}</span>
        </div>
        <h1 class="text-2xl font-bold text-primary dark:text-white mb-2">{{ t('quizFinalResults') }}</h1>
        <p v-if="myRank > 0" class="text-gray-500 dark:text-gray-400 mb-6">#{{ myRank }}</p>

        <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 mb-6">
          <div class="space-y-1">
            <div v-for="(p, i) in leaderboard" :key="p.id"
                 class="flex items-center justify-between px-3 py-2 rounded-xl"
                 :class="p.id === quizStore.participantId ? 'bg-secondary/10' : 'bg-slate-50 dark:bg-slate-700/40'">
              <span class="text-slate-600 dark:text-slate-300">{{ i + 1 }}. {{ p.display_name }}</span>
              <span class="font-bold text-primary dark:text-white">{{ p.score }} {{ t('quizPoints') }}</span>
            </div>
          </div>
        </div>

        <button @click="router.push({ name: 'home' })"
                class="px-6 py-3 bg-secondary text-white rounded-2xl font-semibold
                       border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all">
          {{ t('quizBackToHome') }}
        </button>
      </div>

    </template>
  </div>
</template>
