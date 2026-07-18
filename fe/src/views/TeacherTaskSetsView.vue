<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';
import { getTasksByGrade, assignTaskToClassroom, getClassroomDetail, getTaskExamples, copyTaskForTeacher } from '@/api/apiClient';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ classroomId: [String, Number] });

const router = useRouter();
const authStore = useAuthStore();
const toastStore = useToastStore();
const copyingId = ref(null);

const isMine = (task) => Number(task.owner_teacher_id) === Number(authStore.id);

const editTask = (task) => {
  router.push({ name: 'teacher-edit-task', params: { classroomId: props.classroomId, taskId: task.id } });
};

const copyAndEdit = async (task) => {
  copyingId.value = task.id;
  try {
    const result = await copyTaskForTeacher(authStore.id, task.id);
    toastStore.addToast({ message: 'Sada skopírovaná do tvojej knižnice.', type: 'success', visible: true });
    router.push({ name: 'teacher-edit-task', params: { classroomId: props.classroomId, taskId: result.task_id } });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri kopírovaní sady.', type: 'error', visible: true });
  }
  copyingId.value = null;
};

const classroom = ref(null);
const expanded = reactive({});
const gradeLoading = reactive({});
const gradeTasks = reactive({});
const assignedTaskIds = ref([]);
const assigning = ref(null);

const expandedTasks = reactive({});
const taskExamples = reactive({});
const taskExamplesLoading = reactive({});

const toggleTask = async (task) => {
  const key = task.id;
  expandedTasks[key] = !expandedTasks[key];
  if (expandedTasks[key] && taskExamples[key] === undefined) {
    taskExamplesLoading[key] = true;
    try {
      taskExamples[key] = await getTaskExamples(task.id) || [];
    } catch (e) {
      taskExamples[key] = [];
    }
    taskExamplesLoading[key] = false;
  }
};

const showModal = ref(false);
const pendingTask = ref(null);
const isHomework = ref(false);
const dueDate = ref('');

const loadAssigned = async () => {
  try {
    const data = await getClassroomDetail(props.classroomId, { teacherId: authStore.id });
    classroom.value = data;
    assignedTaskIds.value = (data.task_assignments || []).map(a => a.task_id);
  } catch (e) {
    console.error(e);
  }
};

const toggleGrade = async (grade) => {
  expanded[grade] = !expanded[grade];
  if (expanded[grade] && gradeTasks[grade] === undefined) {
    gradeLoading[grade] = true;
    gradeTasks[grade] = await getTasksByGrade(grade) || [];
    gradeLoading[grade] = false;
  }
};

const openModal = (task) => {
  pendingTask.value = task;
  isHomework.value = false;
  dueDate.value = '';
  showModal.value = true;
};

