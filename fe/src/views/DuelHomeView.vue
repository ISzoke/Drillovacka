<script setup>
import { useI18n } from 'vue-i18n';
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { browseTasks, listPublicDuels, getGradeLevels } from '@/api/apiClient';
import { useDuelStore } from '@/stores/useDuelStore';
import { useToastStore } from '@/stores/useToastStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { getDisplayName, setDisplayName } from '@/utils/sessionManager';
import Spinner from '@/components/Spinner.vue';

const { t } = useI18n();
const router = useRouter();
const duelStore = useDuelStore();
const toastStore = useToastStore();
const authStore = useAuthStore();

const displayName = ref(getDisplayName());
// Matches useDuelStore's myIdentity(): only a logged-in student sends
// student_id — admin/teacher (and everyone else) plays as an anonymous
// session and needs the name box, even though authStore.isAuthenticated is true for them.
const isAnonymous = computed(() => !(authStore.isAuthenticated && authStore.role === 'student'));

const mode = ref('1v1');
const visibility = ref('public');
const timeLimitSeconds = ref(180); // default 3 min, user-editable below
const timeLimitMinutes = computed({
  get: () => timeLimitSeconds.value / 60,
  set: (v) => { timeLimitSeconds.value = Math.max(30, Math.round((Number(v) || 3) * 60)); },
});
const taskSearch = ref('');
const tasks = ref([]);
const selectedTask = ref(null);
const tasksLoading = ref(false);
const creating = ref(false);

const manualCode = ref('');
const joining = ref(false);

const publicGames = ref([]);
let pollTimer = null;

const grades = ref([]);
const expandedGrades = ref(new Set());

const tasksByGrade = computed(() => {
  return grades.value
    .map((g) => ({
      grade: g.grade,
      tasks: tasks.value.filter((t) => t.grade_levels?.includes(g.grade)),
    }))
    .filter((group) => group.tasks.length);
});

const toggleGrade = (grade) => {
  const next = new Set(expandedGrades.value);
  if (next.has(grade)) next.delete(grade);
  else next.add(grade);
  expandedGrades.value = next;
};

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

const persistName = () => {
  const trimmed = displayName.value.trim();
  if (trimmed) setDisplayName(trimmed);
  return trimmed;
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
      displayName: persistName(),
    });
    router.push({ name: 'duel-room', params: { code: data.code } });
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('duelCreateError'), type: 'error', visible: true });
  }
  creating.value = false;
};

const botDifficulty = ref('medium');

const handlePlayBot = async () => {
  if (!selectedTask.value) {
    toastStore.addToast({ message: t('duelSelectTaskFirst'), type: 'error', visible: true });
    return;
  }
  creating.value = true;
  try {
    const data = await duelStore.createGame({
      taskId: selectedTask.value.task_id,
      mode: '1v1',
      visibility: 'private',
      timeLimitSeconds: timeLimitSeconds.value,
      vsBot: true,
      botDifficulty: botDifficulty.value,
      displayName: persistName(),
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
    await duelStore.joinGame(code, persistName());
    router.push({ name: 'duel-room', params: { code } });
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('duelJoinError'), type: 'error', visible: true });
  }
  joining.value = false;
};

const handleJoinPublic = async (code) => {
  joining.value = true;
  try {
    await duelStore.joinGame(code, persistName());
    router.push({ name: 'duel-room', params: { code } });
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('duelJoinError'), type: 'error', visible: true });
  }
  joining.value = false;
};

