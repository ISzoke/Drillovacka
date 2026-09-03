<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { browseTasks, getTaskExamples, parentPrintTest } from '@/api/apiClient';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';

const { t } = useI18n();
const toastStore = useToastStore();

const grade = ref(3);
const tasks = ref([]);
const tasksLoading = ref(false);
const selectedTaskId = ref(null);
const examples = ref([]);
const examplesLoading = ref(false);

const title = ref('');
const childName = ref('');
const count = ref(10);
const columns = ref(1);
const mirror = ref(true);
const withAnswers = ref(true);

const generating = ref(false);
const shuffledPool = ref([]);

const grades = [1, 2, 3, 4, 5, 6, 7, 8, 9];

const maxCount = computed(() => Math.min(20, examples.value.length || 20));

const shuffle = () => {
  const pool = [...examples.value];
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  shuffledPool.value = pool;
};

const loadTasks = async () => {
  tasksLoading.value = true;
  selectedTaskId.value = null;
  examples.value = [];
  try {
    tasks.value = await browseTasks(grade.value);
  } catch (e) {
    tasks.value = [];
  }
  tasksLoading.value = false;
};

const loadExamples = async () => {
  if (!selectedTaskId.value) return;
  examplesLoading.value = true;
  try {
    examples.value = await getTaskExamples(selectedTaskId.value) || [];
    const tk = tasks.value.find(x => x.task_id === selectedTaskId.value);
    if (tk && !title.value.trim()) title.value = tk.task_name;
    count.value = Math.min(10, examples.value.length || 10);
    shuffle();
  } catch (e) {
    examples.value = [];
    shuffledPool.value = [];
  }
  examplesLoading.value = false;
};

watch(grade, loadTasks, { immediate: true });
watch(selectedTaskId, loadExamples);

const buildPayload = () => ({
  title: title.value.trim() || t('parentPrintDefaultTitle'),
  student_name: childName.value.trim(),
  mirror: mirror.value,
  show_answer_page: withAnswers.value,
  columns: columns.value,
  items: shuffledPool.value.slice(0, count.value).map(e => ({ example_id: e.id })),
});

// ── Live inline preview — the real WeasyPrint-rendered PDF, byte-for-byte the
// same as the download, refreshed automatically as the settings change.
const previewUrl = ref('');
const previewLoading = ref(false);
let previewObjectUrl = null;
let previewSeq = 0;
let previewDebounce = null;

const revokePreviewUrl = () => {
  if (previewObjectUrl) { URL.revokeObjectURL(previewObjectUrl); previewObjectUrl = null; }
};

const loadPreview = async () => {
  if (!shuffledPool.value.length) {
    revokePreviewUrl();
    previewUrl.value = '';
    return;
  }
  const reqId = ++previewSeq;
  previewLoading.value = true;
  try {
    const blob = await parentPrintTest(buildPayload());
    if (reqId !== previewSeq) return;
    const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
    revokePreviewUrl();
    previewObjectUrl = url;
    previewUrl.value = url;
  } catch (e) {
    // keep the last good preview on failure
  }
  if (reqId === previewSeq) previewLoading.value = false;
};

watch([shuffledPool, count, columns, mirror, withAnswers, title, childName], () => {
  clearTimeout(previewDebounce);
  previewDebounce = setTimeout(loadPreview, 600);
});

const reshuffle = () => { shuffle(); };

