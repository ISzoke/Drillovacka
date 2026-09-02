<script setup>
import { useI18n } from 'vue-i18n';
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import QRCode from 'qrcode';
import { useQuizStore } from '@/stores/useQuizStore';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ code: String });
const { t } = useI18n();
const router = useRouter();
const quizStore = useQuizStore();
const toastStore = useToastStore();

const loading = ref(true);
const qrDataUrl = ref(null);

const status = computed(() => quizStore.roomState?.status);
const leaderboard = computed(() => quizStore.reviewData?.leaderboard || quizStore.roomState?.leaderboard || []);
const participantCount = computed(() => quizStore.roomState?.participant_count ?? leaderboard.value.length);
const totalQuestions = computed(() => quizStore.roomState?.total_questions ?? quizStore.totalQuestions);
const currentIndexDisplay = computed(() => (quizStore.questionIndex ?? 0) + 1);
const isLastQuestion = computed(() => (quizStore.questionIndex ?? 0) + 1 >= (totalQuestions.value ?? Infinity));
const shareLink = computed(() => `${window.location.origin}/quiz/${props.code}`);

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

const copyLink = async () => {
  try {
    await navigator.clipboard.writeText(shareLink.value);
    toastStore.addToast({ message: t('duelLinkCopied'), type: 'success', visible: true });
  } catch (e) {
    // clipboard may be unavailable in this browser/context — non-critical
  }
};

onMounted(async () => {
  try {
    await quizStore.refreshState(props.code);
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('quizJoinError'), type: 'error', visible: true });
    router.push({ name: 'teacher-dashboard' });
    return;
  }
  quizStore.connect(props.code, true);
  qrDataUrl.value = await QRCode.toDataURL(shareLink.value, { margin: 1, width: 220 });
  loading.value = false;
});

onUnmounted(() => {
  quizStore.disconnectSocket();
});

watch(() => quizStore.errorMessage, (msg) => {
  if (msg) {
    toastStore.addToast({ message: msg, type: 'error', visible: true });
    quizStore.errorMessage = null;
  }
});
</script>

<template>
  <div class="pt-20 px-4 max-w-2xl mx-auto pb-12">

    <Spinner v-if="loading" />

    <template v-else>

      <div class="text-center mb-6">
        <h1 class="text-3xl font-bold text-primary dark:text-white mb-1">{{ t('quizHostTitle') }}</h1>
        <p class="text-gray-500 dark:text-gray-400 text-sm">{{ quizStore.roomState?.task_name }}</p>
      </div>

      <!-- Waiting for players -->
      <div v-if="status === 'waiting'" class="text-center">
        <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 mb-6">
          <div class="text-sm text-gray-400 mb-1">{{ t('quizRoomCode') }}</div>
          <div class="text-4xl font-mono font-bold tracking-widest text-primary dark:text-white mb-4">{{ code }}</div>
          <img v-if="qrDataUrl" :src="qrDataUrl" alt="QR" class="mx-auto rounded-xl mb-4" width="220" height="220" />
          <button @click="copyLink"
                  class="px-4 py-2 bg-secondary text-white rounded-xl font-semibold text-sm
                         border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all">
            {{ t('duelCopyLink') }}
          </button>
        </div>

        <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 mb-6">
          <div class="font-bold text-primary dark:text-white mb-2">{{ participantCount }} {{ t('duelPlayersJoined') }}</div>
          <div class="flex flex-wrap gap-2 justify-center">
            <span v-for="p in leaderboard" :key="p.id"
                  class="px-3 py-1 rounded-xl bg-secondary/10 text-secondary text-sm font-semibold">
              {{ p.display_name }}
            </span>
          </div>
        </div>

        <button @click="quizStore.startGame()"
                :disabled="participantCount === 0"
                class="w-full py-3 font-bold text-lg rounded-2xl transition-all
                       border-b-[6px] active:border-b-[2px] active:translate-y-1 disabled:opacity-50 disabled:pointer-events-none
                       bg-secondary text-white border-blue-700 hover:-translate-y-0.5">
          {{ t('quizStartGame') }}
        </button>
      </div>

      <!-- Live question -->
      <div v-else-if="status === 'question'" class="text-center">
        <div class="text-sm text-gray-400 mb-2">{{ t('quizQuestionOf', { current: currentIndexDisplay, total: totalQuestions }) }}</div>
        <div class="rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-8 mb-6">
          <div class="text-3xl font-semibold text-primary dark:text-white">{{ renderedQuestion }}</div>
        </div>
        <p class="text-gray-500 dark:text-gray-400 mb-6">
          {{ t('quizAnsweredCount', { answered: quizStore.answeredCount, total: participantCount }) }}
        </p>
        <button @click="quizStore.reveal()"
                class="w-full py-3 font-bold text-lg rounded-2xl transition-all
                       border-b-[6px] active:border-b-[2px] active:translate-y-1
                       bg-accent text-white border-red-700 hover:-translate-y-0.5">
          {{ t('quizReveal') }}
        </button>
      </div>

      <!-- Review -->
      <div v-else-if="status === 'review'" class="text-center">
        <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 mb-6">
          <div class="text-sm text-gray-400 mb-1">{{ t('quizCorrectAnswerIs') }}</div>
          <div class="text-2xl font-bold text-green-600 dark:text-green-400">{{ renderedCorrectAnswer }}</div>
        </div>

        <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 mb-6">
          <div class="font-bold text-primary dark:text-white mb-3">{{ t('quizLeaderboard') }}</div>
          <div class="space-y-1">
            <div v-for="(p, i) in leaderboard" :key="p.id"
                 class="flex items-center justify-between px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-700/40">
              <span class="text-slate-600 dark:text-slate-300">{{ i + 1 }}. {{ p.display_name }}</span>
              <span class="font-bold text-primary dark:text-white">{{ p.score }} {{ t('quizPoints') }}</span>
            </div>
          </div>
        </div>

        <button @click="quizStore.nextQuestion()"
                class="w-full py-3 font-bold text-lg rounded-2xl transition-all
                       border-b-[6px] active:border-b-[2px] active:translate-y-1
                       bg-secondary text-white border-blue-700 hover:-translate-y-0.5">
          {{ isLastQuestion ? t('quizFinishQuiz') : t('quizNextQuestion') }}
        </button>
      </div>

      <!-- Finished -->
      <div v-else-if="status === 'finished'" class="text-center">
        <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-100 dark:bg-green-900/30 mb-4">
          <span class="text-4xl">🏆</span>
        </div>
        <h2 class="text-2xl font-bold text-primary dark:text-white mb-4">{{ t('quizFinalResults') }}</h2>

        <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 mb-6">
          <div class="space-y-1">
            <div v-for="(p, i) in leaderboard" :key="p.id"
                 class="flex items-center justify-between px-3 py-2 rounded-xl"
                 :class="i === 0 ? 'bg-yellow-100 dark:bg-yellow-900/30' : 'bg-slate-50 dark:bg-slate-700/40'">
              <span class="text-slate-600 dark:text-slate-300">{{ i + 1 }}. {{ p.display_name }}</span>
              <span class="font-bold text-primary dark:text-white">{{ p.score }} {{ t('quizPoints') }}</span>
            </div>
          </div>
        </div>

        <button @click="router.push({ name: 'teacher-dashboard' })"
                class="px-6 py-3 bg-secondary text-white rounded-2xl font-semibold
                       border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all">
          {{ t('quizBackToClassroom') }}
        </button>
      </div>

    </template>
  </div>
</template>