onMounted(async () => {
  grades.value = await getGradeLevels();
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

    <!-- Anonymous display name -->
    <div v-if="isAnonymous" class="mb-8 rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
      <h2 class="font-bold text-lg text-primary dark:text-white mb-3">{{ t('yourNameLabel') }}</h2>
      <input
        v-model="displayName"
        type="text"
        maxlength="64"
        :placeholder="t('yourNamePlaceholder')"
        class="w-full px-4 py-3 rounded-2xl border-2 border-slate-200 dark:border-slate-600
               bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
               focus:outline-none focus:border-secondary transition-colors"
      />
    </div>

    <!-- Join by code -->
    <div class="mb-8 rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
      <h2 class="font-bold text-lg text-primary dark:text-white mb-3">{{ t('duelJoinByCode') }}</h2>
      <div class="flex gap-2">
        <input
          v-model="manualCode"
          type="text"
          maxlength="8"
          :placeholder="t('duelEnterCode')"
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
            <div class="text-xs text-gray-400">{{ t(g.mode === '1v1' ? 'duelMode1v1' : 'duelMode2v2') }} · {{ g.participant_count }}/{{ g.required_count }}</div>
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
            {{ t(m === '1v1' ? 'duelMode1v1' : 'duelMode2v2') }}
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
        <div class="flex items-center gap-2">
          <input
            v-model.number="timeLimitMinutes"
            type="number"
            min="1"
            max="15"
            step="1"
            class="w-24 px-4 py-2 rounded-xl border-2 border-slate-200 dark:border-slate-600
                   bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-center font-semibold
                   focus:outline-none focus:border-secondary"
          />
          <span class="text-sm text-gray-500 dark:text-gray-400">{{ t('duelMinutes') }}</span>
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
        <div v-else class="max-h-72 overflow-y-auto space-y-2">
          <div v-for="group in tasksByGrade" :key="group.grade"
               class="rounded-xl border-2 border-slate-200 dark:border-slate-600 overflow-hidden">
            <button
              @click="toggleGrade(group.grade)"
              class="w-full flex items-center justify-between px-3 py-2 font-semibold text-primary dark:text-white
                     bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            >
              <span>{{ t('gradeFullLabel', { grade: group.grade }) }}</span>
              <span class="flex items-center gap-2 text-xs text-gray-400 font-normal">
                {{ group.tasks.length }}
                <span class="transition-transform" :class="expandedGrades.has(group.grade) ? 'rotate-180' : ''">▾</span>
              </span>
            </button>
            <div v-if="expandedGrades.has(group.grade)" class="p-1 space-y-1">
              <button v-for="task in group.tasks" :key="task.task_id" @click="selectedTask = task"
                      class="w-full text-left px-3 py-2 rounded-xl border-2 transition-colors"
                      :class="selectedTask?.task_id === task.task_id ? 'bg-secondary/10 border-secondary' : 'border-transparent hover:border-slate-200 dark:hover:border-slate-600'">
                <div class="font-medium text-primary dark:text-white">{{ task.task_name }}</div>
                <div class="text-xs text-gray-400">{{ task.example_count }} {{ t('examples') }}</div>
              </button>
            </div>
          </div>
          <div v-if="!tasksByGrade.length" class="text-center text-sm text-gray-400 py-4">{{ t('taskSetsNoResults') }}</div>
        </div>
        <div v-if="selectedTask" class="mt-2 px-3 py-2 rounded-xl bg-secondary/10 text-sm text-primary dark:text-white">
          {{ t('duelChooseTask') }}: <span class="font-semibold">{{ selectedTask.task_name }}</span>
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

    <!-- Play vs bot -->
    <div class="mt-6 rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">
      <h2 class="font-bold text-lg text-primary dark:text-white mb-1">{{ t('duelVsBotTitle') }}</h2>
      <p class="text-gray-500 dark:text-gray-400 text-sm mb-4">{{ t('duelVsBotSubtitle') }}</p>

      <div class="mb-4">
        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ t('duelBotDifficulty') }}</div>
        <div class="flex gap-2">
          <button v-for="d in ['easy', 'medium', 'hard']" :key="d" @click="botDifficulty = d"
                  class="flex-1 py-2 rounded-xl font-semibold border-2 transition-colors text-sm"
                  :class="botDifficulty === d ? 'bg-accent text-white border-accent' : 'border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-300'">
            {{ t(`duelBotDifficulty_${d}`) }}
          </button>
        </div>
      </div>

      <button
        @click="handlePlayBot"
        :disabled="creating || !selectedTask"
        class="w-full py-3 font-bold text-lg rounded-2xl transition-all
               border-b-[6px] active:border-b-[2px] active:translate-y-1 disabled:opacity-50 disabled:pointer-events-none
               bg-accent text-white border-red-700 hover:-translate-y-0.5"
      >
        🤖 {{ creating ? '...' : t('duelPlayVsBot') }}
      </button>
    </div>

  </div>
</template>
