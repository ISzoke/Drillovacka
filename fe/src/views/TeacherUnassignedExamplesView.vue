<script setup>
import { ref, reactive, onMounted, nextTick, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import {
  getMyTeacherTasks, teacherListExamples, teacherCreateExample, teacherUpdateExample, teacherDeleteExample,
  teacherBulkSetGrade, teacherBulkDelete,
} from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import TeacherIcon from '@/components/TeacherIcon.vue';
import TeacherPageHeader from '@/components/TeacherPageHeader.vue';
import TeacherBulkOrganizeModal from '@/components/TeacherBulkOrganizeModal.vue';

const authStore = useAuthStore();
const toastStore = useToastStore();
const { t } = useI18n();

const myTasks = ref([]);

const loadingExamples = ref(true);
const examples = ref([]);
const gradeFilter = ref(null);
const searchQuery = ref('');
let searchDebounce = null;

const selectedIds = ref(new Set());
const toggleSelect = (id) => {
  const s = new Set(selectedIds.value);
  s.has(id) ? s.delete(id) : s.add(id);
  selectedIds.value = s;
};
const selectAllVisible = () => { selectedIds.value = new Set(examples.value.map(e => e.id)); };
const clearSelection = () => { selectedIds.value = new Set(); };

const showOrganizeModal = ref(false);
const organizeDefaultHomework = ref(false);
const bulkGradeChoice = ref(null);
const bulkGrading = ref(false);
const bulkDeleting = ref(false);

const expandedId = ref(null);
const editingId = ref(null);
const editDraft = reactive({ example: '', input_type: 'INLINE', answer: '', steps: [], grade: null });
const saving = ref(false);

const showNewForm = ref(false);
const newExample = reactive({ example: '', input_type: 'INLINE', answer: '', steps: [], grade: null });
const creating = ref(false);

watch([examples, editDraft, newExample], async () => {
  await nextTick();
  window.MathJax?.typeset();
}, { deep: true });

const loadTasks = async () => {
  try {
    myTasks.value = await getMyTeacherTasks(authStore.id);
  } catch (e) {
    myTasks.value = [];
  }
};

const loadExamples = async () => {
  loadingExamples.value = true;
  try {
    examples.value = await teacherListExamples(authStore.id, {
      grade: gradeFilter.value,
      search: searchQuery.value,
      unattachedOnly: true,
    });
  } catch (e) {
    examples.value = [];
  }
  loadingExamples.value = false;
};

onMounted(() => { loadTasks(); loadExamples(); });
watch(gradeFilter, loadExamples);
watch(searchQuery, () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadExamples, 300);
});
watch(examples, clearSelection);

const openOrganizeModal = (defaultHomework) => {
  organizeDefaultHomework.value = defaultHomework;
  showOrganizeModal.value = true;
};

const onOrganizeSuccess = () => {
  showOrganizeModal.value = false;
  clearSelection();
  loadTasks();
  loadExamples();
};

const bulkApplyGrade = async () => {
  bulkGrading.value = true;
  try {
    await teacherBulkSetGrade(authStore.id, [...selectedIds.value], bulkGradeChoice.value);
    toastStore.addToast({ message: t('gradeSetForSelected'), type: 'success', visible: true });
    clearSelection();
    await loadExamples();
  } catch (e) {
    toastStore.addToast({ message: t('errorSettingGrade'), type: 'error', visible: true });
  }
  bulkGrading.value = false;
};

const bulkDeleteSelected = async () => {
  const n = selectedIds.value.size;
  if (!confirm(t('confirmBulkDeleteExamples', { n }))) return;
  bulkDeleting.value = true;
  try {
    await teacherBulkDelete(authStore.id, [...selectedIds.value]);
    toastStore.addToast({ message: t('examplesDeletedCount', { n }), type: 'success', visible: true });
    clearSelection();
    await loadExamples();
  } catch (e) {
    toastStore.addToast({ message: t('errorDeleting'), type: 'error', visible: true });
  }
  bulkDeleting.value = false;
};

const toggleExpand = (ex) => {
  if (editingId.value === ex.id) return;
  expandedId.value = expandedId.value === ex.id ? null : ex.id;
};

const startEdit = (ex) => {
  editingId.value = ex.id;
  expandedId.value = ex.id;
  editDraft.example = ex.example;
  editDraft.input_type = ex.input_type;
  editDraft.answer = ex.answer;
  editDraft.steps = [...ex.steps];
  editDraft.grade = ex.grade;
};

const cancelEdit = () => { editingId.value = null; };

const addStep = (target) => target.steps.push('');
const removeStep = (target, i) => target.steps.splice(i, 1);

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

