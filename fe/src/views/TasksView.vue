<!--
================================================================================
 Component: TasksView.vue
 Description:
      Displays tasks with associated skills and examples.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { getTasks, deleteTask, getGradeLevels, updateTaskGradeLevels } from '@/api/apiClient';
import { useTaskStore } from '@/stores/useTaskStore';
import { useToastStore } from '@/stores/useToastStore';
import { useRouter } from 'vue-router';
import Spinner from '@/components/Spinner.vue';

const { t } = useI18n();
const tasks = ref([]);
const gradeLevels = ref([]);
const loading = ref(true);
const router = useRouter();
const toastStore = useToastStore();
const savingGrades = ref({});
const selectedGrades = ref({});

// Modal window variables
const showDeleteModal = ref(false);
const taskToDelete = ref(null);
const taskToDeleteIndex = ref(null);
const taskToDeleteName = ref('');

// Render MathJax content
const renderMathJax = () => {
  if (window.MathJax && window.MathJax.typesetPromise) {
    window.MathJax.typesetPromise().catch((err) =>
      console.error('MathJax rendering error:', err)
    );
  } else {
    console.warn('MathJax is not loaded properly');
  }
};

// Fetch tasks and render their examples
onMounted(async () => {
  try {
    const [taskData, gradeData] = await Promise.all([
      getTasks(),
      getGradeLevels(),
    ]);
    tasks.value = taskData || [];
    gradeLevels.value = gradeData || [];
    initializeSelectedGrades();
  } catch (error) {
    console.error("Failed to fetch tasks:", error);
  } finally {
    loading.value = false;
  }
  nextTick(() => renderMathJax());
});

watch(tasks, () => {
  nextTick(() => renderMathJax());
});

const initializeSelectedGrades = () => {
  const nextState = {};
  for (const task of tasks.value) {
    nextState[task.task_id] = (task.grade_levels || []).map((grade) => grade.id);
  }
  selectedGrades.value = nextState;
};

const toggleGradeSelection = (taskId, gradeId, checked) => {
  const current = new Set(selectedGrades.value[taskId] || []);
  if (checked) {
    current.add(gradeId);
  } else {
    current.delete(gradeId);
  }
  selectedGrades.value = {
    ...selectedGrades.value,
    [taskId]: Array.from(current).sort((a, b) => a - b),
  };
};

const saveTaskGrades = async (taskIndex) => {
  const task = tasks.value[taskIndex];
  if (!task) return;

  savingGrades.value = {
    ...savingGrades.value,
    [task.task_id]: true,
  };

  try {
    const result = await updateTaskGradeLevels(task.task_id, selectedGrades.value[task.task_id] || []);
    task.grade_levels = result.grade_levels || [];
    toastStore.addToast({
      message: t('gradesSavedForTaskMessage', { name: task.task_name }),
      type: 'success',
      visible: true,
    });
  } catch (error) {
    toastStore.addToast({
      message: typeof error === 'string' ? error : t('gradesSaveFailedMessage'),
      type: 'error',
      visible: true,
    });
  } finally {
    savingGrades.value = {
      ...savingGrades.value,
      [task.task_id]: false,
    };
  }
};

// Open delete confirmation modal
const confirmDeleteTask = (taskId, taskIndex, taskName) => {
  taskToDelete.value = taskId;
  taskToDeleteIndex.value = taskIndex;
  taskToDeleteName.value = taskName;
  showDeleteModal.value = true;
};

// Cancel delete
const cancelDelete = () => {
  taskToDelete.value = null;
  taskToDeleteIndex.value = null;
  taskToDeleteName.value = '';
  showDeleteModal.value = false;
};

// Delete task when confirmed
const handleDeleteTask = async () => {
  if (!taskToDelete.value || taskToDeleteIndex.value === null) return;

  try {
    await deleteTask(taskToDelete.value);

    toastStore.addToast({
      message: t('taskSetDeletedMessage', { name: taskToDeleteName.value }),
      type: 'success',
      visible: true,
    });

    tasks.value.splice(taskToDeleteIndex.value, 1);

  } catch (error) {
    console.error("Error deleting task:", error);

  } finally {
    cancelDelete();
  }
};

// Navigate and pass task data to sandbox to edit selected task
const handleEditTask = (taskIndex) => {
  const taskStore = useTaskStore();
  const task = tasks.value[taskIndex];
  taskStore.setTask(task);
  router.push('/sandbox');
};
</script>

