<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import {
  teacherGenerateTaskPreview, teacherSaveTask, assignTaskToClassroom,
  browseTasks, getTaskExamples, copyTaskForTeacher,
} from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import TeacherIcon from '@/components/TeacherIcon.vue';
import TeacherPageHeader from '@/components/TeacherPageHeader.vue';

const props = defineProps({ classroomId: [String, Number] });

const authStore = useAuthStore();
const toastStore = useToastStore();
const router = useRouter();
const { t } = useI18n();

const mode = ref(null); // null | 'manual' | 'ai-form' | 'ai' | 'browse'

// Browse Aritmation library state
const browseSearch = ref('');
const browseGrade = ref('');
const browseLoading = ref(false);
const browseResults = ref([]);
const browseCopyingId = ref(null);
const expandedBrowseId = ref(null);
const browsePreview = reactive({});
const browsePreviewLoading = reactive({});
let browseSearchDebounce = null;

// AI generation state
const aiType = ref('arithmetic');
const aiCount = ref(10);
const aiDescription = ref('');
const aiGenerating = ref(false);
const aiError = ref('');
const isMix = ref(false);
const mixSegments = ref([
  { type: 'arithmetic', count: 10 },
  { type: 'fractions',  count: 10 },
]);

// Preview / edit state (shared by both modes)
const taskName = ref('');
const taskGrade = ref('');
const examples = ref([]);
const saving = ref(false);

const AI_TYPES_BASE = [
  { value: 'arithmetic', labelKey: 'aiTypeArithmetic',  icon: '±', inputType: 'INLINE' },
  { value: 'fractions',  labelKey: 'aiTypeFractions',   icon: '½', inputType: 'FRAC'   },
  { value: 'word',       labelKey: 'aiTypeWordProblem', icon: '📖', inputType: 'WORD' },
  { value: 'algebra',    labelKey: 'aiTypeAlgebra',     icon: 'x', inputType: 'VAR'    },
];
const AI_TYPES = computed(() => AI_TYPES_BASE.map(item => ({ ...item, label: t(item.labelKey) })));

const selectedType = computed(() => AI_TYPES.value.find(item => item.value === aiType.value));
const hasPreview = computed(() => examples.value.length > 0);
const mixTotal = computed(() => mixSegments.value.reduce((s, seg) => s + Number(seg.count), 0));

// LaTeX re-render whenever examples change
watch(examples, async () => {
  await nextTick();
  window.MathJax?.typeset();
}, { deep: true });

const startManual = () => {
  mode.value = 'manual';
  taskName.value = '';
  taskGrade.value = '';
  examples.value = [{ example: '', input_type: 'INLINE', answer: '' }];
};

const startBrowse = () => {
  mode.value = 'browse';
  loadBrowse();
};

const loadBrowse = async () => {
  browseLoading.value = true;
  try {
    browseResults.value = await browseTasks(browseGrade.value || null, browseSearch.value) || [];
  } catch (e) {
    browseResults.value = [];
  }
  browseLoading.value = false;
};

watch(browseGrade, loadBrowse);
watch(browseSearch, () => {
  clearTimeout(browseSearchDebounce);
  browseSearchDebounce = setTimeout(loadBrowse, 300);
});

const toggleBrowsePreview = async (task) => {
  const key = task.task_id;
  expandedBrowseId.value = expandedBrowseId.value === key ? null : key;
  if (expandedBrowseId.value === key && browsePreview[key] === undefined) {
    browsePreviewLoading[key] = true;
    try {
      browsePreview[key] = await getTaskExamples(key) || [];
    } catch (e) {
      browsePreview[key] = [];
    }
    browsePreviewLoading[key] = false;
  }
};

const copyFromBrowse = async (task) => {
  browseCopyingId.value = task.task_id;
  try {
    const result = await copyTaskForTeacher(authStore.id, task.task_id);
    if (props.classroomId) {
      await assignTaskToClassroom(props.classroomId, authStore.id, result.task_id, false, null);
    }
    toastStore.addToast({ message: t('taskCopiedToLibrary'), type: 'success', visible: true });
    router.push(props.classroomId
      ? { name: 'teacher-edit-task', params: { classroomId: props.classroomId, taskId: result.task_id } }
      : { name: 'teacher-edit-task-standalone', params: { taskId: result.task_id } });
  } catch (e) {
    toastStore.addToast({ message: t('taskCopyError'), type: 'error', visible: true });
  }
  browseCopyingId.value = null;
};

