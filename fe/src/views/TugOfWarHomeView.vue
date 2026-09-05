<script setup>
import { useI18n } from 'vue-i18n';
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { browseTasks, getGradeLevels, getMyTeacherTasks } from '@/api/apiClient';
import { useTugOfWarStore } from '@/stores/useTugOfWarStore';
import { useToastStore } from '@/stores/useToastStore';
import { useAuthStore } from '@/stores/useAuthStore';
import Spinner from '@/components/Spinner.vue';

const { t } = useI18n();
const router = useRouter();
const towStore = useTugOfWarStore();
const toastStore = useToastStore();
const authStore = useAuthStore();

const endMode = ref('time'); // 'time' | 'target'
const timeLimitSeconds = ref(300); // default 5 min
const timeLimitMinutes = computed({
  get: () => timeLimitSeconds.value / 60,
  set: (v) => { timeLimitSeconds.value = Math.max(60, Math.round((Number(v) || 5) * 60)); },
});
const targetDiff = ref(20);
const maxTeamSize = ref(30);

const taskSearch = ref('');
const tasks = ref([]);
const myTasks = ref([]);
const selectedTask = ref(null);
const tasksLoading = ref(false);
const creating = ref(false);

const filteredMyTasks = computed(() => {
  const q = taskSearch.value.trim().toLowerCase();
  if (!q) return myTasks.value;
  return myTasks.value.filter((t) => t.task_name.toLowerCase().includes(q));
});

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

const loadMyTasks = async () => {
  try {
    const data = await getMyTeacherTasks(authStore.id);
    myTasks.value = data.map((t) => ({
      task_id: t.id,
      task_name: t.name,
      example_count: t.example_count,
      grade_levels: t.grade_levels,
    }));
  } catch (e) {
    myTasks.value = [];
  }
};

const handleCreate = async () => {
  if (!selectedTask.value) {
    toastStore.addToast({ message: t('duelSelectTaskFirst'), type: 'error', visible: true });
    return;
  }
  creating.value = true;
  try {
    const data = await towStore.createGame({
      taskId: selectedTask.value.task_id,
      endMode: endMode.value,
      timeLimitSeconds: endMode.value === 'time' ? timeLimitSeconds.value : undefined,
      targetDiff: endMode.value === 'target' ? targetDiff.value : undefined,
      maxTeamSize: maxTeamSize.value,
    });
    router.push({ name: 'teacher-tow-host', params: { code: data.code } });
  } catch (e) {
    toastStore.addToast({ message: e?.response?.data?.error || t('towCreateError'), type: 'error', visible: true });
  }
  creating.value = false;
};

onMounted(async () => {
  grades.value = await getGradeLevels();
  searchTasks();
  loadMyTasks();
});
</script>

