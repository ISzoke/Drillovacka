<script setup>
import { useI18n } from 'vue-i18n';
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useTugOfWarStore } from '@/stores/useTugOfWarStore';
import { useToastStore } from '@/stores/useToastStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { getSessionId, getDisplayName, setDisplayName } from '@/utils/sessionManager';
import { initSession, getTugOfWarState } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import FractionInput from '@/components/Input Fields/FractionInput.vue';

const props = defineProps({ code: String });
const { t } = useI18n();
const router = useRouter();
const towStore = useTugOfWarStore();
const toastStore = useToastStore();
const authStore = useAuthStore();

const loading = ref(true);
const answerText = ref('');
const fractionInputRef = ref(null);

const status = computed(() => towStore.roomState?.status);
const teamA = computed(() => towStore.roomState?.team_a || []);
const teamB = computed(() => towStore.roomState?.team_b || []);
const maxTeamSize = computed(() => towStore.roomState?.max_team_size ?? 30);
const endMode = computed(() => towStore.roomState?.end_mode);
const targetDiff = computed(() => towStore.roomState?.target_diff || 20);
const visualRange = computed(() => (endMode.value === 'target' ? targetDiff.value : 30));
const ropePosition = computed(() => towStore.roomState?.rope_position || 0);
const ropePercent = computed(() => {
  const clamped = Math.max(-visualRange.value, Math.min(visualRange.value, ropePosition.value));
  return 50 + (clamped / visualRange.value) * 50;
});
const winnerTeam = computed(() => towStore.roomState?.winner_team);
const iWon = computed(() => winnerTeam.value && winnerTeam.value === towStore.myTeam);
const myStats = computed(() => {
  const list = towStore.myTeam === 'A' ? teamA.value : teamB.value;
  return list.find((p) => p.id === towStore.participantId);
});
const inputType = computed(() => (towStore.currentQuestion?.input_type || '').toUpperCase());
const shareLink = computed(() => `${window.location.origin}/tug-of-war/${props.code}`);
const lastFlash = computed(() => towStore.lastResult);

const renderedQuestion = computed(() => {
  const text = towStore.currentQuestion?.example;
  return text ? `\\(${text.replace(/\*/g, '\\cdot')}\\)` : '';
});
function renderMathJax() {
  if (window.MathJax) window.MathJax.typesetPromise();
}
watch(() => towStore.currentQuestion, () => renderMathJax(), { flush: 'post' });

const copyLink = async () => {
  try {
    await navigator.clipboard.writeText(shareLink.value);
    toastStore.addToast({ message: t('duelLinkCopied'), type: 'success', visible: true });
  } catch (e) {
    // clipboard may be unavailable in this browser/context — non-critical
  }
};

const handleFractionAnswer = (numerator, denominator) => {
  towStore.submitAnswer([numerator, denominator]);
  fractionInputRef.value?.clearInput();
};

const submitAnswer = () => {
  if (!towStore.currentQuestion) return;
  if (inputType.value === 'FRAC') {
    fractionInputRef.value?.getAnswer();
    return;
  }
  let payload;
  if (inputType.value === 'VAR') {
    payload = answerText.value.split(',').map((v) => v.trim());
    answerText.value = '';
  } else {
    payload = answerText.value;
    answerText.value = '';
  }
  towStore.submitAnswer(payload);
};

watch(() => towStore.errorMessage, (msg) => {
  if (msg) {
    toastStore.addToast({ message: msg, type: 'error', visible: true });
    towStore.errorMessage = null;
  }
});

// Matches useDuelStore's myIdentity(): only a logged-in student sends
// student_id — admin/teacher plays as an anonymous session too.
const isAnonymous = () => !(authStore.isAuthenticated && authStore.role === 'student');
const needsNamePrompt = ref(false);
const promptName = ref('');
const needsTeamChoice = ref(false);
const teamCounts = ref({ A: 0, B: 0 });
const joinMaxTeamSize = ref(30);
const chosenTeam = ref(null);

const loadTeamCounts = async () => {
  try {
    const state = await getTugOfWarState(props.code);
    teamCounts.value = { A: (state.team_a || []).length, B: (state.team_b || []).length };
    joinMaxTeamSize.value = state.max_team_size ?? 30;
  } catch (e) {
    // best-effort — the join call below will surface a real error if the code is bad
  }
};

