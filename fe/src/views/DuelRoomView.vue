<script setup>
import { useI18n } from 'vue-i18n';
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useDuelStore } from '@/stores/useDuelStore';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ code: String });
const { t } = useI18n();
const router = useRouter();
const duelStore = useDuelStore();
const toastStore = useToastStore();

const loading = ref(true);
const answerText = ref('');
const fracNum = ref('');
const fracDen = ref('');

const status = computed(() => duelStore.roomState?.status);
const participants = computed(() => duelStore.roomState?.participants || []);
const teamA = computed(() => participants.value.filter(p => p.team === 'A'));
const teamB = computed(() => participants.value.filter(p => p.team === 'B'));
const requiredCount = computed(() => duelStore.roomState?.required_count || 2);
const targetSteps = computed(() => duelStore.roomState?.target_steps || 8);
const ropePosition = computed(() => duelStore.roomState?.rope_position || 0);
const ropePercent = computed(() => {
  const clamped = Math.max(-targetSteps.value, Math.min(targetSteps.value, ropePosition.value));
  return 50 + (clamped / targetSteps.value) * 50; // 0 = fully team B's edge, 100 = fully team A's edge
});
const winnerTeam = computed(() => duelStore.roomState?.winner_team);
const iWon = computed(() => winnerTeam.value && winnerTeam.value === duelStore.myTeam);
const inputType = computed(() => (duelStore.currentQuestion?.input_type || '').toUpperCase());
const shareLink = computed(() => `${window.location.origin}/duel/${props.code}`);
const lastFlash = computed(() => duelStore.lastResult);

const copyLink = async () => {
  try {
    await navigator.clipboard.writeText(shareLink.value);
    toastStore.addToast({ message: t('duelLinkCopied'), type: 'success', visible: true });
  } catch (e) {
    // clipboard may be unavailable in this browser/context — non-critical
  }
};

const submitAnswer = () => {
  if (!duelStore.currentQuestion) return;
  let payload;
  if (inputType.value === 'FRAC') {
    payload = [fracNum.value, fracDen.value];
    fracNum.value = '';
    fracDen.value = '';
  } else if (inputType.value === 'VAR') {
    payload = answerText.value.split(',').map(v => v.trim());
    answerText.value = '';
  } else {
    payload = answerText.value;
    answerText.value = '';
  }
  duelStore.submitAnswer(payload);
};

watch(() => duelStore.errorMessage, (msg) => {
  if (msg) {
    toastStore.addToast({ message: msg, type: 'error', visible: true });
    duelStore.errorMessage = null;
  }
});

onMounted(async () => {
  try {
    // Idempotent: resumes the existing participant if we already have a slot
    // (founder, or returning from a reload), otherwise claims the next open one.
    await duelStore.joinGame(props.code);
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('duelJoinError'), type: 'error', visible: true });
    router.push({ name: 'duel-home' });
    return;
  }
  duelStore.connect(props.code);
  loading.value = false;
});

onUnmounted(() => {
  duelStore.disconnectSocket();
});
</script>

<template>
  <div class="pt-20 px-4 max-w-2xl mx-auto pb-12">

    <Spinner v-if="loading" />

    <template v-else>

      <!-- Waiting room -->
      <div v-if="status === 'waiting'" class="text-center">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-secondary/10 dark:bg-secondary/20 mb-4">
          <span class="text-3xl">⏳</span>
        </div>
        <h1 class="text-2xl font-bold text-primary dark:text-white mb-1">{{ t('duelWaitingForPlayers') }}</h1>
        <p class="text-gray-500 dark:text-gray-400 text-sm mb-6">
          {{ participants.length }}/{{ requiredCount }} {{ t('duelPlayersJoined') }}
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
          <div v-for="(team, label) in { A: teamA, B: teamB }" :key="label"
               class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
            <div class="font-bold text-primary dark:text-white mb-2">{{ t('duelTeam') }} {{ label }}</div>
            <div v-for="p in team" :key="`${p.team}${p.slot}`" class="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-1">
              <span :class="p.connected ? 'text-green-500' : 'text-gray-300'">●</span>
              {{ p.display_name }}
            </div>
            <div v-if="!team.length" class="text-sm text-gray-300 italic">{{ t('duelEmptySlot') }}</div>
          </div>
        </div>
      </div>

      <!-- Active gameplay -->
      <div v-else-if="status === 'active'">
        <!-- Rope -->
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

        <!-- Flash feedback -->
        <div v-if="lastFlash" class="text-center mb-3 font-bold text-lg"
             :class="lastFlash.isCorrect ? 'text-green-500' : 'text-accent'">
          {{ lastFlash.isCorrect ? t('duelCorrect') : t('duelWrong') }}
        </div>

        <!-- Current question -->
        <div class="rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 text-center">
          <div v-if="duelStore.currentQuestion" class="text-2xl font-semibold text-primary dark:text-white mb-5">
            {{ duelStore.currentQuestion.example }}
          </div>
          <div v-else class="text-gray-400 mb-5">{{ t('duelWaitingForOpponent') }}</div>

          <div v-if="inputType === 'FRAC'" class="flex items-center justify-center gap-2 mb-4">
            <input v-model="fracNum" type="text" inputmode="numeric" class="w-20 px-3 py-2 text-center text-xl rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100" @keyup.enter="submitAnswer" />
            <span class="text-2xl text-slate-400">/</span>
            <input v-model="fracDen" type="text" inputmode="numeric" class="w-20 px-3 py-2 text-center text-xl rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100" @keyup.enter="submitAnswer" />
          </div>
          <input v-else v-model="answerText" type="text" autofocus
                 class="w-full px-4 py-3 mb-4 text-center text-xl rounded-xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-secondary"
                 @keyup.enter="submitAnswer" />

          <button @click="submitAnswer" :disabled="!duelStore.currentQuestion"
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
          <span class="text-4xl">{{ iWon ? '🏆' : '🥈' }}</span>
        </div>
        <h1 class="text-2xl font-bold text-primary dark:text-white mb-2">
          {{ iWon ? t('duelYouWon') : t('duelYouLost') }}
        </h1>
        <p class="text-gray-500 dark:text-gray-400 mb-6">
          {{ t('duelTeam') }} {{ winnerTeam }} {{ t('duelWonTheGame') }}
        </p>
        <button @click="router.push({ name: 'duel-home' })"
                class="px-6 py-3 bg-secondary text-white rounded-2xl font-semibold
                       border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all">
          {{ t('duelBackToHome') }}
        </button>
      </div>

    </template>
  </div>
</template>
