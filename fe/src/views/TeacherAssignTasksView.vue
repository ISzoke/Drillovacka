<script setup>
import { useI18n } from 'vue-i18n';
import { ref, onMounted, computed } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRouter } from 'vue-router';
import { getTasks, assignTaskToClassroom, getClassroomDetail } from '@/api/apiClient';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ classroomId: [String, Number] });

const authStore = useAuthStore();
const router = useRouter();
const langStore = useLanguageStore();
const toastStore = useToastStore();
const { t } = useI18n();

const allTasks = ref([]);
const assignedTaskIds = ref(new Set());
const loading = ref(true);
const assigning = ref(null);
const search = ref('');
const selectedGrade = ref('');
const showHomeworkModal = ref(false);
const pendingTask = ref(null);
const isHomework = ref(false);
const dueDate = ref('');

const filteredTasks = computed(() => {
  return allTasks.value.filter(t => {
    const matchSearch = !search.value || t.title.toLowerCase().includes(search.value.toLowerCase());
    const matchGrade = !selectedGrade.value ||
      (t.grade_levels && t.grade_levels.includes(parseInt(selectedGrade.value)));
    return matchSearch && matchGrade;
  });
});

const fetchData = async () => {
  loading.value = true;
  try {
    const [tasks, classroom] = await Promise.all([
      getTasks(),
      getClassroomDetail(props.classroomId, { teacherId: authStore.id }),
    ]);
    allTasks.value = tasks || [];
    assignedTaskIds.value = new Set(
      (classroom.task_assignments || []).map(a => a.task_id)
    );
  } catch (e) {
    console.error('Error fetching data:', e);
  }
  loading.value = false;
};

const openAssignModal = (task) => {
  pendingTask.value = task;
  isHomework.value = false;
  dueDate.value = '';
  showHomeworkModal.value = true;
};

const confirmAssign = async () => {
  if (!pendingTask.value) return;
  assigning.value = pendingTask.value.id;
  showHomeworkModal.value = false;
  try {
    await assignTaskToClassroom(
      props.classroomId,
      authStore.id,
      pendingTask.value.id,
      isHomework.value,
      dueDate.value || null,
    );
    assignedTaskIds.value.add(pendingTask.value.id);
    toastStore.addToast({
      message: t('taskAssigned') || 'Úloha priradená',
      type: 'success',
      visible: true,
    });
  } catch (e) {
    console.error('Error assigning task:', e);
    toastStore.addToast({
      message: t('errorAssigning') || 'Chyba pri priraďovaní',
      type: 'error',
      visible: true,
    });
  }
  assigning.value = null;
  pendingTask.value = null;
};

onMounted(fetchData);
</script>

<template>
  <div class="pt-24 px-4 max-w-4xl mx-auto">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <router-link :to="{ name: 'teacher-classroom', params: { classroomId } }"
                   class="text-secondary hover:underline text-sm">
        &larr; {{ t('backToClassroom') || 'Späť do triedy' }}
      </router-link>
    </div>
    <h1 class="text-2xl font-bold text-primary mb-6">
      {{ t('assignTasks') || 'Priradiť úlohy' }}
    </h1>

    <Spinner v-if="loading" />

    <template v-else>
      <!-- Filters -->
      <div class="flex flex-col sm:flex-row gap-3 mb-6">
        <input
          v-model="search"
          type="text"
          :placeholder="t('searchTasks')"
          class="flex-1 px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                 focus:outline-none focus:ring-2 focus:ring-secondary"
        />
        <select
          v-model="selectedGrade"
          class="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                 focus:outline-none focus:ring-2 focus:ring-secondary"
        >
          <option value="">{{ t('allGrades') }}</option>
          <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">
            {{ g }}. {{ t('grade') || 'ročník' }}
          </option>
        </select>
      </div>

      <div v-if="filteredTasks.length === 0" class="text-center py-12 text-gray-400">
        {{ t('noTasksFound') || 'Žiadne úlohy nenájdené.' }}
      </div>

      <div v-else class="space-y-3">
        <div v-for="task in filteredTasks" :key="task.id"
             class="flex items-center justify-between p-4 bg-white dark:bg-slate-800 rounded-xl
                    border border-slate-200 dark:border-slate-700">
          <div class="flex-1 min-w-0">
            <div class="font-medium text-slate-800 dark:text-slate-100 truncate">
              {{ task.title }}
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 flex gap-2 flex-wrap">
              <span v-if="task.example_count">
                {{ task.example_count }} {{ t('examples') || 'príkladov' }}
              </span>
              <span v-if="task.grade_levels?.length">
                &middot; {{ task.grade_levels.map(g => g + '.').join(', ') }}
              </span>
            </div>
          </div>

          <div class="ml-4 flex-shrink-0">
            <span v-if="assignedTaskIds.has(task.id)"
                  class="text-xs text-green-600 dark:text-green-400 font-medium px-3 py-1
                         bg-green-50 dark:bg-green-900/30 rounded-full">
              {{ t('assigned') || 'Priradené' }}
            </span>
            <button v-else
                    @click="openAssignModal(task)"
                    :disabled="assigning === task.id"
                    class="px-4 py-1.5 bg-secondary text-white rounded-lg text-sm font-medium
                           hover:bg-blue-600 transition-colors disabled:opacity-50">
              {{ assigning === task.id ? '...' : (t('assign') || 'Priradiť') }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- Homework modal -->
    <div v-if="showHomeworkModal"
         class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
         @click.self="showHomeworkModal = false">
      <div class="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-sm shadow-xl">
        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 mb-1">
          {{ pendingTask?.title }}
        </h3>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          {{ t('configureAssignment') || 'Nastavte priradenie' }}
        </p>

        <label class="flex items-center gap-3 mb-4 cursor-pointer">
          <input type="checkbox" v-model="isHomework" class="w-4 h-4 accent-secondary" />
          <span class="text-sm text-slate-700 dark:text-slate-300">
            {{ t('markAsHomework') || 'Označiť ako domácu úlohu' }}
          </span>
        </label>

        <div v-if="isHomework" class="mb-4">
          <label class="block text-sm text-slate-700 dark:text-slate-300 mb-1">
            {{ t('dueDate') || 'Termín odovzdania' }}
          </label>
          <input type="date" v-model="dueDate"
                 class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                        bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                        focus:outline-none focus:ring-2 focus:ring-secondary" />
        </div>

        <div class="flex gap-3 justify-end">
          <button @click="showHomeworkModal = false"
                  class="px-4 py-2 rounded-md text-gray-600 dark:text-gray-300
                         hover:bg-gray-100 dark:hover:bg-slate-700">
            {{ t('cancel') || 'Zrušiť' }}
          </button>
          <button @click="confirmAssign"
                  class="px-4 py-2 bg-secondary text-white rounded-md hover:bg-blue-600 font-semibold">
            {{ t('assign') || 'Priradiť' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