const deleteForeverAction = async (ex) => {
  if (!confirm(t('confirmDeleteExample', { example: ex.example }))) return;
  try {
    await teacherDeleteExample(ex.id, authStore.id);
    examples.value = examples.value.filter(e => e.id !== ex.id);
    toastStore.addToast({ message: t('exampleDeleted'), type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: t('errorDeleting'), type: 'error', visible: true });
  }
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
    if (gradeFilter.value === null || gradeFilter.value === created.grade) {
      examples.value.unshift(created);
    }
    newExample.example = ''; newExample.answer = ''; newExample.steps = []; newExample.grade = null;
    showNewForm.value = false;
    toastStore.addToast({ message: t('exampleAddedToLibrary'), type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: t('errorCreatingExample'), type: 'error', visible: true });
  }
  creating.value = false;
};
</script>

<template>
  <div class="pt-20 px-4 max-w-3xl mx-auto pb-16">

    <TeacherPageHeader
      :crumbs="[{ label: t('myLibrary'), to: { name: 'teacher-library' } }]"
      :current="t('unassigned')"
      :title="t('unassignedExamplesTitle')"
      :subtitle="t('unassignedExamplesSubtitle')" />

    <div class="flex items-center justify-between mb-3 gap-2">
      <div class="flex-1"></div>
      <div class="flex items-center gap-2">
        <input v-model="searchQuery" type="text" :placeholder="t('search') + '...'"
               class="w-36 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                      bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                      focus:outline-none focus:ring-1 focus:ring-secondary" />
        <select v-model="gradeFilter"
                class="px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                       bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                       focus:outline-none focus:ring-1 focus:ring-secondary">
          <option :value="null">{{ t('allGrades') }}</option>
          <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. {{ t('grade') }}</option>
        </select>
      </div>
    </div>

    <!-- Selection toolbar -->
    <div v-if="selectedIds.size" class="flex items-center flex-wrap gap-2 mb-3 px-3 py-2 rounded-xl bg-secondary/10">
      <span class="text-xs font-semibold text-secondary mr-1">{{ selectedIds.size }} {{ t('selectedCount') }}</span>
      <button @click="openOrganizeModal(false)"
              class="flex items-center gap-1 text-xs px-2.5 py-1.5 bg-white dark:bg-slate-800 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
        <TeacherIcon name="library" :size="12" /> {{ t('createSet') }}
      </button>
      <button @click="openOrganizeModal(true)"
              class="flex items-center gap-1 text-xs px-2.5 py-1.5 bg-white dark:bg-slate-800 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
        <TeacherIcon name="calendar" :size="12" /> {{ t('assignAsHomework') }}
      </button>
      <router-link :to="{ name: 'teacher-print', query: { ids: [...selectedIds].join(',') } }"
                   class="flex items-center gap-1 text-xs px-2.5 py-1.5 bg-white dark:bg-slate-800 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
        <TeacherIcon name="print" :size="12" /> {{ t('printPdf') }}
      </router-link>
      <div class="flex items-center gap-1">
        <select v-model="bulkGradeChoice"
                class="px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                       bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs">
          <option :value="null">{{ t('gradeAbbrNone') }}</option>
          <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. {{ t('gradeAbbr') }}</option>
        </select>
        <button @click="bulkApplyGrade" :disabled="bulkGrading"
                class="text-xs px-2.5 py-1.5 bg-white dark:bg-slate-800 text-secondary rounded-lg hover:bg-secondary/20 font-medium disabled:opacity-50">
          {{ bulkGrading ? '...' : t('setGrade') }}
        </button>
      </div>
      <button @click="bulkDeleteSelected" :disabled="bulkDeleting"
              class="flex items-center gap-1 text-xs px-2.5 py-1.5 bg-white dark:bg-slate-800 text-accent rounded-lg hover:bg-accent/10 font-medium disabled:opacity-50">
        <TeacherIcon name="delete" :size="12" /> {{ bulkDeleting ? '...' : t('delete') }}
      </button>
      <button @click="clearSelection" class="text-xs px-2 py-1.5 text-gray-400 hover:text-gray-600 ml-auto">
        {{ t('clearSelectionAction') }}
      </button>
    </div>

    <div v-if="loadingExamples" class="flex justify-center py-6"><Spinner /></div>

    <div v-else class="space-y-2 mb-4">
      <div v-if="examples.length" class="flex justify-end -mt-1">
        <button @click="selectAllVisible" class="text-xs text-secondary hover:underline">{{ t('selectAllVisible') }}</button>
      </div>
      <div v-for="ex in examples" :key="ex.id"
           class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">

        <!-- Collapsed row (click to expand) -->
        <div class="flex items-center gap-2 px-3 py-2.5 cursor-pointer select-none" @click="toggleExpand(ex)">
          <input type="checkbox" :checked="selectedIds.has(ex.id)" @click.stop="toggleSelect(ex.id)"
                 class="w-4 h-4 accent-secondary flex-shrink-0" />
          <TeacherIcon name="chevronDown" :size="13"
                       class="text-slate-400 flex-shrink-0 transition-transform"
                       :class="expandedId === ex.id ? 'rotate-180' : '-rotate-90'" />
          <div class="flex-1 min-w-0 font-mono text-sm text-slate-800 dark:text-slate-100 truncate">
            {{ ex.example }} <span class="text-secondary font-semibold">= {{ ex.answer }}</span>
          </div>
          <span v-if="ex.grade" class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-tertiary/50 text-primary dark:bg-tertiary/20 dark:text-tertiary flex-shrink-0">
            {{ ex.grade }}. {{ t('gradeAbbr') }}
          </span>
          <span v-else class="text-[11px] px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-gray-400 flex-shrink-0">
            {{ t('noGrade') }}
          </span>
          <div class="flex items-center gap-0.5 pl-2 border-l border-slate-100 dark:border-slate-700 flex-shrink-0" @click.stop>
            <button @click="startEdit(ex)" :title="t('edit')"
                    class="p-1.5 rounded-lg text-gray-400 hover:text-secondary hover:bg-secondary/10">
              <TeacherIcon name="edit" :size="14" />
            </button>
            <button @click="deleteForeverAction(ex)" :title="t('deleteForever')"
                    class="p-1.5 rounded-lg text-gray-400 hover:text-accent hover:bg-accent/10">
              <TeacherIcon name="delete" :size="14" />
            </button>
          </div>
        </div>

        <!-- Expanded detail / edit -->
        <div v-if="expandedId === ex.id" class="border-t border-slate-100 dark:border-slate-700 px-3 py-3 bg-slate-50 dark:bg-slate-900/40">

          <div v-if="editingId !== ex.id" class="text-xs text-gray-500 dark:text-gray-400 space-y-1.5">
            <div><span class="text-gray-400">{{ t('type') }}:</span> {{ ex.input_type }}</div>
            <div>
              <span class="text-gray-400">{{ t('location') }}:</span>
              {{ t('unassignedLocationText') }}
            </div>
            <div v-if="ex.steps.length">
              <span class="text-gray-400">{{ t('solutionSteps') }}:</span>
              <ol class="list-decimal list-inside mt-1 space-y-0.5">
                <li v-for="(s, i) in ex.steps" :key="i">{{ s }}</li>
              </ol>
            </div>
          </div>

          <div v-else class="space-y-2">
            <input v-model="editDraft.example" type="text" :placeholder="t('examplePlaceholder')"
                   class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                          bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                          font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
            <div class="flex gap-2">
              <select v-model="editDraft.input_type"
                      class="w-28 px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                             bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                             focus:outline-none focus:ring-1 focus:ring-secondary">
                <option value="INLINE">INLINE</option>
                <option value="FRAC">FRAC</option>
                <option value="WORD">WORD</option>
                <option value="VAR">VAR</option>
              </select>
              <input v-model="editDraft.answer" type="text" :placeholder="t('answerPlaceholder')"
                     class="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                            bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                            font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
              <select v-model="editDraft.grade"
                      class="w-20 px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                             bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                             focus:outline-none focus:ring-1 focus:ring-secondary">
                <option :value="null">{{ t('gradeAbbrNone') }}</option>
                <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. {{ t('gradeAbbr') }}</option>
              </select>
            </div>
            <div class="space-y-1.5">
              <div v-for="(step, i) in editDraft.steps" :key="i" class="flex gap-2">
                <input v-model="editDraft.steps[i]" type="text" :placeholder="t('stepPlaceholder', { n: i + 1 })"
                       class="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                              bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
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
      </div>

      <div v-if="!examples.length" class="text-sm text-gray-400 text-center py-6">
        <template v-if="searchQuery">{{ t('noExamplesForSearch', { query: searchQuery }) }}</template>
        <template v-else-if="gradeFilter">{{ t('noExamplesForGrade', { grade: gradeFilter }) }}</template>
        <template v-else>{{ t('noUnassignedExamples') }}</template>
      </div>
    </div>

    <button @click="showNewForm = !showNewForm"
            class="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
      <TeacherIcon name="plus" :size="12" /> {{ t('newExampleToLibrary') }}
    </button>

    <div v-if="showNewForm" class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-3 space-y-2 mt-3">
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
          <option :value="null">{{ t('gradeAbbrNone') }}</option>
          <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. {{ t('gradeAbbr') }}</option>
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
        {{ creating ? t('addingEllipsis') : t('addToLibrary') }}
      </button>
    </div>

    <TeacherBulkOrganizeModal v-if="showOrganizeModal"
                              :example-ids="[...selectedIds]"
                              :my-tasks="myTasks"
                              :default-homework="organizeDefaultHomework"
                              @close="showOrganizeModal = false"
                              @success="onOrganizeSuccess" />

  </div>
</template>
