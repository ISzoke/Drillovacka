<script setup>
import { ref, reactive, onMounted, nextTick, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import {
  getTeacherTaskExamples, teacherCreateExample, teacherUpdateExample, teacherDeleteExample,
  attachExampleToTask, detachExampleFromTask, teacherListExamples, deleteTeacherTask,
} from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ classroomId: [String, Number], taskId: [String, Number] });

const router = useRouter();
const authStore = useAuthStore();
const toastStore = useToastStore();

const loading = ref(true);
const taskName = ref('');
const examples = ref([]);
const editingId = ref(null);
const editDraft = reactive({ example: '', input_type: 'INLINE', answer: '', steps: [] });
const saving = ref(false);
const deletingTask = ref(false);

const showNewForm = ref(false);
const newExample = reactive({ example: '', input_type: 'INLINE', answer: '', steps: [] });
const creating = ref(false);

const showLibrary = ref(false);
const libraryLoading = ref(false);
const libraryExamples = ref([]);
const attachingId = ref(null);

watch([examples, editDraft, newExample], async () => {
  await nextTick();
  window.MathJax?.typeset();
}, { deep: true });

const load = async () => {
  loading.value = true;
  try {
    const data = await getTeacherTaskExamples(props.taskId, authStore.id);
    taskName.value = data.task_name;
    examples.value = data.examples;
  } catch (e) {
    toastStore.addToast({ message: 'Toto nie je vaša sada.', type: 'error', visible: true });
    router.push({ name: 'teacher-task-sets', params: { classroomId: props.classroomId } });
  }
  loading.value = false;
};

onMounted(load);

const startEdit = (ex) => {
  editingId.value = ex.id;
  editDraft.example = ex.example;
  editDraft.input_type = ex.input_type;
  editDraft.answer = ex.answer;
  editDraft.steps = [...ex.steps];
};

const cancelEdit = () => { editingId.value = null; };