const confirmAssign = async () => {
  if (!pendingTask.value) return;
  assigning.value = pendingTask.value.id;
  showModal.value = false;
  try {
    await assignTaskToClassroom(
      props.classroomId, authStore.id, pendingTask.value.id,
      isHomework.value, dueDate.value || null,
    );
    assignedTaskIds.value = [...assignedTaskIds.value, pendingTask.value.id];
    toastStore.addToast({ message: 'Úloha priradená', type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri priraďovaní', type: 'error', visible: true });
  }
  assigning.value = null;
  pendingTask.value = null;
};

onMounted(loadAssigned);
</script>

<template>
  <div class="pt-24 px-4 max-w-4xl mx-auto">

    <div class="flex items-center gap-2 mb-4">
      <router-link :to="{ name: 'teacher-classroom', params: { classroomId } }"
                   class="text-secondary hover:underline text-sm">
        &larr; Späť do triedy
      </router-link>
    </div>

    <div class="flex items-center justify-between mb-1">
      <h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100">Príkladové sady</h1>
      <router-link :to="{ name: 'teacher-create-task', params: { classroomId } }"
                   class="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600
                          font-semibold transition-colors text-sm">
        + Vytvoriť novú sadu
      </router-link>
    </div>
    <p v-if="classroom" class="text-sm text-gray-500 dark:text-gray-400 mb-6">
      {{ classroom.name }}
    </p>
    <div v-else class="mb-6" />

    <!-- Grade accordion -->
    <div class="space-y-2">
      <div v-for="grade in [1,2,3,4,5,6,7,8,9]" :key="grade"
           class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">

        <button @click="toggleGrade(grade)"
                class="w-full flex items-center justify-between px-5 py-4 text-left
                       hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
          <span class="font-bold text-slate-800 dark:text-slate-100">{{ grade }}. ročník</span>
          <svg class="w-4 h-4 text-slate-400 transition-transform duration-200"
               :class="expanded[grade] ? 'rotate-180' : ''"
               viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06z" clip-rule="evenodd" />
          </svg>
        </button>

        <template v-if="expanded[grade]">
          <div class="border-t border-slate-100 dark:border-slate-700">

            <div v-if="gradeLoading[grade]" class="flex justify-center py-6">
              <Spinner />
            </div>

            <div v-else-if="!gradeTasks[grade]?.length"
                 class="py-5 text-center text-sm text-gray-400">
              Žiadne úlohy pre {{ grade }}. ročník.
            </div>

            <div v-else class="divide-y divide-slate-100 dark:divide-slate-700/60">
              <div v-for="task in gradeTasks[grade]" :key="task.id">

                <!-- Task row -->
                <div class="flex items-center gap-3 px-5 py-3 hover:bg-slate-50 dark:hover:bg-slate-700/20 cursor-pointer"
                     @click="toggleTask(task)">
                  <svg class="w-3.5 h-3.5 text-slate-400 flex-shrink-0 transition-transform duration-150"
                       :class="expandedTasks[task.id] ? 'rotate-90' : ''"
                       viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06z" clip-rule="evenodd" />
                  </svg>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-slate-800 dark:text-slate-100 text-sm truncate">
                      {{ task.name }}
                    </div>
                    <div class="text-xs text-gray-400 mt-0.5">
                      {{ task.example_count ?? 0 }} príkladov
                    </div>
                  </div>
                  <div class="flex-shrink-0 flex items-center gap-1.5" @click.stop>
                    <button v-if="isMine(task)" @click="editTask(task)"
                            class="px-2.5 py-1.5 text-secondary hover:bg-secondary/10 text-xs rounded-lg font-medium">
                      Upraviť
                    </button>
                    <button v-else @click="copyAndEdit(task)" :disabled="copyingId === task.id"
                            class="px-2.5 py-1.5 text-secondary hover:bg-secondary/10 text-xs rounded-lg font-medium disabled:opacity-50">
                      {{ copyingId === task.id ? '...' : 'Kopírovať a upraviť' }}
                    </button>
                    <span v-if="assignedTaskIds.includes(task.id)"
                          class="text-xs px-3 py-1 bg-green-50 dark:bg-green-900/30
                                 text-green-600 dark:text-green-400 rounded-full font-medium">
                      Priradené
                    </span>
                    <button v-else
                            @click="openModal(task)"
                            :disabled="assigning === task.id"
                            class="px-3 py-1.5 bg-secondary text-white text-xs rounded-lg
                                   hover:bg-blue-600 transition-colors disabled:opacity-50 font-medium">
                      {{ assigning === task.id ? '...' : 'Priradiť' }}
                    </button>
                  </div>
                </div>

                <!-- Expanded: example preview -->
                <div v-if="expandedTasks[task.id]"
                     class="bg-slate-50 dark:bg-slate-900/40 border-t border-slate-100 dark:border-slate-700/50 px-5 py-3">
                  <div v-if="taskExamplesLoading[task.id]" class="flex justify-center py-4">
                    <Spinner />
                  </div>
                  <div v-else-if="!taskExamples[task.id]?.length"
                       class="text-xs text-gray-400 py-2 text-center">
                    Žiadne príklady.
                  </div>
                  <div v-else class="flex flex-wrap gap-2">
                    <span v-for="ex in taskExamples[task.id]" :key="ex.id"
                          class="px-2.5 py-1 bg-white dark:bg-slate-800 border border-slate-200
                                 dark:border-slate-700 rounded-lg text-xs font-mono
                                 text-slate-700 dark:text-slate-300">
                      {{ ex.example }}
                    </span>
                  </div>
                </div>

              </div>
            </div>

          </div>
        </template>
      </div>
    </div>

    <!-- Assign modal -->
    <div v-if="showModal"
         class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
         @click.self="showModal = false">
      <div class="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-sm shadow-xl">
        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 mb-1">
          {{ pendingTask?.name }}
        </h3>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">Nastavte priradenie</p>

        <label class="flex items-center gap-3 mb-4 cursor-pointer">
          <input type="checkbox" v-model="isHomework" class="w-4 h-4 accent-secondary" />
          <span class="text-sm text-slate-700 dark:text-slate-300">Označiť ako domácu úlohu</span>
        </label>

        <div v-if="isHomework" class="mb-4">
          <label class="block text-sm text-slate-700 dark:text-slate-300 mb-1">Termín odovzdania</label>
          <input type="date" v-model="dueDate"
                 class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                        bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100
                        focus:outline-none focus:ring-2 focus:ring-secondary" />
        </div>

        <div class="flex gap-3 justify-end">
          <button @click="showModal = false"
                  class="px-4 py-2 rounded-md text-gray-600 dark:text-gray-300
                         hover:bg-gray-100 dark:hover:bg-slate-700">
            Zrušiť
          </button>
          <button @click="confirmAssign"
                  class="px-4 py-2 bg-secondary text-white rounded-md hover:bg-blue-600 font-semibold">
            Priradiť
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
