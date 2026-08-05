<script setup>
import { ref, nextTick, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/useAuthStore';
import { teacherGenerateMoreExamplesPreview, teacherSaveGeneratedExamples } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import TeacherIcon from '@/components/TeacherIcon.vue';

const props = defineProps({ taskId: [String, Number] });
const emit = defineEmits(['close', 'success']);

const authStore = useAuthStore();
const { t } = useI18n();

const description = ref('');
const count = ref(10);
const generating = ref(false);
const saving = ref(false);
const error = ref('');
const examples = ref([]); // null until first generation; [] means preview step not reached yet

const generate = async () => {
  error.value = '';
  if (!description.value.trim()) {
    error.value = t('descriptionRequired');
    return;
  }
  generating.value = true;
  try {
    const data = await teacherGenerateMoreExamplesPreview(authStore.id, props.taskId, description.value, count.value);
    examples.value = (data.examples || []).map(e => ({
      example: e.example, input_type: e.input_type, answer: e.answer,
    }));
  } catch (e) {
    error.value = e?.response?.data?.error || t('errorGenerating');
  }
  generating.value = false;
};

const removeExample = (i) => examples.value.splice(i, 1);

watch(examples, async () => {
  await nextTick();
  window.MathJax?.typeset();
}, { deep: true });

const save = async () => {
  const validExamples = examples.value.filter(e => e.example.trim() && e.answer.trim());
  if (!validExamples.length) return;
  saving.value = true;
  try {
    const result = await teacherSaveGeneratedExamples(authStore.id, props.taskId, validExamples, description.value);
    emit('success', result.created || []);
  } catch (e) {
    error.value = e?.response?.data?.error || t('errorSaving');
  }
  saving.value = false;
};
</script>

<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="emit('close')">
    <div class="bg-white dark:bg-slate-800 rounded-2xl p-5 w-full max-w-lg max-h-[85vh] overflow-y-auto shadow-xl">

      <div class="flex items-center gap-2 mb-4">
        <div class="w-9 h-9 rounded-full bg-secondary/10 text-secondary flex items-center justify-center flex-shrink-0">
          <TeacherIcon name="sparkle" :size="16" />
        </div>
        <h3 class="text-lg font-bold text-slate-800 dark:text-slate-100">{{ t('generateMoreWithAi') }}</h3>
      </div>

      <!-- Form step -->
      <div v-if="!examples.length" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            {{ t('numberOfNewExamples') }} <span class="text-secondary font-bold ml-1">{{ count }}</span>
          </label>
          <input type="range" v-model.number="count" min="3" max="30" step="1" class="w-full accent-secondary" />
          <div class="flex justify-between text-xs text-gray-400 mt-0.5"><span>3</span><span>30</span></div>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{{ t('additionalRequest') }}</label>
          <textarea v-model="description" rows="3"
                    :placeholder="t('moreExamplesPlaceholder')"
                    class="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600
                           bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                           focus:outline-none focus:ring-2 focus:ring-secondary resize-none text-sm" />
          <p v-if="error" class="text-red-500 text-sm mt-1">{{ error }}</p>
        </div>

        <div class="flex gap-3">
          <button @click="emit('close')"
                  class="px-4 py-2.5 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 text-sm">
            {{ t('cancel') }}
          </button>
          <button @click="generate" :disabled="generating"
                  class="flex-1 py-2.5 bg-secondary text-white rounded-2xl font-bold
                         border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5
                         active:border-b-2 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
            <Spinner v-if="generating" class="w-4 h-4" />
            <TeacherIcon v-else name="sparkle" :size="13" />
            <span>{{ generating ? t('generatingEllipsis') : t('generate') }}</span>
          </button>
        </div>
      </div>

      <!-- Preview / edit step -->
      <div v-else class="space-y-4">
        <div class="space-y-3">
          <div v-for="(ex, i) in examples" :key="i"
               class="bg-slate-50 dark:bg-slate-900/40 rounded-xl border border-slate-200 dark:border-slate-700 p-3">
            <div class="flex gap-2 items-start">
              <span class="text-xs text-gray-400 mt-2.5 w-5 text-right flex-shrink-0">{{ i + 1 }}</span>
              <div class="flex-1 min-w-0">
                <textarea v-if="ex.input_type === 'WORD'" v-model="ex.example" rows="2"
                          class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                                 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                                 focus:outline-none focus:ring-1 focus:ring-secondary resize-none" />
                <input v-else v-model="ex.example" type="text"
                       class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                              bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                              font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
              </div>
              <select v-model="ex.input_type"
                      class="w-24 px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                             bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                             focus:outline-none focus:ring-1 focus:ring-secondary flex-shrink-0">
                <option value="INLINE">INLINE</option>
                <option value="FRAC">FRAC</option>
                <option value="WORD">WORD</option>
                <option value="VAR">VAR</option>
              </select>
              <input v-model="ex.answer" type="text" :placeholder="t('answerPlaceholder')"
                     class="w-28 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                            bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                            font-mono focus:outline-none focus:ring-1 focus:ring-secondary flex-shrink-0" />
              <button @click="removeExample(i)" class="text-red-400 hover:text-red-600 mt-2 flex-shrink-0 text-xl leading-none">×</button>
            </div>
          </div>
        </div>

        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>

        <div class="flex gap-3 pt-1">
          <button @click="examples = []"
                  class="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600
                         text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 text-sm">
            {{ t('regenerate') }}
          </button>
          <button @click="save" :disabled="saving"
                  class="flex-1 py-2.5 bg-secondary text-white rounded-2xl font-bold
                         border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5
                         active:border-b-2 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
            <Spinner v-if="saving" class="w-4 h-4" />
            <span>{{ saving ? t('addingEllipsis') : t('addToSet') }}</span>
          </button>
        </div>
      </div>

    </div>
  </div>
</template>