<template>

  <div class="max-w-5xl mx-auto p-4 pt-12">
    <div class="flex flex-col items-center justify-center">
      <h1 class="text-4xl text-primary font-bold text-center">{{ t('taskSetsTitle') }}</h1>

      <div class="my-4 flex flex-col sm:flex-row gap-3">
        <RouterLink to="/tasks/grades"
          class="bg-blue-600 hover:bg-blue-700 p-4 cursor-pointer text-xl font-bold text-white rounded-lg transition">
          {{ t('manageByGradeLink') }}
        </RouterLink>
        <RouterLink to="/sandbox"
          class="bg-green-500 hover:bg-green-700 p-4 cursor-pointer text-xl font-bold text-white rounded-lg transition">
          {{ t('createNewSetLink') }}
        </RouterLink>
        <RouterLink to="/bulk-import"
          class="bg-sky-600 hover:bg-sky-700 p-4 cursor-pointer text-xl font-bold text-white rounded-lg transition">
          {{ t('bulkImportTitle') }}
        </RouterLink>
      </div>

      <Spinner v-if="loading" />

    </div>
    <!-- Task list -->  
    <div v-for="(task, taskIndex) in tasks" :key="task.task_id"
      class="border border-gray-300 rounded-lg shadow-sm p-4 mb-6 bg-white overflow-hidden">

      
      <div class="flex flex-col gap-4 lg:flex-row lg:justify-between lg:items-start">

        <div class="flex flex-col min-w-0 flex-1">

          <!-- Task name -->
          <h2 class="text-lg font-semibold mb-2 break-words">
            {{ task.task_name }}
          </h2>

          <!-- Task skills -->
          <div v-if="task.examples.length > 0" class="flex flex-wrap gap-2">
            <span v-for="skill in task.skills" :key="skill.id" class="text-sm text-gray-600 break-words">
              {{ skill.name }}
            </span>
          </div>

          <div class="mt-3">
            <div class="text-sm font-semibold text-slate-700 mb-2">{{ t('assignedGradesLabel') }}</div>
            <div class="flex flex-wrap gap-2">
              <span
                v-if="(task.grade_levels || []).length === 0"
                class="inline-flex items-center rounded-full bg-amber-100 text-amber-800 px-3 py-1 text-xs font-semibold"
              >
                {{ t('unassignedTaskLabel') }}
              </span>
              <span
                v-for="grade in task.grade_levels"
                :key="grade.id"
                class="inline-flex items-center rounded-full bg-sky-100 text-sky-800 px-3 py-1 text-xs font-semibold"
              >
                {{ grade.grade }}. {{ t('grade') }}
              </span>
            </div>
          </div>

          <div class="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div class="text-sm font-semibold text-slate-800 mb-2">{{ t('manuallyAssignGradesLabel') }}</div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              <label
                v-for="grade in gradeLevels"
                :key="grade.id"
                class="inline-flex items-center gap-2 text-sm text-slate-700 break-words"
              >
                <input
                  type="checkbox"
                  :checked="(selectedGrades[task.task_id] || []).includes(grade.id)"
                  @change="toggleGradeSelection(task.task_id, grade.id, $event.target.checked)"
                >
                <span>{{ grade.grade }}. {{ t('grade') }}</span>
              </label>
            </div>
            <button
              @click="saveTaskGrades(taskIndex)"
              :disabled="savingGrades[task.task_id]"
              class="mt-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm py-2 px-3 rounded font-bold transition"
            >
              {{ savingGrades[task.task_id] ? t('saving') : t('saveGrades') }}
            </button>
          </div>

        </div>

        <!-- Task actions -->
        <div class="flex flex-col sm:flex-row gap-2 lg:flex-shrink-0">
          <button @click="handleEditTask(taskIndex)"
            class="bg-amber-500 hover:bg-amber-600 text-white text-sm py-2 px-3 rounded font-bold transition whitespace-nowrap"
            :title="t('editSetTitle')">
            {{ t('editButton') }}
          </button>
          <button @click="confirmDeleteTask(task.task_id, taskIndex, task.task_name)"
            class="bg-red-500 hover:bg-red-700 text-white text-sm py-2 px-3 rounded font-bold transition whitespace-nowrap"
            :title="t('deleteWholeSetTitle')">
            {{ t('delete') }}
          </button>
        </div>

      </div>

      <!-- Tasks example list -->
      <details class="group">

        <summary class="cursor-pointer font-medium text-blue-600 hover:underline">
          {{ t('showExamplesToggle') }}
        </summary>

        <div class="mt-4">
          <div v-for="example in task.examples" :key="example.example_id"
            class="flex flex-col gap-3 lg:flex-row lg:justify-between lg:items-start mb-4 border-b pb-3 min-w-0">

            <p class="text-gray-700 min-w-0 break-words lg:flex-1">
              <span>{{ t('exampleLabel') }}</span> <span v-html="example.example" class="font-semibold text-black dark:text-white break-words"></span>
            </p>

            <p class="text-gray-700 break-words lg:min-w-[140px] lg:text-right">
              <span>{{ t('resultLabel') }} </span>
              <span v-html="example.answers.map(a => a.answer_text).join(', ')" class="font-semibold text-black dark:text-white"></span>
            </p>

          </div>
        </div>

      </details>
    </div>
  </div>

  <!-- Delete task confirmation modal -->
  <div v-if="showDeleteModal" class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
    <div class="bg-white p-6 rounded-lg shadow-lg w-[92%] max-w-2xl">
      <h2 class="text-2xl mb-4 break-words">{{ t('confirmDeleteTaskSetMessage', { name: taskToDeleteName }) }}</h2>
      <p class="mt-2 text-lg font-semibold text-red-600"><i class="fa-solid fa-triangle-exclamation text-xl"></i> {{ t('actionIrreversibleWarning') }} </p>
      <div class="flex flex-col sm:flex-row sm:justify-end gap-3 mt-4 font-semibold text-xl">
        <button @click="cancelDelete"
          class="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400">
          {{ t('cancel') }}
        </button>
        <button @click="handleDeleteTask"
          class="px-4 py-1 bg-red-500 text-white rounded-lg hover:bg-red-600 transition font-semibold">
          {{ t('delete') }}
        </button>
      </div>
    </div>
  </div>
  
</template>
