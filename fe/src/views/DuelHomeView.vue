<script setup>
import { useI18n } from 'vue-i18n';
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { browseTasks, listPublicDuels } from '@/api/apiClient';
import { useDuelStore } from '@/stores/useDuelStore';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';

const { t } = useI18n();
const router = useRouter();
const duelStore = useDuelStore();
const toastStore = useToastStore();

const mode = ref('1v1');
const visibility = ref('public');
const timeLimitSeconds = ref(180);
const taskSearch = ref('');
const tasks = ref([]);
const selectedTask = ref(null);
const tasksLoading = ref(false);
const creating = ref(false);

const manualCode = ref('');
const joining = ref(false);

const publicGames = ref([]);
let pollTimer = null;

const TIME_OPTIONS = [60, 120, 180, 300];

const searchTasks = async () => {
  tasksLoading.value = true;
  try {
    tasks.value = await browseTasks(null, taskSearch.value.trim());
  } catch (e) {
    tasks.value = [];
  }
  tasksLoading.value = false;
};

const refreshPublicGames = async () => {
  try {
    publicGames.value = await listPublicDuels();
  } catch (e) {
    // silent — lobby polling shouldn't spam toasts
  }
};

const handleCreate = async () => {
  if (!selectedTask.value) {
    toastStore.addToast({ message: t('duelSelectTaskFirst'), type: 'error', visible: true });
    return;
  }
  creating.value = true;
  try {
    const data = await duelStore.createGame({
      taskId: selectedTask.value.task_id,
      mode: mode.value,
      visibility: visibility.value,
      timeLimitSeconds: timeLimitSeconds.value,
    });
    router.push({ name: 'duel-room', params: { code: data.code } });
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('duelCreateError'), type: 'error', visible: true });
  }
  creating.value = false;
};

const handleJoinByCode = async () => {
  const code = manualCode.value.trim().toUpperCase();
  if (!code) return;
  joining.value = true;
  try {
    await duelStore.joinGame(code);
    router.push({ name: 'duel-room', params: { code } });
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('duelJoinError'), type: 'error', visible: true });
  }
  joining.value = false;
};

const handleJoinPublic = async (code) => {
  joining.value = true;
  try {
    await duelStore.joinGame(code);
    router.push({ name: 'duel-room', params: { code } });
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('duelJoinError'), type: 'error', visible: true });
  }
  joining.value = false;
};

onMounted(() => {
  searchTasks();
  refreshPublicGames();
  pollTimer = setInterval(refreshPublicGames, 4000);
});

onUnmounted(() => {
  clearInterval(pollTimer);
});
</script>