const saveEdit = async (ex) => {
  saving.value = true;
  try {
    const updated = await teacherUpdateExample(ex.id, authStore.id, {
      example: editDraft.example, inputType: editDraft.input_type,
      answer: editDraft.answer, steps: editDraft.steps.filter(s => s.trim()),
    });
    const i = examples.value.findIndex(e => e.id === ex.id);
    if (i !== -1) examples.value[i] = updated;
    editingId.value = null;
    toastStore.addToast({ message: 'Príklad uložený.', type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri ukladaní príkladu.', type: 'error', visible: true });
  }
  saving.value = false;
};

const addStep = (target) => target.steps.push('');
const removeStep = (target, i) => target.steps.splice(i, 1);

const detach = async (ex) => {
  if (!confirm(`Odstrániť "${ex.example}" z tejto sady? (ostane v tvojej knižnici)`)) return;
  try {
    await detachExampleFromTask(props.taskId, authStore.id, ex.id);
    examples.value = examples.value.filter(e => e.id !== ex.id);
    toastStore.addToast({ message: 'Príklad odstránený zo sady.', type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri odstraňovaní.', type: 'error', visible: true });
  }
};

const deleteForever = async (ex) => {
  if (!confirm(`Natrvalo zmazať "${ex.example}"? Zmaže sa aj história precvičovania žiakmi.`)) return;
  try {
    await teacherDeleteExample(ex.id, authStore.id);
    examples.value = examples.value.filter(e => e.id !== ex.id);
    toastStore.addToast({ message: 'Príklad zmazaný.', type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri mazaní.', type: 'error', visible: true });
  }
};

const submitNewExample = async () => {
  if (!newExample.example.trim() || !newExample.answer.trim()) {
    toastStore.addToast({ message: 'Vyplň príklad aj odpoveď.', type: 'error', visible: true });
    return;
  }
  creating.value = true;
  try {
    const created = await teacherCreateExample(authStore.id, {
      example: newExample.example, inputType: newExample.input_type,
      answer: newExample.answer, steps: newExample.steps.filter(s => s.trim()),
    });
    const attached = await attachExampleToTask(props.taskId, authStore.id, created.id);
    examples.value.push(attached);
    newExample.example = ''; newExample.answer = ''; newExample.steps = [];
    showNewForm.value = false;
    toastStore.addToast({ message: 'Príklad pridaný.', type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri vytváraní príkladu.', type: 'error', visible: true });
  }
  creating.value = false;
};

const openLibrary = async () => {
  showLibrary.value = true;
  libraryLoading.value = true;
  try {
    libraryExamples.value = await teacherListExamples(authStore.id, { unattachedOnly: true });
  } catch (e) {
    libraryExamples.value = [];
  }
  libraryLoading.value = false;
};

const attachFromLibrary = async (ex) => {
  attachingId.value = ex.id;
  try {
    const attached = await attachExampleToTask(props.taskId, authStore.id, ex.id);
    examples.value.push(attached);
    libraryExamples.value = libraryExamples.value.filter(e => e.id !== ex.id);
    toastStore.addToast({ message: 'Príklad pridaný zo knižnice.', type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri pridávaní.', type: 'error', visible: true });
  }
  attachingId.value = null;
};

const deleteTask = async () => {
  if (!confirm(`Natrvalo zmazať celú sadu "${taskName.value}"?`)) return;
  deletingTask.value = true;
  try {
    await deleteTeacherTask(props.taskId, authStore.id);
    toastStore.addToast({ message: 'Sada zmazaná.', type: 'success', visible: true });
    router.push({ name: 'teacher-task-sets', params: { classroomId: props.classroomId } });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri mazaní sady.', type: 'error', visible: true });
    deletingTask.value = false;
  }
};
</script>

<template>
  <div class="pt-20 px-4 max-w-3xl mx-auto pb-16">

    <div class="flex items-center gap-2 mb-5">
      <router-link :to="{ name: 'teacher-task-sets', params: { classroomId } }"
                   class="text-secondary hover:underline text-sm">
        ← Späť na sady
      </router-link>
    </div>

    <div v-if="loading" class="flex justify-center py-16"><Spinner /></div>

    <template v-else>
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-bold text-primary dark:text-white">{{ taskName }}</h1>
        <button @click="deleteTask" :disabled="deletingTask"
                class="text-xs px-3 py-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg disabled:opacity-50">
          {{ deletingTask ? '...' : 'Zmazať sadu' }}
        </button>
      </div>

      <div class="space-y-3 mb-5">
        <div v-for="ex in examples" :key="ex.id"
             class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-3">

          <!-- Read-only row -->
          <div v-if="editingId !== ex.id" class="flex gap-2 items-start">
            <div class="flex-1 min-w-0">
              <div class="font-mono text-sm text-slate-800 dark:text-slate-100">{{ ex.example }}</div>
              <div class="text-xs text-gray-400 mt-1">
                {{ ex.input_type }} · odpoveď: <span class="font-mono">{{ ex.answer }}</span>
                <span v-if="ex.steps.length"> · {{ ex.steps.length }} krokov</span>
              </div>
            </div>
            <button @click="startEdit(ex)"
                    class="text-xs px-2.5 py-1.5 text-secondary hover:bg-secondary/10 rounded-lg flex-shrink-0">
              Upraviť
            </button>
            <button @click="detach(ex)"
                    class="text-xs px-2.5 py-1.5 text-gray-500 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg flex-shrink-0">
              Odstrániť zo sady
            </button>
            <button @click="deleteForever(ex)"
                    class="text-red-400 hover:text-red-600 flex-shrink-0 text-xl leading-none px-1">×</button>
          </div>

          <!-- Edit form -->
          <div v-else class="space-y-2">
            <input v-model="editDraft.example" type="text" placeholder="Príklad"
                   class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                          bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                          font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
            <div class="flex gap-2">
              <select v-model="editDraft.input_type"
                      class="w-28 px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                             bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-xs
                             focus:outline-none focus:ring-1 focus:ring-secondary">
                <option value="INLINE">INLINE</option>
                <option value="FRAC">FRAC</option>
                <option value="WORD">WORD</option>
                <option value="VAR">VAR</option>
              </select>
              <input v-model="editDraft.answer" type="text" placeholder="Odpoveď"
                     class="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                            bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                            font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
            </div>
            <div class="space-y-1.5">
              <div v-for="(step, i) in editDraft.steps" :key="i" class="flex gap-2">
                <input v-model="editDraft.steps[i]" type="text" :placeholder="`Krok ${i + 1}`"
                       class="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                              bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                              focus:outline-none focus:ring-1 focus:ring-secondary" />
                <button @click="removeStep(editDraft, i)" class="text-red-400 hover:text-red-600 text-lg leading-none">×</button>
              </div>
              <button @click="addStep(editDraft)" class="text-xs text-secondary hover:underline">+ Pridať krok</button>
            </div>
            <div class="flex gap-2 pt-1">
              <button @click="cancelEdit" class="px-3 py-1.5 rounded-lg text-gray-500 hover:bg-slate-100 dark:hover:bg-slate-700 text-xs">
                Zrušiť
              </button>
              <button @click="saveEdit(ex)" :disabled="saving"
                      class="px-3 py-1.5 rounded-lg bg-secondary text-white text-xs font-semibold hover:bg-blue-600 disabled:opacity-50">
                {{ saving ? 'Ukladám...' : 'Uložiť' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="!examples.length" class="text-sm text-gray-400 text-center py-6">
          Táto sada zatiaľ nemá žiadne príklady.
        </div>
      </div>

      <!-- Add example -->
      <div class="flex gap-3 mb-4">
        <button @click="showNewForm = !showNewForm"
                class="text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
          + Nový príklad
        </button>
        <button @click="openLibrary"
                class="text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
          + Z mojej knižnice
        </button>
      </div>

      <div v-if="showNewForm" class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-3 space-y-2 mb-4">
        <input v-model="newExample.example" type="text" placeholder="Príklad"
               class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                      bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                      font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
        <div class="flex gap-2">
          <select v-model="newExample.input_type"
                  class="w-28 px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                         bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-xs
                         focus:outline-none focus:ring-1 focus:ring-secondary">
            <option value="INLINE">INLINE</option>
            <option value="FRAC">FRAC</option>
            <option value="WORD">WORD</option>
            <option value="VAR">VAR</option>
          </select>
          <input v-model="newExample.answer" type="text" placeholder="Odpoveď"
                 class="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                        bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                        font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
        </div>
        <div class="space-y-1.5">
          <div v-for="(step, i) in newExample.steps" :key="i" class="flex gap-2">
            <input v-model="newExample.steps[i]" type="text" :placeholder="`Krok ${i + 1}`"
                   class="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                          bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                          focus:outline-none focus:ring-1 focus:ring-secondary" />
            <button @click="removeStep(newExample, i)" class="text-red-400 hover:text-red-600 text-lg leading-none">×</button>
          </div>
          <button @click="addStep(newExample)" class="text-xs text-secondary hover:underline">+ Pridať krok</button>
        </div>
        <button @click="submitNewExample" :disabled="creating"
                class="w-full py-2 bg-secondary text-white rounded-lg font-semibold text-sm hover:bg-blue-600 disabled:opacity-50">
          {{ creating ? 'Pridávam...' : 'Pridať do sady' }}
        </button>
      </div>
    </template>

    <!-- Library modal -->
    <div v-if="showLibrary" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
         @click.self="showLibrary = false">
      <div class="bg-white dark:bg-slate-800 rounded-xl p-5 w-full max-w-lg max-h-[80vh] overflow-y-auto shadow-xl">
        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3">Moja knižnica (voľné príklady)</h3>
        <div v-if="libraryLoading" class="flex justify-center py-8"><Spinner /></div>
        <div v-else-if="!libraryExamples.length" class="text-sm text-gray-400 text-center py-8">
          Žiadne voľné príklady v knižnici.
        </div>
        <div v-else class="space-y-2">
          <div v-for="ex in libraryExamples" :key="ex.id"
               class="flex items-center gap-2 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700">
            <div class="flex-1 min-w-0 font-mono text-sm text-slate-800 dark:text-slate-100 truncate">{{ ex.example }}</div>
            <button @click="attachFromLibrary(ex)" :disabled="attachingId === ex.id"
                    class="text-xs px-2.5 py-1.5 bg-secondary text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 flex-shrink-0">
              {{ attachingId === ex.id ? '...' : 'Pridať' }}
            </button>
          </div>
        </div>
        <button @click="showLibrary = false" class="mt-4 w-full py-2 rounded-lg text-gray-500 hover:bg-slate-100 dark:hover:bg-slate-700 text-sm">
          Zavrieť
        </button>
      </div>
    </div>

  </div>
</template>