const proceedJoin = async (team) => {
  loading.value = true;
  needsNamePrompt.value = false;
  needsTeamChoice.value = false;
  try {
    if (isAnonymous()) {
      await initSession(getSessionId());
      const chosenName = promptName.value.trim();
      if (chosenName) setDisplayName(chosenName);
    }
    await towStore.joinGame(props.code, team, getDisplayName());
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('towJoinError'), type: 'error', visible: true });
    router.push({ name: 'tow-join-manual' });
    return;
  }
  towStore.connect(props.code);
  loading.value = false;
};

const startTeamChoice = async () => {
  await loadTeamCounts();
  loading.value = false;
  needsTeamChoice.value = true;
};

onMounted(() => {
  if (isAnonymous() && !getDisplayName()) {
    loading.value = false;
    needsNamePrompt.value = true;
    return;
  }
  startTeamChoice();
});

onUnmounted(() => {
  towStore.disconnectSocket();
});
</script>

<template>
  <div class="pt-20 px-4 max-w-2xl mx-auto pb-12">

    <Spinner v-if="loading" />

    <!-- First-time anonymous entry — pick a name before joining -->
    <div v-else-if="needsNamePrompt" class="text-center">
      <h1 class="text-2xl font-bold text-primary dark:text-white mb-4">{{ t('yourNameLabel') }}</h1>
      <div class="rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 max-w-sm mx-auto">
        <input v-model="promptName" type="text" maxlength="64" :placeholder="t('yourNamePlaceholder')"
               class="w-full px-4 py-3 mb-3 text-center rounded-2xl border-2 border-slate-200 dark:border-slate-600
                      bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-secondary"
               @keyup.enter="startTeamChoice" />
        <button @click="startTeamChoice"
                class="w-full py-3 font-bold text-lg rounded-2xl transition-all
                       border-b-[6px] active:border-b-[2px] active:translate-y-1
                       bg-secondary text-white border-blue-700 hover:-translate-y-0.5">
          {{ t('duelJoin') }}
        </button>
      </div>
    </div>

    <!-- Team choice -->
    <div v-else-if="needsTeamChoice" class="text-center">
      <h1 class="text-2xl font-bold text-primary dark:text-white mb-6">{{ t('towChooseTeam') }}</h1>
      <div class="grid grid-cols-2 gap-4">
        <button @click="proceedJoin('A')"
                class="py-8 rounded-3xl font-bold text-lg border-2 border-secondary text-secondary
                       hover:bg-secondary/10 transition-colors">
          {{ t('duelTeam') }} A
          <div class="text-sm font-normal text-gray-400 mt-1">{{ teamCounts.A }}/{{ joinMaxTeamSize }}</div>
        </button>
        <button @click="proceedJoin('B')"
                class="py-8 rounded-3xl font-bold text-lg border-2 border-accent text-accent
                       hover:bg-accent/10 transition-colors">
          {{ t('duelTeam') }} B
          <div class="text-sm font-normal text-gray-400 mt-1">{{ teamCounts.B }}/{{ joinMaxTeamSize }}</div>
        </button>
      </div>
    </div>

    <template v-else>

      <!-- Waiting room -->
      <div v-if="status === 'waiting'" class="text-center">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-secondary/10 dark:bg-secondary/20 mb-4">
          <span class="text-3xl">⏳</span>
        </div>
        <h1 class="text-2xl font-bold text-primary dark:text-white mb-1">{{ t('towWaitingForHost') }}</h1>
        <p class="text-gray-500 dark:text-gray-400 text-sm mb-6">
          {{ t('towYourTeam') }}: <span class="font-bold" :class="towStore.myTeam === 'A' ? 'text-secondary' : 'text-accent'">{{ towStore.myTeam }}</span>
        </p>

        <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5 mb-6">
          <div class="text-sm text-gray-400 mb-1">{{ t('duelRoomCode') }}</div>
          <div class="text-3xl font-mono font-bold tracking-widest text-primary dark:text-white mb-3">{{ code }}</div>
          <button @click="copyLink"
                  class="px-4 py-2 bg-secondary text-white rounded-xl font-semibold text-sm
                         border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all">
            {{ t('duelCopyLink') }}
          </button>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
            <div class="font-bold text-secondary mb-2">{{ t('duelTeam') }} A ({{ teamA.length }}/{{ maxTeamSize }})</div>
            <div v-for="p in teamA" :key="p.id" class="text-sm text-slate-600 dark:text-slate-300">{{ p.display_name }}</div>
          </div>
          <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
            <div class="font-bold text-accent mb-2">{{ t('duelTeam') }} B ({{ teamB.length }}/{{ maxTeamSize }})</div>
            <div v-for="p in teamB" :key="p.id" class="text-sm text-slate-600 dark:text-slate-300">{{ p.display_name }}</div>
          </div>
        </div>
      </div>

      <!-- Active gameplay -->
      <div v-else-if="status === 'active'">
        <div class="mb-8">
          <div class="flex justify-between text-sm font-bold mb-1">
            <span class="text-secondary">{{ t('duelTeam') }} A</span>
            <span class="text-accent">{{ t('duelTeam') }} B</span>
          </div>
          <div class="relative h-6 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
            <div class="absolute inset-y-0 left-0 bg-gradient-to-r from-secondary to-secondary/70 transition-all duration-500"
                 :style="{ width: ropePercent + '%' }" />
            <div class="absolute inset-y-0 w-1 bg-white dark:bg-slate-900" style="left: 50%" />
          </div>
        </div>

        <div v-if="myStats" class="text-center mb-4 text-sm text-gray-500 dark:text-gray-400">
          {{ t('towMyScore', { correct: myStats.correct_count, wrong: myStats.wrong_count }) }}
        </div>

        <div v-if="lastFlash" class="text-center mb-3 font-bold text-lg"
             :class="lastFlash.isCorrect ? 'text-green-500' : 'text-accent'">
          {{ lastFlash.isCorrect ? t('duelCorrect') : t('duelWrong') }}
        </div>

        <div class="rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 text-center">
          <div v-if="towStore.currentQuestion" class="text-2xl font-semibold text-primary dark:text-white mb-5">
            {{ renderedQuestion }}
          </div>
          <div v-else class="text-gray-400 mb-5">{{ t('towLoadingNext') }}</div>

          <div v-if="inputType === 'FRAC'" class="mb-4" @keyup.enter="submitAnswer">
            <FractionInput ref="fractionInputRef" @answer-sent="handleFractionAnswer" />
          </div>
          <input v-else v-model="answerText" type="text" autofocus
                 class="w-full px-4 py-3 mb-4 text-center text-xl rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-secondary"
                 @keyup.enter="submitAnswer" />

          <button @click="submitAnswer" :disabled="!towStore.currentQuestion"
                  class="w-full py-3 font-bold text-lg rounded-2xl transition-all
                         border-b-[6px] active:border-b-[2px] active:translate-y-1 disabled:opacity-50
                         bg-secondary text-white border-blue-700 hover:-translate-y-0.5">
            {{ t('duelSubmit') }}
          </button>
        </div>
      </div>

      <!-- Result -->
      <div v-else-if="status === 'finished'" class="text-center">
        <div class="inline-flex items-center justify-center w-20 h-20 rounded-full mb-4"
             :class="iWon ? 'bg-green-100 dark:bg-green-900/30' : 'bg-accent/10'">
          <span class="text-4xl">{{ iWon ? '🏆' : winnerTeam ? '🥈' : '🤝' }}</span>
        </div>
        <h1 class="text-2xl font-bold text-primary dark:text-white mb-2">
          {{ winnerTeam ? (iWon ? t('duelYouWon') : t('duelYouLost')) : t('towDraw') }}
        </h1>
        <p v-if="myStats" class="text-gray-500 dark:text-gray-400 mb-6">
          {{ t('towMyScore', { correct: myStats.correct_count, wrong: myStats.wrong_count }) }}
        </p>

        <div v-if="towStore.results?.top" class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 mb-6 text-left">
          <div class="font-bold text-primary dark:text-white mb-2">{{ t('towTopPerformers') }} &middot; {{ t('duelTeam') }} {{ towStore.myTeam }}</div>
          <div v-for="(p, i) in towStore.results.top[towStore.myTeam] || []" :key="p.id"
               class="flex items-center justify-between px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-700/40 mb-1">
            <span class="text-slate-600 dark:text-slate-300">{{ i + 1 }}. {{ p.display_name }}</span>
            <span class="font-bold text-green-600">{{ p.correct_count }}</span>
          </div>
        </div>

        <div v-if="towStore.results?.worst" class="rounded-2xl border-2 border-red-200 dark:border-red-900/40 bg-white dark:bg-slate-800 p-4 mb-6 text-left">
          <div class="font-bold text-red-500 mb-2">{{ t('towWorstPerformers') }} &middot; {{ t('duelTeam') }} {{ towStore.myTeam }}</div>
          <div v-for="p in towStore.results.worst[towStore.myTeam] || []" :key="p.id"
               class="flex items-center justify-between px-3 py-2 rounded-xl bg-red-50 dark:bg-red-900/20 mb-1">
            <span class="text-slate-600 dark:text-slate-300">{{ p.display_name }}</span>
            <span class="font-bold text-red-500">{{ p.correct_count }}</span>
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