<template>
  <div class="pt-20 px-4 max-w-2xl mx-auto pb-12">

    <div class="text-center mb-8">
      <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-secondary/10 dark:bg-secondary/20 mb-4">
        <span class="text-3xl">🪢</span>
      </div>
      <h1 class="text-3xl font-bold text-primary dark:text-white mb-2">{{ t('towTitle') }}</h1>
      <p class="text-gray-500 dark:text-gray-400 text-sm">{{ t('towSubtitle') }}</p>
    </div>

    <div class="rounded-3xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-5">

      <div class="mb-4">
        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ t('towEndMode') }}</div>
        <div class="flex gap-2">
          <button @click="endMode = 'time'"
                  class="flex-1 py-2 rounded-xl font-semibold border-2 transition-colors"
                  :class="endMode === 'time' ? 'bg-secondary text-white border-secondary' : 'border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-300'">
            {{ t('towEndModeTime') }}
          </button>
          <button @click="endMode = 'target'"
                  class="flex-1 py-2 rounded-xl font-semibold border-2 transition-colors"
                  :class="endMode === 'target' ? 'bg-secondary text-white border-secondary' : 'border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-300'">
            {{ t('towEndModeTarget') }}
          </button>
        </div>
        <p class="text-xs text-gray-400 mt-2">{{ t('towEndModeHelp') }}</p>
      </div>

      <div v-if="endMode === 'time'" class="mb-4">
        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ t('duelTimeLimit') }}</div>
        <div class="flex items-center gap-2">
          <input v-model.number="timeLimitMinutes" type="number" min="1" max="30" step="1"
                 class="w-24 px-4 py-2 rounded-xl border-2 border-slate-200 dark:border-slate-600
                        bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-center font-semibold
                        focus:outline-none focus:border-secondary" />
          <span class="text-sm text-gray-500 dark:text-gray-400">{{ t('duelMinutes') }}</span>
        </div>
      </div>

      <div v-else class="mb-4">
        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ t('towTargetDiff') }}</div>
        <div class="flex items-center gap-2">
          <input v-model.number="targetDiff" type="number" min="3" max="200" step="1"
                 class="w-24 px-4 py-2 rounded-xl border-2 border-slate-200 dark:border-slate-600
                        bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-center font-semibold
                        focus:outline-none focus:border-secondary" />
          <span class="text-sm text-gray-500 dark:text-gray-400">{{ t('towTargetDiffUnit') }}</span>
        </div>
      </div>

      <div class="mb-4">
        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ t('towMaxTeamSize') }}</div>
        <input v-model.number="maxTeamSize" type="number" min="1" max="30" step="1"
               class="w-24 px-4 py-2 rounded-xl border-2 border-slate-200 dark:border-slate-600
                      bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-center font-semibold
                      focus:outline-none focus:border-secondary" />
      </div>

      <div class="mb-4">
        <div class="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-2">{{ t('duelChooseTask') }}</div>
        <input v-model="taskSearch" @input="searchTasks" type="text" :placeholder="t('search')"
               class="w-full px-4 py-2 mb-2 rounded-xl border-2 border-slate-200 dark:border-slate-600
                      bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 focus:outline-none focus:border-secondary" />
        <Spinner v-if="tasksLoading" />
        <div v-else class="max-h-72 overflow-y-auto space-y-2">
          <div v-if="filteredMyTasks.length" class="rounded-xl border-2 border-secondary/40 overflow-hidden">
            <div class="px-3 py-2 font-semibold text-primary dark:text-white bg-secondary/10">
              {{ t('towMyTasks') }}
            </div>
            <div class="p-1 space-y-1">
              <button v-for="task in filteredMyTasks" :key="`mine-${task.task_id}`" @click="selectedTask = task"
                      class="w-full text-left px-3 py-2 rounded-xl border-2 transition-colors"
                      :class="selectedTask?.task_id === task.task_id ? 'bg-secondary/10 border-secondary' : 'border-transparent hover:border-slate-200 dark:hover:border-slate-600'">
                <div class="font-medium text-primary dark:text-white">{{ task.task_name }}</div>
                <div class="text-xs text-gray-400">{{ task.example_count }} {{ t('examples') }}</div>
              </button>
            </div>
          </div>
          <div v-for="group in tasksByGrade" :key="group.grade"
               class="rounded-xl border-2 border-slate-200 dark:border-slate-600 overflow-hidden">
            <button @click="toggleGrade(group.grade)"
                    class="w-full flex items-center justify-between px-3 py-2 font-semibold text-primary dark:text-white
                           bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
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
          <div v-if="!tasksByGrade.length && !filteredMyTasks.length" class="text-center text-sm text-gray-400 py-4">{{ t('taskSetsNoResults') }}</div>
        </div>
        <div v-if="selectedTask" class="mt-2 px-3 py-2 rounded-xl bg-secondary/10 text-sm text-primary dark:text-white">
          {{ t('duelChooseTask') }}: <span class="font-semibold">{{ selectedTask.task_name }}</span>
        </div>
      </div>

      <button @click="handleCreate" :disabled="creating || !selectedTask"
              class="w-full py-3 font-bold text-lg rounded-2xl transition-all
                     border-b-[6px] active:border-b-[2px] active:translate-y-1 disabled:opacity-50 disabled:pointer-events-none
                     bg-secondary text-white border-blue-700 hover:-translate-y-0.5">
        {{ creating ? '...' : t('towCreateGame') }}
      </button>
    </div>

  </div>
</template>