const run = async (mode) => {
  if (!examples.value.length) {
    toastStore.addToast({ message: t('parentPrintPickTask'), type: 'error', visible: true });
    return;
  }
  generating.value = true;
  try {
    const blob = await parentPrintTest(buildPayload());
    const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
    if (mode === 'tab') {
      window.open(url, '_blank');
    } else {
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(title.value || 'precvicovanie').replace(/[^\wÀ-ž\- ]/g, '').trim() || 'precvicovanie'}.pdf`;
      a.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (e) {
    toastStore.addToast({ message: t('parentPrintError'), type: 'error', visible: true });
  }
  generating.value = false;
};

onBeforeUnmount(() => { clearTimeout(previewDebounce); revokePreviewUrl(); });
</script>

<template>
  <div class="pt-24 px-4 max-w-5xl mx-auto pb-16">
    <h1 class="text-3xl font-bold text-primary dark:text-white mb-1">{{ t('parentPrintTitle') }}</h1>
    <p class="text-gray-500 dark:text-gray-400 mb-8 max-w-2xl">{{ t('parentPrintIntro') }}</p>

    <div class="grid gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <!-- Settings -->
      <div class="space-y-5 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 h-fit">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{{ t('gradeLevel') }}</label>
          <div class="flex flex-wrap gap-1.5">
            <button v-for="g in grades" :key="g" @click="grade = g"
                    :class="['w-9 h-9 rounded-lg text-sm font-semibold transition-colors',
                             grade === g ? 'bg-secondary text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200']">
              {{ g }}.
            </button>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{{ t('parentPrintTaskLabel') }}</label>
          <div v-if="tasksLoading" class="py-2"><Spinner /></div>
          <select v-else v-model="selectedTaskId"
                  class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                         bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                         focus:outline-none focus:ring-2 focus:ring-secondary">
            <option :value="null" disabled>{{ t('parentPrintTaskPlaceholder') }}</option>
            <option v-for="tk in tasks" :key="tk.task_id" :value="tk.task_id">
              {{ tk.task_name }} ({{ tk.example_count }})
            </option>
          </select>
          <p v-if="!tasksLoading && !tasks.length" class="text-xs text-gray-400 mt-1">{{ t('parentPrintNoTasks') }}</p>
        </div>

        <div v-if="examplesLoading" class="py-2"><Spinner /></div>

        <template v-if="examples.length">
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {{ t('parentPrintCount') }}: <span class="font-bold">{{ count }}</span>
            </label>
            <input type="range" min="4" :max="maxCount" v-model.number="count" class="w-full accent-secondary" />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{{ t('parentPrintColumns') }}</label>
            <div class="flex gap-1.5">
              <button v-for="c in [1, 2]" :key="c" @click="columns = c"
                      :class="['px-4 py-1.5 rounded-lg text-sm font-semibold transition-colors',
                               columns === c ? 'bg-secondary text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200']">
                {{ c }}
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{{ t('parentPrintSheetTitle') }}</label>
            <input v-model="title" type="text"
                   class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                          bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                          focus:outline-none focus:ring-2 focus:ring-secondary" />
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{{ t('parentPrintChildName') }}</label>
            <input v-model="childName" type="text" :placeholder="t('parentPrintChildNamePlaceholder')"
                   class="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600
                          bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                          focus:outline-none focus:ring-2 focus:ring-secondary" />
          </div>

          <label class="flex items-start gap-2 cursor-pointer">
            <input type="checkbox" v-model="withAnswers" class="mt-1 accent-secondary" />
            <span class="text-sm text-slate-700 dark:text-slate-300">{{ t('parentPrintWithAnswers') }}</span>
          </label>

          <label class="flex items-start gap-2 cursor-pointer" :class="{ 'opacity-40 pointer-events-none': !withAnswers }">
            <input type="checkbox" v-model="mirror" class="mt-1 accent-secondary" />
            <span class="text-sm text-slate-700 dark:text-slate-300">
              {{ t('parentPrintMirror') }}
              <span class="block text-xs text-gray-400">{{ t('parentPrintMirrorHint') }}</span>
            </span>
          </label>

          <div class="flex flex-wrap gap-2 pt-2">
            <button @click="reshuffle" type="button"
                    class="px-3 py-2 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-sm font-semibold hover:bg-slate-200">
              🔀 {{ t('parentPrintShuffle') }}
            </button>
            <button @click="run('tab')" :disabled="generating"
                    class="px-4 py-2 rounded-lg bg-secondary text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-50">
              {{ t('parentPrintOpen') }}
            </button>
            <button @click="run('download')" :disabled="generating"
                    class="px-4 py-2 rounded-lg border border-secondary text-secondary text-sm font-semibold hover:bg-secondary/10 disabled:opacity-50">
              {{ generating ? t('downloadingEllipsis') : t('parentPrintDownload') }}
            </button>
          </div>
        </template>
      </div>

      <!-- Live preview -->
      <div class="relative min-h-[400px] md:sticky md:top-24 h-fit bg-slate-100 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 flex items-center justify-center overflow-hidden">
        <iframe v-if="previewUrl" :src="previewUrl" class="w-full h-[75vh] bg-white" :title="t('parentPrintPreview')"></iframe>
        <p v-else-if="!previewLoading" class="text-sm text-gray-400 text-center px-6">{{ t('parentPrintPreviewEmpty') }}</p>
        <div v-if="previewLoading"
             class="absolute top-2 right-2 flex items-center gap-1.5 text-xs text-slate-500 bg-white/80 dark:bg-slate-800/80 px-2 py-1 rounded-full">
          <span class="w-3 h-3 border-2 border-slate-300 border-t-secondary rounded-full animate-spin"></span>
          {{ t('parentPrintUpdating') }}
        </div>
        <div v-if="previewLoading && !previewUrl" class="flex flex-col items-center gap-3 text-gray-400">
          <Spinner /><span class="text-sm">{{ t('parentPrintUpdating') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