<template>
  <div class="pt-20 px-4 max-w-2xl mx-auto pb-12">

    <div class="text-center mb-8">
      <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-secondary/10 dark:bg-secondary/20 mb-4">
        <span class="text-3xl">🪢</span>
      </div>
      <h1 class="text-3xl font-bold text-primary dark:text-white mb-2">{{ t('duelTitle') }}</h1>
      <p class="text-gray-500 dark:text-gray-400 text-sm">{{ t('duelSubtitle') }}</p>
    </div>

    <!-- Join by code -->
    <div class="mb-8 rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
      <h2 class="font-bold text-lg text-primary dark:text-white mb-3">{{ t('duelJoinByCode') }}</h2>
      <div class="flex gap-2">
        <input
          v-model="manualCode"
          type="text"
          maxlength="8"
          :placeholder="t('enterCode')"
          class="flex-1 px-4 py-3 text-center text-xl font-mono uppercase tracking-widest
                 rounded-2xl border-2 border-slate-200 dark:border-slate-600
                 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                 focus:outline-none focus:border-secondary transition-colors"
          @keyup.enter="handleJoinByCode"
        />
        <button
          @click="handleJoinByCode"
          :disabled="joining"
          class="px-5 py-3 bg-secondary text-white rounded-2xl font-semibold
                 border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5
                 active:border-b-2 transition-all disabled:opacity-50"
        >
          {{ t('duelJoin') }}
        </button>
      </div>
    </div>

    <!-- Public lobby -->
    <div v-if="publicGames.length" class="mb-8 rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
      <h2 class="font-bold text-lg text-primary dark:text-white mb-3">{{ t('duelPublicLobby') }}</h2>
      <div class="space-y-2">
        <div v-for="g in publicGames" :key="g.code"
             class="flex items-center justify-between p-3 rounded-2xl border border-slate-200 dark:border-slate-700">
          <div>
            <div class="font-semibold text-primary dark:text-white">{{ g.task_name }}</div>
            <div class="text-xs text-gray-400">{{ g.mode }} · {{ g.participant_count }}/{{ g.required_count }}</div>
          </div>
          <button
            @click="handleJoinPublic(g.code)"
            :disabled="joining"
            class="px-4 py-2 bg-secondary text-white rounded-xl font-semibold text-sm
                   border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5
                   active:border-b-2 transition-all disabled:opacity-50"
          >
            {{ t('duelJoin') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Create game -->
    <div class="rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
      <h2 class="font-bold text-lg text-primary dark:text-white mb-4">{{ t('duelCreateGame') }}</h2>

      <div class="mb-4">
        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ t('duelMode') }}</div>
        <div class="flex gap-2">
          <button v-for="m in ['1v1', '2v2']" :key="m" @click="mode = m"
                  class="flex-1 py-2 rounded-xl font-semibold border-2 transition-colors"
                  :class="mode === m ? 'bg-secondary text-white border-secondary' : 'border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-300'">
            {{ m }}
          </button>
        </div>
      </div>

      <div class="mb-4">
        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ t('duelVisibility') }}</div>
        <div class="flex gap-2">
          <button v-for="v in ['public', 'private']" :key="v" @click="visibility = v"
                  class="flex-1 py-2 rounded-xl font-semibold border-2 transition-colors"
                  :class="visibility === v ? 'bg-secondary text-white border-secondary' : 'border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-300'">
            {{ t(v === 'public' ? 'duelPublic' : 'duelPrivate') }}
          </button>
        </div>
      </div>

      <div class="mb-4">
        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ t('duelTimeLimit') }}</div>
        <div class="flex gap-2">
          <button v-for="secs in TIME_OPTIONS" :key="secs" @click="timeLimitSeconds = secs"
                  class="flex-1 py-2 rounded-xl font-semibold border-2 transition-colors"
                  :class="timeLimitSeconds === secs ? 'bg-secondary text-white border-secondary' : 'border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-300'">
            {{ Math.round(secs / 60) }} min
          </button>
        </div>
      </div>

      <div class="mb-4">
        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ t('duelChooseTask') }}</div>
        <input
          v-model="taskSearch"
          @input="searchTasks"
          type="text"
          :placeholder="t('search')"
          class="w-full px-4 py-2 mb-2 rounded-xl border-2 border-slate-200 dark:border-slate-600
                 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-secondary"
        />
        <Spinner v-if="tasksLoading" />
        <div v-else class="max-h-56 overflow-y-auto space-y-1">
          <button v-for="task in tasks" :key="task.task_id" @click="selectedTask = task"
                  class="w-full text-left px-3 py-2 rounded-xl border-2 transition-colors"
                  :class="selectedTask?.task_id === task.task_id ? 'bg-secondary/10 border-secondary' : 'border-transparent hover:border-slate-200 dark:hover:border-slate-600'">
            <div class="font-medium text-primary dark:text-white">{{ task.task_name }}</div>
            <div class="text-xs text-gray-400">{{ task.example_count }} {{ t('examples') }}</div>
          </button>
          <div v-if="!tasks.length" class="text-center text-sm text-gray-400 py-4">{{ t('taskSetsNoResults') }}</div>
        </div>
      </div>

      <button
        @click="handleCreate"
        :disabled="creating || !selectedTask"
        class="w-full py-3 font-bold text-lg rounded-2xl transition-all
               border-b-[6px] active:border-b-[2px] active:translate-y-1 disabled:opacity-50 disabled:pointer-events-none
               bg-secondary text-white border-blue-700 hover:-translate-y-0.5"
      >
        {{ creating ? '...' : t('duelCreateGame') }}
      </button>
    </div>

  </div>
</template>