const addExample = () => {
  examples.value.push({ example: '', input_type: selectedType.value?.inputType || 'INLINE', answer: '' });
};

const removeExample = (i) => {
  if (examples.value.length > 1) examples.value.splice(i, 1);
};

const addMixSegment = () => {
  mixSegments.value.push({ type: 'arithmetic', count: 5 });
};

const removeMixSegment = (i) => {
  if (mixSegments.value.length > 1) mixSegments.value.splice(i, 1);
};

const generate = async () => {
  aiError.value = '';
  if (!aiDescription.value.trim()) {
    aiError.value = t('aiDescriptionRequired');
    return;
  }
  aiGenerating.value = true;
  try {
    let data;
    if (isMix.value) {
      data = await teacherGenerateTaskPreview(
        authStore.id, 'mix', null, aiDescription.value,
        mixSegments.value.map(s => ({ type: s.type, count: Number(s.count) })),
      );
    } else {
      data = await teacherGenerateTaskPreview(
        authStore.id, aiType.value, aiCount.value, aiDescription.value,
      );
    }
    taskName.value = data.task_name || '';
    examples.value = (data.examples || []).map(e => ({
      example: e.example,
      input_type: e.input_type,
      answer: e.answer,
    }));
    mode.value = 'ai';
  } catch (e) {
    aiError.value = e?.response?.data?.error || t('aiGenerationError');
  }
  aiGenerating.value = false;
};

const save = async () => {
  const validExamples = examples.value.filter(e => e.example.trim() && e.answer.trim());
  if (!taskName.value.trim()) {
    toastStore.addToast({ message: t('taskNameRequired'), type: 'error', visible: true });
    return;
  }
  if (!validExamples.length) {
    toastStore.addToast({ message: t('addAtLeastOneExample'), type: 'error', visible: true });
    return;
  }
  saving.value = true;
  try {
    const hasWord = validExamples.some(e => e.input_type === 'WORD');
    const allWord = validExamples.every(e => e.input_type === 'WORD');
    const form = allWord ? 'word-problem' : 'classic';

    // If AI-generated, record the prompt + params for admin research purposes
    const genPrompt = mode.value === 'ai' ? aiDescription.value : '';
    const genParams = mode.value === 'ai' ? (isMix.value
      ? { is_mix: true, segments: mixSegments.value }
      : { is_mix: false, type: aiType.value, count: aiCount.value }
    ) : null;

    const result = await teacherSaveTask(
      authStore.id, taskName.value, form, taskGrade.value || null, validExamples,
      genPrompt, genParams,
    );
    if (props.classroomId) {
      await assignTaskToClassroom(props.classroomId, authStore.id, result.task_id, false, null);
    }
    toastStore.addToast({
      message: props.classroomId ? t('taskCreatedAndAssigned') : t('taskCreated'),
      type: 'success', visible: true,
    });
    router.push(props.classroomId
      ? { name: 'teacher-task-sets', params: { classroomId: props.classroomId } }
      : { name: 'teacher-library' });
  } catch (e) {
    toastStore.addToast({ message: t('taskSaveError'), type: 'error', visible: true });
  }
  saving.value = false;
};
</script>

