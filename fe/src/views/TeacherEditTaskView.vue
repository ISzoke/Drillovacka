<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import {
  getTeacherTaskExamples, teacherCreateExample, teacherUpdateExample, teacherDeleteExample,
  attachExampleToTask, detachExampleFromTask, teacherListExamples, deleteTeacherTask,
} from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import TeacherIcon from '@/components/TeacherIcon.vue';
import TeacherPageHeader from '@/components/TeacherPageHeader.vue';
import TeacherGenerateMoreExamplesModal from '@/components/TeacherGenerateMoreExamplesModal.vue';

const props = defineProps({ classroomId: [String, Number], taskId: [String, Number] });

const router = useRouter();
const authStore = useAuthStore();
const toastStore = useToastStore();
const { t } = useI18n();

const loading = ref(true);
const taskName = ref('');
const examples = ref([]);
const editingId = ref(null);
const editDraft = reactive({ example: '', input_type: 'INLINE', answer: '', steps: [], grade: null });
const saving = ref(false);
const deletingTask = ref(false);

const showNewForm = ref(false);
const newExample = reactive({ example: '', input_type: 'INLINE', answer: '', steps: [], grade: null });
const creating = ref(false);

const backTarget = () => props.classroomId
  ? { name: 'teacher-task-sets', params: { classroomId: props.classroomId } }
  : { name: 'teacher-library' };

const showLibrary = ref(false);
const libraryLoading = ref(false);
const libraryExamples = ref([]);
const attachingId = ref(null);

const showGenerateMore = ref(false);
const onGenerateMoreSuccess = (created) => {
  showGenerateMore.value = false;
  examples.value.push(...created);
  toastStore.addToast({ message: t('examplesAddedFromAi', { count: created.length }), type: 'success', visible: true });
};

// Live "what the student sees" preview — reflects whichever draft is currently being edited/created.
const previewDraft = computed(() => {
  if (editingId.value !== null) return editDraft;
  if (showNewForm.value) return newExample;
  return null;
});

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
    toastStore.addToast({ message: t('notYourTaskSet'), type: 'error', visible: true });
    router.push({ name: 'teacher-task-sets', params: { classroomId: props.classroomId } });
  }
  loading.value = false;
};

onMounted(load);

const startEdit = (ex) => {
  showNewForm.value = false;
  editingId.value = ex.id;
  editDraft.example = ex.example;
  editDraft.input_type = ex.input_type;
  editDraft.answer = ex.answer;
  editDraft.steps = [...ex.steps];
  editDraft.grade = ex.grade;
};

const cancelEdit = () => { editingId.value = null; };

const saveEdit = async (ex) => {
  saving.value = true;
  try {
    const updated = await teacherUpdateExample(ex.id, authStore.id, {
      example: editDraft.example, inputType: editDraft.input_type,
      answer: editDraft.answer, steps: editDraft.steps.filter(s => s.trim()),
      grade: editDraft.grade,
    });
    const i = examples.value.findIndex(e => e.id === ex.id);
    if (i !== -1) examples.value[i] = updated;
    editingId.value = null;
    toastStore.addToast({ message: t('exampleSaved'), type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: t('errorSavingExample'), type: 'error', visible: true });
  }
  saving.value = false;
};

const addStep = (target) => target.steps.push('');
const removeStep = (target, i) => target.steps.splice(i, 1);

const detach = async (ex) => {
  if (!confirm(t('confirmDetachExample', { example: ex.example }))) return;
  try {
    await detachExampleFromTask(props.taskId, authStore.id, ex.id);
    examples.value = examples.value.filter(e => e.id !== ex.id);
    toastStore.addToast({ message: t('exampleDetached'), type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: t('errorRemoving'), type: 'error', visible: true });
  }
};

const deleteForever = async (ex) => {
  if (!confirm(t('confirmDeleteExampleForever', { example: ex.example }))) return;
  try {
    await teacherDeleteExample(ex.id, authStore.id);
    examples.value = examples.value.filter(e => e.id !== ex.id);
    toastStore.addToast({ message: t('exampleDeleted'), type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: t('errorDeleting'), type: 'error', visible: true });
  }
};

const openNewForm = () => {
  editingId.value = null;
  showNewForm.value = true;
};

const submitNewExample = async () => {
  if (!newExample.example.trim() || !newExample.answer.trim()) {
    toastStore.addToast({ message: t('fillExampleAndAnswer'), type: 'error', visible: true });
    return;
  }
  creating.value = true;
  try {
    const created = await teacherCreateExample(authStore.id, {
      example: newExample.example, inputType: newExample.input_type,
      answer: newExample.answer, steps: newExample.steps.filter(s => s.trim()),
      grade: newExample.grade,
    });
    const attached = await attachExampleToTask(props.taskId, authStore.id, created.id);
    examples.value.push(attached);
    newExample.example = ''; newExample.answer = ''; newExample.steps = []; newExample.grade = null;
    showNewForm.value = false;
    toastStore.addToast({ message: t('exampleAdded'), type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: t('errorCreatingExample'), type: 'error', visible: true });
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
    toastStore.addToast({ message: t('exampleAddedFromLibrary'), type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: t('errorAdding'), type: 'error', visible: true });
  }
  attachingId.value = null;
};

