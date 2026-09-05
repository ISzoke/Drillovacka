<script setup>
import { useI18n } from 'vue-i18n';
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import QRCode from 'qrcode';
import { useTugOfWarStore } from '@/stores/useTugOfWarStore';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ code: String });
const { t } = useI18n();
const router = useRouter();
const towStore = useTugOfWarStore();
const toastStore = useToastStore();

const loading = ref(true);
const qrDataUrl = ref(null);
const worstRevealed = ref(false);

const status = computed(() => towStore.roomState?.status);
const teamA = computed(() => towStore.roomState?.team_a || []);
const teamB = computed(() => towStore.roomState?.team_b || []);
const maxTeamSize = computed(() => towStore.roomState?.max_team_size ?? 30);
const endMode = computed(() => towStore.roomState?.end_mode);
const targetDiff = computed(() => towStore.roomState?.target_diff || 20);
// Time mode has no fixed target, so cap the visual rope range generously —
// wide enough that a normal-length round rarely pins it to one edge.
const visualRange = computed(() => (endMode.value === 'target' ? targetDiff.value : 30));
const ropePosition = computed(() => towStore.roomState?.rope_position || 0);
const ropePercent = computed(() => {
  const clamped = Math.max(-visualRange.value, Math.min(visualRange.value, ropePosition.value));
  return 50 + (clamped / visualRange.value) * 50;
});
const winnerTeam = computed(() => towStore.roomState?.winner_team);
const canStart = computed(() => teamA.value.length > 0 && teamB.value.length > 0 && status.value === 'waiting');
const shareLink = computed(() => `${window.location.origin}/tug-of-war/${props.code}`);
const teamCorrect = (team) => team.reduce((sum, p) => sum + (p.correct_count || 0), 0);

const copyLink = async () => {
  try {
    await navigator.clipboard.writeText(shareLink.value);
    toastStore.addToast({ message: t('duelLinkCopied'), type: 'success', visible: true });
  } catch (e) {
    // clipboard may be unavailable in this browser/context — non-critical
  }
};

const handleReveal = () => {
  towStore.revealWorst();
  worstRevealed.value = true;
};

onMounted(async () => {
  try {
    await towStore.refreshState(props.code);
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('towJoinError'), type: 'error', visible: true });
    router.push({ name: 'teacher-dashboard' });
    return;
  }
  towStore.connect(props.code, true);
  qrDataUrl.value = await QRCode.toDataURL(shareLink.value, { margin: 1, width: 220 });
  loading.value = false;
});

onUnmounted(() => {
  towStore.disconnectSocket();
});

watch(() => towStore.errorMessage, (msg) => {
  if (msg) {
    toastStore.addToast({ message: msg, type: 'error', visible: true });
    towStore.errorMessage = null;
  }
});
</script>

