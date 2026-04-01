<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import { useRouter } from 'vue-router';
import { teacherGenerateTaskPreview, teacherSaveTask, assignTaskToClassroom } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({ classroomId: [String, Number] });

const authStore = useAuthStore();
const toastStore = useToastStore();
const router = useRouter();

const mode = ref(null); // null | 'manual' | 'ai-form' | 'ai'

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

const AI_TYPES = [
  { value: 'arithmetic', label: 'Aritmetika', icon: '±', inputType: 'INLINE' },
  { value: 'fractions',  label: 'Zlomky',     icon: '½', inputType: 'FRAC'   },
  { value: 'word',       label: 'Slovná úloha', icon: '📖', inputType: 'WORD' },
  { value: 'algebra',    label: 'Algebra',    icon: 'x', inputType: 'VAR'    },
];

const selectedType = computed(() => AI_TYPES.find(t => t.value === aiType.value));
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
    aiError.value = 'Popis je povinný.';
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
    aiError.value = e?.response?.data?.error || 'Chyba pri generovaní.';
  }
  aiGenerating.value = false;
};

const save = async () => {
  const validExamples = examples.value.filter(e => e.example.trim() && e.answer.trim());
  if (!taskName.value.trim()) {
    toastStore.addToast({ message: 'Zadaj názov sady.', type: 'error', visible: true });
    return;
  }
  if (!validExamples.length) {
    toastStore.addToast({ message: 'Pridaj aspoň jeden príklad.', type: 'error', visible: true });
    return;
  }
  saving.value = true;
  try {
    const hasWord = validExamples.some(e => e.input_type === 'WORD');
    const allWord = validExamples.every(e => e.input_type === 'WORD');
    const form = allWord ? 'word-problem' : 'classic';
    const result = await teacherSaveTask(
      authStore.id, taskName.value, form, taskGrade.value || null, validExamples,
    );
    if (props.classroomId) {
      await assignTaskToClassroom(props.classroomId, authStore.id, result.task_id, false, null);
    }
    toastStore.addToast({ message: 'Sada vytvorená a priradená!', type: 'success', visible: true });
    router.push({ name: 'teacher-task-sets', params: { classroomId: props.classroomId } });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri ukladaní.', type: 'error', visible: true });
  }
  saving.value = false;
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

    <h1 class="text-2xl font-bold text-primary dark:text-white mb-6">Vytvoriť novú sadu</h1>

    <!-- ── Mode selection ────────────────────────────────────────────────────── -->
    <div v-if="!hasPreview && mode === null" class="grid sm:grid-cols-2 gap-4">
      <button @click="startManual"
              class="p-6 bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700
                     border-b-[6px] border-b-slate-300 dark:border-b-slate-600
                     hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all text-left">
        <div class="text-3xl mb-3">✏️</div>
        <div class="font-bold text-primary dark:text-white text-lg">Manuálne zadať</div>
        <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Zadaj príklady a odpovede ručne.</div>
      </button>

      <button @click="mode = 'ai-form'"
              class="p-6 bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700
                     border-b-[6px] border-b-slate-300 dark:border-b-slate-600
                     hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all text-left">
        <div class="text-3xl mb-3">🤖</div>
        <div class="font-bold text-primary dark:text-white text-lg">Generovať pomocou AI</div>
        <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Opíš čo chceš a Gemini vygeneruje príklady.</div>
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
          Jeden typ
        </button>
        <button @click="isMix = true"
                :class="['flex-1 py-2 rounded-xl text-sm font-semibold transition-all',
                         isMix ? 'bg-primary text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-slate-100 dark:hover:bg-slate-700']">
          🎲 Mix / Písomka
        </button>
      </div>

      <!-- Single type -->
      <template v-if="!isMix">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Typ príkladov</label>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <button v-for="t in AI_TYPES" :key="t.value"
                    @click="aiType = t.value"
                    :class="[
                      'py-2.5 px-3 rounded-xl text-sm font-medium border-2 transition-all',
                      aiType === t.value
                        ? 'border-secondary bg-secondary/10 dark:bg-secondary/20 text-secondary'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                    ]">
              <span class="mr-1">{{ t.icon }}</span> {{ t.label }}
            </button>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Počet príkladov <span class="text-secondary font-bold ml-1">{{ aiCount }}</span>
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
              Typy príkladov
              <span class="ml-2 text-xs text-gray-400">celkom: {{ mixTotal }} príkladov</span>
            </label>
            <button @click="addMixSegment"
                    class="text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary
                           rounded-lg hover:bg-secondary/20 font-medium">
              + Pridať typ
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
                <option v-for="t in AI_TYPES" :key="t.value" :value="t.value">
                  {{ t.icon }} {{ t.label }}
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
          {{ isMix ? 'Téma / kontext písomky' : 'Popis príkladov' }}
        </label>
        <textarea v-model="aiDescription" rows="3"
                  :placeholder="isMix
                    ? 'Napr: 5. ročník, precvičiť zlomky a slovné úlohy z geometrie...'
                    : 'Napr: násobilka 7, príklady so zvyškom, rovnice s dvoma premennými...'"
                  class="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600
                         bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                         focus:outline-none focus:ring-2 focus:ring-secondary resize-none text-sm" />
        <p v-if="aiError" class="text-red-500 text-sm mt-1">{{ aiError }}</p>
      </div>

      <div class="flex gap-3">
        <button @click="mode = null"
                class="px-4 py-2.5 rounded-xl text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 text-sm">
          Späť
        </button>
        <button @click="generate" :disabled="aiGenerating"
                class="flex-1 py-3 bg-secondary text-white rounded-2xl font-bold
                       border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5
                       active:border-b-2 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
          <Spinner v-if="aiGenerating" class="w-4 h-4" />
          <span>{{ aiGenerating ? 'Generujem...' : '🤖 Generovať' }}</span>
        </button>
      </div>
    </div>

    <!-- ── Preview / edit (manual or after AI) ─────────────────────────────── -->
    <div v-else-if="hasPreview || mode === 'manual'" class="space-y-5">

      <!-- Task name + grade -->
      <div class="flex gap-3">
        <div class="flex-1">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Názov sady</label>
          <input v-model="taskName" type="text" placeholder="Napr: Násobilka 7"
                 class="w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600
                        bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                        focus:outline-none focus:ring-2 focus:ring-secondary" />
        </div>
        <div class="w-28">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Ročník</label>
          <select v-model="taskGrade"
                  class="w-full px-3 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600
                         bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                         focus:outline-none focus:ring-2 focus:ring-secondary">
            <option value="">—</option>
            <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. roč.</option>
          </select>
        </div>
      </div>

      <!-- Examples list -->
      <div>
        <div class="flex items-center justify-between mb-3">
          <label class="text-sm font-medium text-slate-700 dark:text-slate-300">
            Príklady ({{ examples.length }})
          </label>
          <button @click="addExample"
                  class="text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary
                         rounded-lg hover:bg-secondary/20 font-medium">
            + Pridať
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
                          placeholder="Slovná úloha..."
                          class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                                 bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                                 focus:outline-none focus:ring-1 focus:ring-secondary resize-none" />
                <input v-else v-model="ex.example" type="text" placeholder="Príklad napr. \frac{1}{2} + \frac{1}{3}"
                       class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                              bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                              font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
                <!-- LaTeX preview -->
                <div v-if="ex.input_type !== 'WORD' && ex.example.trim()"
                     class="mt-1.5 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-900
                            border border-slate-100 dark:border-slate-700 text-sm text-slate-700 dark:text-slate-300">
                  <span class="text-xs text-gray-400 mr-2">náhľad:</span>\({{ ex.example }}\)
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
                <input v-model="ex.answer" type="text" placeholder="Odpoveď"
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
          Zahodiť
        </button>
        <button v-if="mode === 'ai'" @click="mode = 'ai-form'"
                class="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600
                       text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 text-sm">
          Regenerovať
        </button>
        <button @click="save" :disabled="saving"
                class="flex-1 py-2.5 bg-secondary text-white rounded-2xl font-bold
                       border-b-4 border-blue-700 hover:-translate-y-0.5 active:translate-y-0.5
                       active:border-b-2 transition-all disabled:opacity-50 flex items-center justify-center gap-2">
          <Spinner v-if="saving" class="w-4 h-4" />
          <span>{{ saving ? 'Ukladám...' : 'Uložiť a priradiť' }}</span>
        </button>
      </div>
    </div>

  </div>
</template>