const deleteTask = async () => {
  if (!confirm(t('confirmDeleteTaskSet', { name: taskName.value }))) return;
  deletingTask.value = true;
  try {
    await deleteTeacherTask(props.taskId, authStore.id);
    toastStore.addToast({ message: t('taskSetDeleted'), type: 'success', visible: true });
    router.push({ name: 'teacher-task-sets', params: { classroomId: props.classroomId } });
  } catch (e) {
    toastStore.addToast({ message: t('errorDeletingTaskSet'), type: 'error', visible: true });
    deletingTask.value = false;
  }
};
</script>

<template>
  <div class="pt-20 px-4 max-w-4xl mx-auto pb-16">

    <TeacherPageHeader
      :crumbs="[{ label: classroomId ? t('taskSetsTitle') : t('myLibrary'), to: backTarget() }]"
      :current="taskName"
      :title="taskName">
      <template #action>
        <button @click="deleteTask" :disabled="deletingTask"
                class="text-xs px-3 py-1.5 text-accent hover:bg-accent/10 rounded-lg disabled:opacity-50">
          {{ deletingTask ? '...' : t('deleteTaskSet') }}
        </button>
      </template>
    </TeacherPageHeader>

    <div v-if="loading" class="flex justify-center py-16"><Spinner /></div>

    <div v-else class="grid lg:grid-cols-[1fr_220px] gap-6 items-start">
      <div>
        <div class="space-y-2 mb-4">
          <div v-for="ex in examples" :key="ex.id"
               class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-3">

            <!-- Read-only row -->
            <div v-if="editingId !== ex.id" class="flex gap-2 items-center">
              <div class="flex-1 min-w-0">
                <div class="font-mono text-sm text-slate-800 dark:text-slate-100">
                  {{ ex.example }} <span class="text-secondary font-semibold">= {{ ex.answer }}</span>
                </div>
                <div class="text-xs text-gray-400 mt-1">
                  {{ ex.input_type }}
                  <span v-if="ex.steps.length"> · {{ t('stepsCountText', { count: ex.steps.length }) }}</span>
                </div>
              </div>
              <span v-if="ex.grade" class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-tertiary/50 text-primary dark:bg-tertiary/20 dark:text-tertiary flex-shrink-0">
                {{ t('gradeShortLabel', { grade: ex.grade }) }}
              </span>
              <div class="flex items-center gap-0.5 pl-2 border-l border-slate-100 dark:border-slate-700 flex-shrink-0">
                <button @click="startEdit(ex)" :title="t('edit')"
                        class="p-1.5 rounded-lg text-gray-400 hover:text-secondary hover:bg-secondary/10">
                  <TeacherIcon name="edit" :size="14" />
                </button>
                <button @click="detach(ex)" :title="t('removeFromSet')"
                        class="p-1.5 rounded-lg text-gray-400 hover:text-secondary hover:bg-secondary/10">
                  <TeacherIcon name="remove" :size="14" />
                </button>
                <button @click="deleteForever(ex)" :title="t('deleteForever')"
                        class="p-1.5 rounded-lg text-gray-400 hover:text-accent hover:bg-accent/10">
                  <TeacherIcon name="delete" :size="14" />
                </button>
              </div>
            </div>

            <!-- Edit form -->
            <div v-else class="space-y-2">
              <input v-model="editDraft.example" type="text" :placeholder="t('examplePlaceholder')"
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
                <input v-model="editDraft.answer" type="text" :placeholder="t('answerPlaceholder')"
                       class="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                              bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                              font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
                <select v-model="editDraft.grade"
                        class="w-20 px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                               bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-xs
                               focus:outline-none focus:ring-1 focus:ring-secondary">
                  <option :value="null">{{ t('gradeNoneLabel') }}</option>
                  <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ t('gradeShortLabel', { grade: g }) }}</option>
                </select>
              </div>
              <div class="space-y-1.5">
                <div v-for="(step, i) in editDraft.steps" :key="i" class="flex gap-2">
                  <input v-model="editDraft.steps[i]" type="text" :placeholder="t('stepPlaceholder', { n: i + 1 })"
                         class="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                                bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                                focus:outline-none focus:ring-1 focus:ring-secondary" />
                  <button @click="removeStep(editDraft, i)" class="text-accent/70 hover:text-accent text-lg leading-none">×</button>
                </div>
                <button @click="addStep(editDraft)" class="text-xs text-secondary hover:underline">{{ t('addStep') }}</button>
              </div>
              <div class="flex gap-2 pt-1 justify-end">
                <button @click="cancelEdit" class="px-3 py-1.5 rounded-lg text-gray-500 hover:bg-slate-100 dark:hover:bg-slate-700 text-xs">
                  {{ t('cancel') }}
                </button>
                <button @click="saveEdit(ex)" :disabled="saving"
                        class="px-3 py-1.5 rounded-lg bg-secondary text-white text-xs font-semibold hover:bg-blue-600 disabled:opacity-50">
                  {{ saving ? t('saving') : t('save') }}
                </button>
              </div>
            </div>
          </div>

          <div v-if="!examples.length" class="text-sm text-gray-400 text-center py-6">
            {{ t('emptyTaskSet') }}
          </div>
        </div>

        <!-- Add example -->
        <div class="flex gap-3 mb-4">
          <button @click="openNewForm"
                  class="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
            <TeacherIcon name="plus" :size="12" /> {{ t('newExampleBtn') }}
          </button>
          <button @click="openLibrary"
                  class="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
            <TeacherIcon name="library" :size="12" /> {{ t('fromMyLibrary') }}
          </button>
          <button @click="showGenerateMore = true"
                  class="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
            <TeacherIcon name="sparkle" :size="12" /> {{ t('generateMoreAi') }}
          </button>
        </div>

        <div v-if="showNewForm" class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-3 space-y-2 mb-4">
          <input v-model="newExample.example" type="text" :placeholder="t('examplePlaceholder')"
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
            <input v-model="newExample.answer" type="text" :placeholder="t('answerPlaceholder')"
                   class="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                          bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                          font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
            <select v-model="newExample.grade"
                    class="w-20 px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                           bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-xs
                           focus:outline-none focus:ring-1 focus:ring-secondary">
              <option :value="null">{{ t('gradeNoneLabel') }}</option>
              <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ t('gradeShortLabel', { grade: g }) }}</option>
            </select>
          </div>
          <div class="space-y-1.5">
            <div v-for="(step, i) in newExample.steps" :key="i" class="flex gap-2">
              <input v-model="newExample.steps[i]" type="text" :placeholder="t('stepPlaceholder', { n: i + 1 })"
                     class="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                            bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                            focus:outline-none focus:ring-1 focus:ring-secondary" />
              <button @click="removeStep(newExample, i)" class="text-accent/70 hover:text-accent text-lg leading-none">×</button>
            </div>
            <button @click="addStep(newExample)" class="text-xs text-secondary hover:underline">{{ t('addStep') }}</button>
          </div>
          <button @click="submitNewExample" :disabled="creating"
                  class="w-full py-2 bg-secondary text-white rounded-lg font-semibold text-sm hover:bg-blue-600 disabled:opacity-50">
            {{ creating ? t('addingText') : t('addToSet') }}
          </button>
        </div>
      </div>

      <!-- Student preview (sticky) -->
      <div class="hidden lg:block sticky top-24">
        <div v-if="previewDraft" class="bg-primary text-white rounded-3xl px-5 py-6 text-center">
          <div class="text-[10px] uppercase tracking-wider text-white/55 mb-3">{{ t('studentPreview') }}</div>
          <div class="font-mono text-xl font-bold leading-snug break-words">
            <template v-if="previewDraft.input_type === 'WORD'">{{ previewDraft.example || '…' }}</template>
            <template v-else>{{ previewDraft.example || '…' }} = _</template>
          </div>
          <span v-if="previewDraft.grade" class="inline-block mt-3 px-2.5 py-0.5 rounded-full bg-white/15 text-[11px] font-semibold">
            {{ t('gradeFullLabel', { grade: previewDraft.grade }) }}
          </span>
        </div>
        <div v-else class="border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-3xl px-5 py-8 text-center text-xs text-gray-400">
          {{ t('previewPlaceholderText') }}
        </div>
      </div>
    </div>

    <!-- Library modal -->
    <div v-if="showLibrary" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
         @click.self="showLibrary = false">
      <div class="bg-white dark:bg-slate-800 rounded-xl p-5 w-full max-w-lg max-h-[80vh] overflow-y-auto shadow-xl">
        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100 mb-3">{{ t('myLibraryModalTitle') }}</h3>
        <div v-if="libraryLoading" class="flex justify-center py-8"><Spinner /></div>
        <div v-else-if="!libraryExamples.length" class="text-sm text-gray-400 text-center py-8">
          {{ t('noFreeExamplesInLibrary') }}
        </div>
        <div v-else class="space-y-2">
          <div v-for="ex in libraryExamples" :key="ex.id"
               class="flex items-center gap-2 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700">
            <div class="flex-1 min-w-0 font-mono text-sm text-slate-800 dark:text-slate-100 truncate">{{ ex.example }}</div>
            <button @click="attachFromLibrary(ex)" :disabled="attachingId === ex.id"
                    class="text-xs px-2.5 py-1.5 bg-secondary text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 flex-shrink-0">
              {{ attachingId === ex.id ? '...' : t('add') }}
            </button>
          </div>
        </div>
        <button @click="showLibrary = false" class="mt-4 w-full py-2 rounded-lg text-gray-500 hover:bg-slate-100 dark:hover:bg-slate-700 text-sm">
          {{ t('close') }}
        </button>
      </div>
    </div>

    <TeacherGenerateMoreExamplesModal v-if="showGenerateMore"
                                      :task-id="props.taskId"
                                      @close="showGenerateMore = false"
                                      @success="onGenerateMoreSuccess" />

  </div>
</template>