<template>
  <div class="pt-20 px-4 max-w-2xl mx-auto pb-12">

    <Spinner v-if="loading" />

    <template v-else>

      <div class="text-center mb-6">
        <h1 class="text-3xl font-bold text-primary dark:text-white mb-1">{{ t('towHostTitle') }}</h1>
        <p class="text-gray-500 dark:text-gray-400 text-sm">{{ towStore.roomState?.task_name }}</p>
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

        <div class="grid grid-cols-2 gap-4 mb-6">
          <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
            <div class="font-bold text-secondary mb-2">{{ t('duelTeam') }} A ({{ teamA.length }}/{{ maxTeamSize }})</div>
            <div v-for="p in teamA" :key="p.id" class="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-1">
              <span :class="p.connected ? 'text-green-500' : 'text-gray-300'">●</span>{{ p.display_name }}
            </div>
            <div v-if="!teamA.length" class="text-sm text-gray-300 italic">{{ t('duelEmptySlot') }}</div>
          </div>
          <div class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4">
            <div class="font-bold text-accent mb-2">{{ t('duelTeam') }} B ({{ teamB.length }}/{{ maxTeamSize }})</div>
            <div v-for="p in teamB" :key="p.id" class="text-sm text-slate-600 dark:text-slate-300 flex items-center gap-1">
              <span :class="p.connected ? 'text-green-500' : 'text-gray-300'">●</span>{{ p.display_name }}
            </div>
            <div v-if="!teamB.length" class="text-sm text-gray-300 italic">{{ t('duelEmptySlot') }}</div>
          </div>
        </div>

        <button @click="towStore.randomizeTeams()"
                class="w-full mb-3 py-3 font-bold rounded-2xl transition-all
                       border-2 border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300
                       hover:bg-slate-50 dark:hover:bg-slate-700">
          🔀 {{ t('towRandomizeTeams') }}
        </button>

        <button @click="towStore.startGame()" :disabled="!canStart"
                class="w-full py-3 font-bold text-lg rounded-2xl transition-all
                       border-b-[6px] active:border-b-[2px] active:translate-y-1 disabled:opacity-50 disabled:pointer-events-none
                       bg-secondary text-white border-blue-700 hover:-translate-y-0.5">
          {{ t('towStartGame') }}
        </button>
      </div>

      <!-- Active round -->
      <div v-else-if="status === 'active'">
        <div class="mb-8">
          <div class="flex justify-between text-sm font-bold mb-1">
            <span class="text-secondary">{{ t('duelTeam') }} A &middot; {{ teamCorrect(teamA) }}</span>
            <span class="text-accent">{{ t('duelTeam') }} B &middot; {{ teamCorrect(teamB) }}</span>
          </div>
          <div class="relative h-8 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
            <div class="absolute inset-y-0 left-0 bg-gradient-to-r from-secondary to-secondary/70 transition-all duration-500"
                 :style="{ width: ropePercent + '%' }" />
            <div class="absolute inset-y-0 w-1 bg-white dark:bg-slate-900" style="left: 50%" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div v-for="(team, label) in { A: teamA, B: teamB }" :key="label"
               class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 max-h-64 overflow-y-auto">
            <div class="font-bold mb-2" :class="label === 'A' ? 'text-secondary' : 'text-accent'">{{ t('duelTeam') }} {{ label }}</div>
            <div v-for="p in team" :key="p.id" class="flex justify-between text-sm text-slate-600 dark:text-slate-300 py-0.5">
              <span>{{ p.display_name }}</span>
              <span class="font-semibold text-green-600">{{ p.correct_count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Finished -->
      <div v-else-if="status === 'finished'" class="text-center">
        <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-100 dark:bg-green-900/30 mb-4">
          <span class="text-4xl">🏆</span>
        </div>
        <h2 class="text-2xl font-bold text-primary dark:text-white mb-1">
          {{ winnerTeam ? t('towTeamWon', { team: winnerTeam }) : t('towDraw') }}
        </h2>
        <p class="text-gray-500 dark:text-gray-400 mb-6">{{ t('towFinalResults') }}</p>

        <div class="grid grid-cols-2 gap-4 mb-6">
          <div v-for="(label) in ['A', 'B']" :key="label"
               class="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-4 text-left">
            <div class="font-bold mb-2" :class="label === 'A' ? 'text-secondary' : 'text-accent'">{{ t('duelTeam') }} {{ label }} &middot; {{ t('towTopPerformers') }}</div>
            <div v-for="(p, i) in towStore.results?.top?.[label] || []" :key="p.id"
                 class="flex items-center justify-between px-2 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-700/40 mb-1 text-sm">
              <span class="text-slate-600 dark:text-slate-300">{{ i + 1 }}. {{ p.display_name }}</span>
              <span class="font-bold text-green-600">{{ p.correct_count }}</span>
            </div>
          </div>
        </div>

        <button v-if="!worstRevealed" @click="handleReveal"
                class="mb-6 px-5 py-3 rounded-2xl font-semibold text-sm
                       border-2 border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300
                       hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
          👁️ {{ t('towRevealWorst') }}
        </button>

        <div v-if="worstRevealed && towStore.results?.worst" class="grid grid-cols-2 gap-4 mb-6">
          <div v-for="(label) in ['A', 'B']" :key="label"
               class="rounded-2xl border-2 border-red-200 dark:border-red-900/40 bg-white dark:bg-slate-800 p-4 text-left">
            <div class="font-bold mb-2 text-red-500">{{ t('duelTeam') }} {{ label }} &middot; {{ t('towWorstPerformers') }}</div>
            <div v-for="p in towStore.results.worst[label] || []" :key="p.id"
                 class="flex items-center justify-between px-2 py-1.5 rounded-lg bg-red-50 dark:bg-red-900/20 mb-1 text-sm">
              <span class="text-slate-600 dark:text-slate-300">{{ p.display_name }}</span>
              <span class="font-bold text-red-500">{{ p.correct_count }}</span>
            </div>
          </div>
        </div>
        <div v-else-if="worstRevealed" class="mb-6"><Spinner /></div>

        <button @click="router.push({ name: 'teacher-dashboard' })"
                class="px-6 py-3 bg-secondary text-white rounded-2xl font-semibold
                       border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all">
          {{ t('quizBackToClassroom') }}
        </button>
      </div>

    </template>
  </div>
</template>