<template>
  <div class="pt-20 px-4 max-w-3xl mx-auto pb-16">

    <TeacherPageHeader
      :crumbs="[props.classroomId
        ? { label: t('taskSetsTitle'), to: { name: 'teacher-task-sets', params: { classroomId: props.classroomId } } }
        : { label: t('myLibrary'), to: { name: 'teacher-library' } }]"
      :current="t('newTaskSet')"
      :title="t('createNewTaskSet')" />

    <!-- ── Mode selection ────────────────────────────────────────────────────── -->
    <div v-if="!hasPreview && mode === null" class="grid sm:grid-cols-3 gap-4">
      <button @click="startManual"
              class="p-6 bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700
                     border-b-[6px] border-b-slate-300 dark:border-b-slate-600
                     hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all text-left">
        <div class="w-11 h-11 rounded-full bg-secondary/10 text-secondary flex items-center justify-center mb-3">
          <TeacherIcon name="edit" :size="20" />
        </div>
        <div class="font-bold text-primary dark:text-white text-lg">{{ t('manualEntryTitle') }}</div>
        <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ t('manualEntryDesc') }}</div>
      </button>

      <button @click="mode = 'ai-form'"
              class="p-6 bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700
                     border-b-[6px] border-b-slate-300 dark:border-b-slate-600
                     hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all text-left">
        <div class="w-11 h-11 rounded-full bg-secondary/10 text-secondary flex items-center justify-center mb-3">
          <TeacherIcon name="sparkle" :size="20" />
        </div>
        <div class="font-bold text-primary dark:text-white text-lg">{{ t('aiGenerateTitle') }}</div>
        <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ t('aiGenerateDesc') }}</div>
      </button>

      <button @click="startBrowse"
              class="p-6 bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700
                     border-b-[6px] border-b-slate-300 dark:border-b-slate-600
                     hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all text-left">
        <div class="w-11 h-11 rounded-full bg-secondary/10 text-secondary flex items-center justify-center mb-3">
          <TeacherIcon name="library" :size="20" />
        </div>
        <div class="font-bold text-primary dark:text-white text-lg">{{ t('fromLibraryTitle') }}</div>
        <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ t('fromLibraryDesc') }}</div>
      </button>
    </div>

    <!-- ── Browse Aritmation library ──────────────────────────────────────────── -->
    <div v-else-if="mode === 'browse'" class="space-y-4">
      <div class="flex gap-3">
        <input v-model="browseSearch" type="text" :placeholder="t('searchTaskSetByName')"
               class="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600
                      bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                      focus:outline-none focus:ring-2 focus:ring-secondary" />
        <select v-model="browseGrade"
                class="w-28 px-3 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600
                       bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                       focus:outline-none focus:ring-2 focus:ring-secondary">
          <option value="">{{ t('gradeLevel') }}</option>
          <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. {{ t('gradeShortSuffix') }}</option>
        </select>
      </div>

      <div v-if="browseLoading" class="flex justify-center py-10"><Spinner /></div>

      <div v-else-if="!browseResults.length" class="text-sm text-gray-400 text-center py-10">
        {{ t('taskSetsNoResults') }}
      </div>

      <div v-else class="space-y-2">
        <div v-for="task in browseResults" :key="task.task_id"
             class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/30"
               @click="toggleBrowsePreview(task)">
            <div class="flex-1 min-w-0">
              <div class="font-medium text-slate-800 dark:text-slate-100 text-sm truncate">{{ task.task_name }}</div>
              <div class="text-xs text-gray-400 mt-0.5">
                {{ task.example_count ?? 0 }} {{ t('examplesCount') }}
                <span v-if="task.grade_levels?.length"> · {{ task.grade_levels.join(', ') }}. {{ t('gradeShortSuffix') }}</span>
              </div>
            </div>
            <button @click.stop="copyFromBrowse(task)" :disabled="browseCopyingId === task.task_id"
                    class="flex-shrink-0 text-xs px-3 py-1.5 bg-secondary text-white rounded-lg
                           hover:bg-blue-600 transition-colors disabled:opacity-50 font-medium">
              {{ browseCopyingId === task.task_id ? '...' : t('createCopy') }}
            </button>
          </div>

          <div v-if="expandedBrowseId === task.task_id"
               class="border-t border-slate-100 dark:border-slate-700 px-4 py-3 bg-slate-50 dark:bg-slate-900/40">
            <div v-if="browsePreviewLoading[task.task_id]" class="flex justify-center py-3"><Spinner /></div>
            <div v-else-if="!browsePreview[task.task_id]?.length" class="text-xs text-gray-400 text-center py-2">
              {{ t('noExamples') }}
            </div>
            <div v-else class="flex flex-wrap gap-2">
              <span v-for="ex in browsePreview[task.task_id]" :key="ex.id"
                    class="px-2.5 py-1 bg-white dark:bg-slate-800 border border-slate-200
                           dark:border-slate-700 rounded-lg text-xs font-mono text-slate-700 dark:text-slate-300">
                {{ ex.example }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <button @click="mode = null"
              class="px-4 py-2.5 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 text-sm">
        {{ t('back') }}
      </button>
    </div>

    <!-- ── AI generation form ────────────────────────────────────────────────── -->
    <div v-else-if="mode === 'ai-form'" class="space-y-5">

      <!-- Mix toggle -->
      <div class="flex items-center gap-3 p-4 rounded-2xl bg-white dark:bg-slate-800
                  border-2 border-slate-200 dark:border-slate-700">
        <button @click="isMix = false"
                :class="['flex-1 py-2 rounded-xl text-sm font-semibold transition-all',
                         !isMix ? 'bg-primary text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-slate-100 dark:hover:bg-slate-700']">
          {{ t('singleType') }}
        </button>
        <button @click="isMix = true"
                :class="['flex-1 py-2 rounded-xl text-sm font-semibold transition-all',
                         isMix ? 'bg-primary text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-slate-100 dark:hover:bg-slate-700']">
          {{ t('mixOrTest') }}
        </button>
      </div>

      <!-- Single type -->
      <template v-if="!isMix">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">{{ t('exampleType') }}</label>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <button v-for="opt in AI_TYPES" :key="opt.value"
                    @click="aiType = opt.value"
                    :class="[
                      'py-2.5 px-3 rounded-xl text-sm font-medium border-2 transition-all',
                      aiType === opt.value
                        ? 'border-secondary bg-secondary/10 dark:bg-secondary/20 text-secondary'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                    ]">
              <span class="mr-1">{{ opt.icon }}</span> {{ opt.label }}
            </button>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            {{ t('numberOfExamples') }} <span class="text-secondary font-bold ml-1">{{ aiCount }}</span>
          </label>
          <input type="range" v-model.number="aiCount" min="3" max="30" step="1"
                 class="w-full accent-secondary" />
          <div class="flex justify-between text-xs text-gray-400 mt-0.5"><span>3</span><span>30</span></div>
        </div>
      </template>

      <!-- Mix segments -->
      <template v-else>
        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="text-sm font-medium text-slate-700 dark:text-slate-300">
              {{ t('exampleTypes') }}
              <span class="ml-2 text-xs text-gray-400">{{ t('totalCount') }} {{ mixTotal }} {{ t('examplesCount') }}</span>
            </label>
            <button @click="addMixSegment"
                    class="text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary
                           rounded-lg hover:bg-secondary/20 font-medium">
              {{ t('addTypeButton') }}
            </button>
          </div>
          <div class="space-y-2">
            <div v-for="(seg, i) in mixSegments" :key="i"
                 class="flex items-center gap-2 p-3 bg-white dark:bg-slate-800 rounded-xl
                        border border-slate-200 dark:border-slate-700">
              <select v-model="seg.type"
                      class="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                             bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-sm
                             focus:outline-none focus:ring-1 focus:ring-secondary">
                <option v-for="opt in AI_TYPES" :key="opt.value" :value="opt.value">
                  {{ opt.icon }} {{ opt.label }}
                </option>
              </select>
              <div class="flex items-center gap-1.5 flex-shrink-0">
                <button @click="seg.count = Math.max(1, seg.count - 1)"
                        class="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300
                               hover:bg-slate-200 font-bold text-sm flex items-center justify-center">−</button>
                <span class="w-8 text-center font-bold text-slate-800 dark:text-slate-100 text-sm">{{ seg.count }}</span>
                <button @click="seg.count = Math.min(30, seg.count + 1)"
                        class="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300
                               hover:bg-slate-200 font-bold text-sm flex items-center justify-center">+</button>
              </div>
              <button v-if="mixSegments.length > 1" @click="removeMixSegment(i)"
                      class="text-red-400 hover:text-red-600 text-xl leading-none flex-shrink-0">×</button>
            </div>
          </div>
        </div>
      </template>

      <!-- Description -->
      <div>
        <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
          {{ isMix ? t('topicContextLabel') : t('exampleDescriptionLabel') }}
        </label>
        <textarea v-model="aiDescription" rows="3"
                  :placeholder="isMix ? t('mixDescriptionPlaceholder') : t('aiDescriptionPlaceholder')"
                  class="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600
                         bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                         focus:outline-none focus:ring-2 focus:ring-secondary resize-none text-sm" />
        <p v-if="aiError" class="text-red-500 text-sm mt-1">{{ aiError }}</p>
      </div>

      <div class="flex gap-3">
        <button @click="mode = null"
                class="px-4 py-2.5 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 text-sm">
          {{ t('back') }}
        </button>
        <button @click="generate" :disabled="aiGenerating"
                class="flex-1 py-3 bg-secondary text-white rounded-2xl font-bold
                       border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5
                       active:border-b-2 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
          <Spinner v-if="aiGenerating" class="w-4 h-4" />
          <TeacherIcon v-else name="sparkle" :size="13" />
          <span>{{ aiGenerating ? t('generatingLabel') : t('generateLabel') }}</span>
        </button>
      </div>
    </div>

    <!-- ── Preview / edit (manual or after AI) ─────────────────────────────── -->
    <div v-else-if="hasPreview || mode === 'manual'" class="space-y-5">

      <!-- Task name + grade -->
      <div class="flex gap-3">
        <div class="flex-1">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{{ t('taskSetName') }}</label>
          <input v-model="taskName" type="text" :placeholder="t('taskNamePlaceholderExample')"
                 class="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600
                        bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                        focus:outline-none focus:ring-2 focus:ring-secondary" />
        </div>
        <div class="w-28">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{{ t('gradeLevel') }}</label>
          <select v-model="taskGrade"
                  class="w-full px-3 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600
                         bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                         focus:outline-none focus:ring-2 focus:ring-secondary">
            <option value="">—</option>
            <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. {{ t('gradeShortSuffix') }}</option>
          </select>
        </div>
      </div>

      <!-- Examples list -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <label class="text-sm font-medium text-slate-700 dark:text-slate-300">
            {{ t('examples') }} ({{ examples.length }})
          </label>
          <button @click="addExample"
                  class="text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary
                         rounded-lg hover:bg-secondary/20 font-medium">
            {{ t('addButton') }}
          </button>
        </div>

        <div class="space-y-3">
          <div v-for="(ex, i) in examples" :key="i"
               class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-3">
            <div class="flex gap-2 items-start">
              <span class="text-xs text-gray-400 mt-2.5 w-5 text-right flex-shrink-0">{{ i + 1 }}</span>

              <!-- Example input -->
              <div class="flex-1 min-w-0">
                <textarea v-if="ex.input_type === 'WORD'" v-model="ex.example" rows="2"
                          :placeholder="t('wordProblemPlaceholder')"
                          class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                                 bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                                 focus:outline-none focus:ring-1 focus:ring-secondary resize-none" />
                <input v-else v-model="ex.example" type="text" :placeholder="t('examplePlaceholderLatex')"
                       class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                              bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                              font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
                <!-- LaTeX preview -->
                <div v-if="ex.input_type !== 'WORD' && ex.example.trim()"
                     class="mt-1.5 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-900
                            border border-slate-100 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-300">
                  <span class="text-xs text-gray-400 mr-2">{{ t('previewLabel') }}</span>\({{ ex.example }}\)
                </div>
              </div>

              <!-- Type + answer + delete -->
              <select v-model="ex.input_type"
                      class="w-24 px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                             bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-xs
                             focus:outline-none focus:ring-1 focus:ring-secondary flex-shrink-0">
                <option value="INLINE">INLINE</option>
                <option value="FRAC">FRAC</option>
                <option value="WORD">WORD</option>
                <option value="VAR">VAR</option>
              </select>
              <div class="flex-shrink-0 w-28">
                <input v-model="ex.answer" type="text" :placeholder="t('answerPlaceholder')"
                       class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                              bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                              font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
                <!-- Answer LaTeX preview -->
                <div v-if="ex.input_type !== 'WORD' && ex.answer.trim()"
                     class="mt-1 text-xs text-center text-slate-500 dark:text-slate-400">
                  \({{ ex.answer }}\)
                </div>
              </div>
              <button @click="removeExample(i)"
                      class="text-red-400 hover:text-red-600 mt-2 flex-shrink-0 text-xl leading-none">×</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-3 pt-2">
        <button @click="mode = null; examples = []"
                class="px-4 py-2.5 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 text-sm">
          {{ t('discard') }}
        </button>
        <button v-if="mode === 'ai'" @click="mode = 'ai-form'"
                class="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600
                       text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 text-sm">
          {{ t('regenerate') }}
        </button>
        <button @click="save" :disabled="saving"
                class="flex-1 py-2.5 bg-secondary text-white rounded-2xl font-bold
                       border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5
                       active:border-b-2 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
          <Spinner v-if="saving" class="w-4 h-4" />
          <span>{{ saving ? t('saving') : t('saveAndAssign') }}</span>
        </button>
      </div>
    </div>

  </div>
</template>
