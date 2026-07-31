<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import {
  getMyTeacherTasks, teacherListExamples, getTeacherTaskExamples, teacherPrintTest,
  teacherGenerateTaskPreview,
} from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import TeacherIcon from '@/components/TeacherIcon.vue';
import TeacherPageHeader from '@/components/TeacherPageHeader.vue';
import ToggleSwitch from '@/components/ToggleSwitch.vue';

const route = useRoute();
const authStore = useAuthStore();
const toastStore = useToastStore();

const RECOMMENDED_SPACING = 24;

const loading = ref(true);
const myTasks = ref([]);
const taskSearch = ref('');
const addedTaskIds = ref(new Set());
const addingTaskId = ref(null);
const unattached = ref([]);
const unattachedOpen = ref(false);

// items = [{ key, id|null, example, answer, points, dot }] in print order
const items = ref([]);
let itemKey = 0;

const settings = ref({
  title: 'Písomná práca',
  class_name: '',
  note: '',
  groups: 1,
  per_page: 1,
  show_points: true,
  answer_key: true,
  cover_page: false,
  show_header: true,
  header_text: '',
  spacing: RECOMMENDED_SPACING,
  columns: 2,
  default_answer_lines: 4,
});

// answer_lines per item: null = auto (podľa typu), 0 = kompaktné (bez riadkov), 1-6 = počet riadkov
const ANSWER_LINES_OPTIONS = [
  { value: null, label: 'Auto (podľa typu)' },
  { value: 0, label: 'Kompaktné (=___)' },
  { value: 1, label: '1 riadok' },
  { value: 2, label: '2 riadky' },
  { value: 3, label: '3 riadky' },
  { value: 4, label: '4 riadky' },
  { value: 5, label: '5 riadkov' },
  { value: 6, label: '6 riadkov' },
];

const generating = ref(false);

// ── Generator (Vytvoriť príklady) — same flow as "Vytvoriť novú sadu" ────────
const genOpen = ref(false);
const genType = ref('arithmetic');
const genCount = ref(10);
const genDescription = ref('');
const genRunning = ref(false);
const genError = ref('');
const isMix = ref(false);
const mixSegments = ref([
  { type: 'arithmetic', count: 10 },
  { type: 'fractions', count: 10 },
]);

const AI_TYPES = [
  { value: 'arithmetic', label: 'Aritmetika', icon: '±' },
  { value: 'fractions', label: 'Zlomky', icon: '½' },
  { value: 'word', label: 'Slovná úloha', icon: '📖' },
  { value: 'algebra', label: 'Algebra', icon: 'x' },
];

const mixTotal = computed(() => mixSegments.value.reduce((s, seg) => s + Number(seg.count), 0));
const genTotal = computed(() => (isMix.value ? mixTotal.value : genCount.value));

const addMixSegment = () => { mixSegments.value.push({ type: 'arithmetic', count: 5 }); };
const removeMixSegment = (i) => {
  if (mixSegments.value.length > 1) mixSegments.value.splice(i, 1);
};

// ── Palette for source dots (per sada) ───────────────────────────────────────
const DOTS = ['bg-blue-500', 'bg-amber-500', 'bg-purple-500', 'bg-green-500', 'bg-rose-500'];
const PILLS = [
  'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-500/10 dark:text-blue-300 dark:border-blue-500/30',
  'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/30',
  'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-500/10 dark:text-purple-300 dark:border-purple-500/30',
  'bg-green-50 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-300 dark:border-green-500/30',
  'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-300 dark:border-rose-500/30',
];
const taskColorIdx = (taskId) => Math.abs(Number(taskId) || 0) % DOTS.length;

const totalPoints = computed(() =>
  items.value.reduce((sum, it) => sum + (Number(it.points) || 0), 0)
);

const filteredTasks = computed(() => {
  const q = taskSearch.value.trim().toLowerCase();
  if (!q) return myTasks.value;
  return myTasks.value.filter(t => t.name.toLowerCase().includes(q));
});

// Rough page estimate: mirrors the backend's row/type/column model closely
// enough for a "~N strán" label — exact pagination stays server-authoritative.
const estimatedPages = computed(() => {
  const n = items.value.length;
  if (!n) return 0;
  const spacingFactor = settings.value.spacing / RECOMMENDED_SPACING;
  const compact = settings.value.per_page === 2;
  const rowH = (compact ? 9 : 13) * spacingFactor;
  const lineH = (compact ? 5 : 6) * spacingFactor;
  const headerH = (compact ? 5 : 6) * spacingFactor;

  let heightMm = 0;
  let compactCount = 0;
  const flushCompact = () => {
    if (compactCount > 0) {
      heightMm += rowH * Math.ceil(compactCount / settings.value.columns);
      compactCount = 0;
    }
  };
  for (const it of items.value) {
    const isWide = it.answer_lines != null ? it.answer_lines > 0 : (it.input_type === 'WORD' || it.input_type === 'VAR');
    if (isWide) {
      flushCompact();
      const lines = it.answer_lines != null && it.answer_lines > 0 ? it.answer_lines : settings.value.default_answer_lines;
      heightMm += headerH + lines * lineH;
    } else {
      compactCount += 1;
    }
  }
  flushCompact();

  const avail = compact ? 135 : 250;
  const sheetPages = Math.max(1, Math.ceil((heightMm + 25) / avail));
  let pages = settings.value.groups * sheetPages;
  if (settings.value.per_page === 2) pages = Math.ceil(pages / 2);
  if (settings.value.cover_page) pages += 1;
  if (settings.value.answer_key) pages += 1;
  return pages;
});

watch(items, async () => {
  await nextTick();
  window.MathJax?.typeset();
}, { deep: false });

watch(unattachedOpen, async (open) => {
  if (open) {
    await nextTick();
    window.MathJax?.typeset();
  }
});

const toItem = (ex, dot = DOTS[0]) => ({
  key: `db-${ex.id}-${itemKey++}`,
  id: ex.id,
  example: ex.example,
  answer: ex.answer,
  input_type: ex.input_type || 'INLINE',
  answer_lines: null,
  points: 1,
  dot,
});

const itemIds = computed(() => new Set(items.value.filter(it => it.id).map(it => it.id)));

const addUnattachedExample = (ex) => {
  if (itemIds.value.has(ex.id)) return;
  items.value = [...items.value, toItem(ex, 'bg-slate-400')];
};

const addAllUnattached = () => {
  const fresh = unattached.value.filter(ex => !itemIds.value.has(ex.id));
  items.value = [...items.value, ...fresh.map(ex => toItem(ex, 'bg-slate-400'))];
};

const addTask = async (task) => {
  if (addedTaskIds.value.has(task.id) || addingTaskId.value) return;
  addingTaskId.value = task.id;
  try {
    const data = await getTeacherTaskExamples(task.id, authStore.id);
    const fresh = data.examples.filter(ex => !itemIds.value.has(ex.id));
    items.value = [...items.value, ...fresh.map(ex => toItem(ex, DOTS[taskColorIdx(task.id)]))];
    addedTaskIds.value = new Set([...addedTaskIds.value, task.id]);
    if (items.value.length && settings.value.title === 'Písomná práca') {
      settings.value.title = task.name;
    }
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri načítaní sady.', type: 'error', visible: true });
  }
  addingTaskId.value = null;
};

const loadFromIds = async (ids) => {
  try {
    const all = await teacherListExamples(authStore.id);
    const byId = new Map(all.map(e => [e.id, e]));
    items.value = ids.filter(id => byId.has(id)).map(id => toItem(byId.get(id)));
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri načítaní príkladov.', type: 'error', visible: true });
  }
};

onMounted(async () => {
  try {
    myTasks.value = await getMyTeacherTasks(authStore.id);
  } catch (e) {
    myTasks.value = [];
  }
  try {
    unattached.value = await teacherListExamples(authStore.id, { unattachedOnly: true });
  } catch (e) {
    unattached.value = [];
  }
  const ids = (route.query.ids || '').split(',').map(Number).filter(Boolean);
  const taskId = Number(route.query.taskId) || null;
  if (taskId) {
    const task = myTasks.value.find(t => t.id === taskId);
    if (task) {
      settings.value.title = task.name;
      await addTask(task);
    }
  } else if (ids.length) {
    await loadFromIds(ids);
  }
  loading.value = false;
});

const generateExamples = async () => {
  if (genRunning.value) return;
  genError.value = '';
  if (!genDescription.value.trim()) {
    genError.value = 'Popis je povinný.';
    return;
  }
  genRunning.value = true;
  try {
    let data;
    if (isMix.value) {
      data = await teacherGenerateTaskPreview(
        authStore.id, 'mix', null, genDescription.value,
        mixSegments.value.map(s => ({ type: s.type, count: Number(s.count) })),
      );
    } else {
      data = await teacherGenerateTaskPreview(
        authStore.id, genType.value, genCount.value, genDescription.value,
      );
    }
    const generated = (data.examples || []).map(e => ({
      key: `gen-${itemKey++}`,
      id: null,
      example: e.example,
      answer: e.answer,
      input_type: e.input_type || 'INLINE',
      answer_lines: null,
      points: 1,
      dot: 'bg-secondary',
    }));
    if (!generated.length) throw new Error('Generátor nevrátil žiadne príklady.');
    items.value = [...items.value, ...generated];
    genOpen.value = false;
    toastStore.addToast({ message: `Pridaných ${generated.length} vygenerovaných príkladov.`, type: 'success', visible: true });
  } catch (e) {
    genError.value = e?.response?.data?.error || e?.message || 'Chyba pri generovaní.';
  }
  genRunning.value = false;
};

// ── Drag & drop reorder ──────────────────────────────────────────────────────
const dragIdx = ref(null);

const onDragStart = (i, event) => {
  dragIdx.value = i;
  event.dataTransfer.effectAllowed = 'move';
};

const onDragEnter = (i) => {
  if (dragIdx.value === null || dragIdx.value === i) return;
  const arr = [...items.value];
  const [moved] = arr.splice(dragIdx.value, 1);
  arr.splice(i, 0, moved);
  items.value = arr;
  dragIdx.value = i;
};

const onDragEnd = () => { dragIdx.value = null; };

const removeItem = (i) => { items.value = items.value.filter((_, idx) => idx !== i); };

const clearItems = () => {
  items.value = [];
  addedTaskIds.value = new Set();
};

// ── PDF ──────────────────────────────────────────────────────────────────────
const buildPayload = () => ({
  title: settings.value.title,
  class_name: settings.value.class_name,
  note: settings.value.note,
  groups: settings.value.groups,
  per_page: settings.value.per_page,
  show_points: settings.value.show_points,
  answer_key: settings.value.answer_key,
  cover_page: settings.value.cover_page,
  show_header: settings.value.show_header,
  header_text: settings.value.header_text,
  spacing: settings.value.spacing,
  columns: settings.value.columns,
  default_answer_lines: settings.value.default_answer_lines,
  items: items.value.map(it => {
    const points = Number.isFinite(Number(it.points)) ? Number(it.points) : 1;
    const base = { points, input_type: it.input_type || 'INLINE', answer_lines: it.answer_lines };
    return it.id
      ? { example_id: it.id, ...base }
      : { example: it.example, answer: it.answer, ...base };
  }),
});

const generatePdf = async (openInTab) => {
  if (!items.value.length) {
    toastStore.addToast({ message: 'Písomka nemá žiadne príklady.', type: 'error', visible: true });
    return;
  }
  generating.value = true;
  try {
    const blob = await teacherPrintTest(authStore.id, buildPayload());
    const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
    if (openInTab) {
      window.open(url, '_blank');
    } else {
      const a = document.createElement('a');
      a.href = url;
      a.download = `${settings.value.title.replace(/[^\wÀ-ž\- ]/g, '').trim() || 'test'}.pdf`;
      a.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri generovaní PDF.', type: 'error', visible: true });
  }
  generating.value = false;
};
</script>

<template>
  <div class="pt-20 px-4 max-w-6xl mx-auto pb-16">

    <div class="flex items-start justify-between gap-3">
      <TeacherPageHeader
        title="Generovanie PDF"
        subtitle="Vyberte príklady a nakonfigurujte nastavenia tlače." />
      <button @click="generatePdf(true)" :disabled="generating || !items.length"
              class="flex-shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium
                     border border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200
                     bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-40">
        <TeacherIcon name="eye" :size="15" />
        Náhľad
      </button>
    </div>

    <div v-if="loading" class="flex justify-center py-16"><Spinner /></div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-[1fr,340px] gap-5 items-start">

      <!-- ════════ Left column ════════ -->
      <div class="space-y-4 min-w-0">

        <!-- Generator (collapsible) -->
        <div class="rounded-xl border overflow-hidden transition-colors bg-white dark:bg-slate-800"
             :class="genOpen ? 'border-secondary/40' : 'border-slate-200 dark:border-slate-700'">
          <button @click="genOpen = !genOpen"
                  class="w-full px-5 py-4 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors">
            <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors"
                 :class="genOpen ? 'bg-secondary text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-400'">
              <TeacherIcon name="sparkle" :size="16" />
            </div>
            <div class="flex-1 text-left">
              <div class="text-sm font-medium text-slate-800 dark:text-slate-100">Vytvoriť príklady</div>
              <div class="text-xs text-gray-400">Automaticky generovať príklady podľa typu a obtiažnosti</div>
            </div>
            <TeacherIcon name="chevronDown" :size="16"
                         class="text-gray-400 transition-transform flex-shrink-0"
                         :class="genOpen && 'rotate-180'" />
          </button>

          <div v-if="genOpen" class="border-t border-slate-100 dark:border-slate-700 px-5 pt-4 pb-5 space-y-5">

            <!-- Jeden typ / Mix -->
            <div class="flex items-center gap-2 p-1.5 rounded-xl bg-slate-50 dark:bg-slate-700/40
                        border border-slate-200 dark:border-slate-700">
              <button @click="isMix = false"
                      :class="['flex-1 py-2 rounded-lg text-sm font-semibold transition-all',
                               !isMix ? 'bg-primary text-white' : 'text-gray-500 dark:text-gray-400 hover:bg-slate-100 dark:hover:bg-slate-700']">
                Jeden typ
              </button>
              <button @click="isMix = true"
                      :class="['flex-1 py-2 rounded-lg text-sm font-semibold transition-all',
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
                          @click="genType = t.value"
                          :class="[
                            'py-2.5 px-3 rounded-xl text-sm font-medium border-2 transition-all',
                            genType === t.value
                              ? 'border-secondary bg-secondary/10 dark:bg-secondary/20 text-secondary'
                              : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                          ]">
                    <span class="mr-1">{{ t.icon }}</span> {{ t.label }}
                  </button>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Počet príkladov <span class="text-secondary font-bold ml-1">{{ genCount }}</span>
                </label>
                <input type="range" v-model.number="genCount" min="3" max="30" step="1"
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
              <textarea v-model="genDescription" rows="3"
                        :placeholder="isMix
                          ? 'Napr: 5. ročník, precvičiť zlomky a slovné úlohy z geometrie...'
                          : 'Napr: násobilka 7, príklady so zvyškom, rovnice s dvoma premennými...'"
                        class="w-full px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-600
                               bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100
                               focus:outline-none focus:ring-2 focus:ring-secondary resize-none text-sm" />
              <p v-if="genError" class="text-red-500 text-sm mt-1">{{ genError }}</p>
            </div>

            <div class="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-700">
              <p class="text-xs text-gray-400">
                Vygeneruje sa
                <span class="font-medium text-slate-700 dark:text-slate-200">{{ genTotal }} príkladov</span>
              </p>
              <button @click="generateExamples" :disabled="genRunning"
                      class="flex items-center gap-1.5 px-3 py-2 bg-secondary text-white rounded-lg
                             font-semibold text-xs hover:bg-blue-600 disabled:opacity-50">
                <Spinner v-if="genRunning" class="w-3.5 h-3.5" />
                <TeacherIcon v-else name="sparkle" :size="13" />
                {{ genRunning ? 'Generujem…' : 'Generovať a pridať' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Selected examples -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div class="px-5 py-3.5 flex items-center justify-between border-b border-slate-100 dark:border-slate-700">
            <div class="flex items-center gap-2">
              <h3 class="text-sm font-medium text-slate-800 dark:text-slate-100">Vybraté príklady</h3>
              <span class="text-xs font-semibold px-1.5 h-5 flex items-center rounded-md
                           bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                {{ items.length }}
              </span>
            </div>
            <div v-if="items.length" class="flex items-center gap-1.5 text-xs text-gray-400">
              <template v-if="settings.show_points">
                <span class="font-medium text-slate-700 dark:text-slate-200">{{ totalPoints }} b</span>
                <span>·</span>
              </template>
              <button @click="clearItems" class="hover:text-accent transition-colors">Vyprázdniť</button>
            </div>
          </div>

          <div v-if="!items.length" class="py-12 text-center">
            <TeacherIcon name="book" :size="38" class="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
            <p class="text-sm text-slate-500 dark:text-slate-400">Žiadne príklady neboli pridané</p>
            <p class="text-xs text-gray-400 mt-1">
              Použite generátor alebo pridajte sadu zo zoznamu nižšie — prípadne označte príklady v
              <router-link :to="{ name: 'teacher-library' }" class="text-secondary hover:underline">knižnici</router-link>.
            </p>
          </div>

          <div v-else class="divide-y divide-slate-100 dark:divide-slate-700">
            <div v-for="(it, i) in items" :key="it.key"
                 draggable="true"
                 @dragstart="onDragStart(i, $event)"
                 @dragenter.prevent="onDragEnter(i)"
                 @dragover.prevent
                 @dragend="onDragEnd"
                 class="flex items-center gap-3 px-5 py-2.5 group transition-colors"
                 :class="dragIdx === i ? 'bg-secondary/5' : 'hover:bg-slate-50 dark:hover:bg-slate-700/40'">
              <TeacherIcon name="grip" :size="15"
                           class="text-slate-300 dark:text-slate-600 group-hover:text-slate-400 cursor-grab flex-shrink-0" />
              <span class="w-2 h-2 rounded-full flex-shrink-0" :class="it.dot" />
              <span class="text-xs font-bold text-slate-400 w-5 text-right flex-shrink-0">{{ i + 1 }}.</span>
              <div class="flex-1 min-w-0 font-mono text-sm text-slate-800 dark:text-slate-100 truncate">
                {{ it.example }}
                <span class="text-secondary font-semibold">= {{ it.answer }}</span>
              </div>
              <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-gray-400 flex-shrink-0">
                {{ it.input_type || 'INLINE' }}
              </span>
              <select v-model="it.answer_lines" title="Miesto na odpoveď"
                      class="flex-shrink-0 px-1.5 py-1 rounded-lg border border-slate-200 dark:border-slate-600
                             bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[11px]
                             focus:outline-none focus:ring-1 focus:ring-secondary">
                <option v-for="opt in ANSWER_LINES_OPTIONS" :key="String(opt.value)" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
              <label v-if="settings.show_points" class="flex items-center gap-1 text-[11px] text-gray-400 flex-shrink-0">
                <input v-model.number="it.points" type="number" min="0" step="0.5"
                       class="w-14 px-1.5 py-1 rounded-lg border border-slate-200 dark:border-slate-600
                              bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs text-right
                              focus:outline-none focus:ring-1 focus:ring-secondary" />
                b.
              </label>
              <button @click="removeItem(i)" title="Odstrániť z písomky"
                      class="w-6 h-6 rounded flex items-center justify-center flex-shrink-0
                             text-gray-400 hover:text-accent hover:bg-accent/10 transition-colors">
                <TeacherIcon name="close" :size="13" />
              </button>
            </div>
          </div>
        </div>

        <!-- Example sets -->
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div class="px-5 py-3.5 border-b border-slate-100 dark:border-slate-700 space-y-3">
            <h3 class="text-sm font-medium text-slate-800 dark:text-slate-100">Príkladové sady</h3>
            <div class="relative">
              <TeacherIcon name="search" :size="14"
                           class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              <input v-model="taskSearch" type="text" placeholder="Hľadať sady..."
                     class="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                            bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                            focus:outline-none focus:ring-1 focus:ring-secondary" />
            </div>
          </div>
          <div class="divide-y divide-slate-100 dark:divide-slate-700">
            <div v-for="t in filteredTasks" :key="t.id"
                 class="flex items-center gap-3 px-5 py-3 transition-colors"
                 :class="addedTaskIds.has(t.id) ? 'opacity-40' : 'hover:bg-slate-50 dark:hover:bg-slate-700/40'">
              <span class="w-2 h-2 rounded-full flex-shrink-0" :class="DOTS[taskColorIdx(t.id)]" />
              <div class="flex-1 min-w-0">
                <p class="text-sm text-slate-800 dark:text-slate-100 truncate">{{ t.name }}</p>
                <p class="text-xs text-gray-400">{{ t.example_count }} príkladov</p>
              </div>
              <span v-if="t.grade_levels?.length"
                    class="text-xs px-2 py-0.5 rounded-full border flex-shrink-0"
                    :class="PILLS[taskColorIdx(t.id)]">
                {{ t.grade_levels.join('., ') }}. ročník
              </span>
              <button @click="addTask(t)" :disabled="addedTaskIds.has(t.id) || addingTaskId === t.id"
                      class="flex-shrink-0 flex items-center gap-1 px-2.5 h-7 rounded-lg text-xs font-medium border transition-colors"
                      :class="addedTaskIds.has(t.id)
                        ? 'bg-slate-100 dark:bg-slate-700 border-transparent text-slate-500 dark:text-slate-400'
                        : 'border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700'">
                <TeacherIcon :name="addedTaskIds.has(t.id) ? 'check' : 'plus'" :size="12" />
                {{ addedTaskIds.has(t.id) ? 'Pridaná' : (addingTaskId === t.id ? '…' : 'Pridať') }}
              </button>
            </div>
            <p v-if="!filteredTasks.length" class="py-8 text-center text-sm text-gray-400">
              Žiadne sady neboli nájdené
            </p>
          </div>

          <!-- Unattached examples (not in any sada) -->
          <div v-if="unattached.length" class="border-t border-slate-200 dark:border-slate-700">
            <div role="button" tabindex="0" @click="unattachedOpen = !unattachedOpen"
                 @keydown.enter="unattachedOpen = !unattachedOpen"
                 class="w-full px-5 py-3 flex items-center gap-3 cursor-pointer select-none
                        hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors">
              <span class="w-2 h-2 rounded-full flex-shrink-0 bg-slate-400" />
              <div class="flex-1 min-w-0 text-left">
                <p class="text-sm text-slate-800 dark:text-slate-100">Nezaradené príklady</p>
                <p class="text-xs text-gray-400">{{ unattached.length }} príkladov mimo sád</p>
              </div>
              <button v-if="unattachedOpen" @click.stop="addAllUnattached"
                      class="flex-shrink-0 flex items-center gap-1 px-2.5 h-7 rounded-lg text-xs font-medium border transition-colors
                             border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200
                             hover:bg-slate-50 dark:hover:bg-slate-700">
                <TeacherIcon name="plus" :size="12" />
                Pridať všetky
              </button>
              <TeacherIcon name="chevronDown" :size="15"
                           class="text-gray-400 transition-transform flex-shrink-0"
                           :class="unattachedOpen && 'rotate-180'" />
            </div>

            <div v-if="unattachedOpen" class="divide-y divide-slate-100 dark:divide-slate-700 border-t border-slate-100 dark:border-slate-700">
              <div v-for="ex in unattached" :key="ex.id"
                   class="flex items-center gap-3 pl-10 pr-5 py-2.5 transition-colors"
                   :class="itemIds.has(ex.id) ? 'opacity-40' : 'hover:bg-slate-50 dark:hover:bg-slate-700/40'">
                <div class="flex-1 min-w-0 font-mono text-sm text-slate-800 dark:text-slate-100 truncate">
                  {{ ex.example }}
                  <span class="text-secondary font-semibold">= {{ ex.answer }}</span>
                </div>
                <button @click="addUnattachedExample(ex)" :disabled="itemIds.has(ex.id)"
                        class="flex-shrink-0 flex items-center gap-1 px-2.5 h-7 rounded-lg text-xs font-medium border transition-colors"
                        :class="itemIds.has(ex.id)
                          ? 'bg-slate-100 dark:bg-slate-700 border-transparent text-slate-500 dark:text-slate-400'
                          : 'border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700'">
                  <TeacherIcon :name="itemIds.has(ex.id) ? 'check' : 'plus'" :size="12" />
                  {{ itemIds.has(ex.id) ? 'Pridaný' : 'Pridať' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ════════ Right column — settings ════════ -->
      <div class="lg:sticky lg:top-20 space-y-4">
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div class="px-5 py-3.5 border-b border-slate-100 dark:border-slate-700 flex items-center gap-2">
            <TeacherIcon name="settings" :size="15" class="text-gray-400" />
            <h3 class="text-sm font-medium text-slate-800 dark:text-slate-100">Nastavenia tlače</h3>
          </div>

          <div class="p-5 space-y-5">
            <!-- Document -->
            <div class="space-y-2">
              <p class="text-xs text-slate-400 dark:text-slate-500 uppercase tracking-wider font-bold">Dokument</p>
              <input v-model="settings.title" type="text" placeholder="Názov dokumentu"
                     class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                            bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                            focus:outline-none focus:ring-1 focus:ring-secondary" />
              <input v-model="settings.class_name" type="text" placeholder="Trieda (napr. 5.A)"
                     class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                            bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                            focus:outline-none focus:ring-1 focus:ring-secondary" />
              <input v-model="settings.note" type="text" placeholder="Pokyny pre žiakov (voliteľné)"
                     class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                            bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                            focus:outline-none focus:ring-1 focus:ring-secondary" />
            </div>

            <hr class="border-slate-100 dark:border-slate-700" />

            <!-- Display toggles -->
            <div class="space-y-0.5">
              <p class="text-xs text-slate-400 dark:text-slate-500 uppercase tracking-wider font-bold mb-2">Zobrazenie</p>

              <div class="flex items-center justify-between py-2">
                <div>
                  <p class="text-sm text-slate-800 dark:text-slate-100">Zobraziť body</p>
                  <p class="text-xs text-gray-400">Každý príklad s bodovou hodnotou</p>
                </div>
                <ToggleSwitch v-model="settings.show_points" />
              </div>

              <div class="flex items-center justify-between py-2">
                <div>
                  <p class="text-sm text-slate-800 dark:text-slate-100">Úvodná strana</p>
                  <p class="text-xs text-gray-400">Pridať titulnú stranu</p>
                </div>
                <ToggleSwitch v-model="settings.cover_page" />
              </div>

              <div class="flex items-center justify-between py-2">
                <div>
                  <p class="text-sm text-slate-800 dark:text-slate-100">Hlavička</p>
                  <p class="text-xs text-gray-400">Záhlavie na každej strane</p>
                </div>
                <ToggleSwitch v-model="settings.show_header" />
              </div>
              <input v-if="settings.show_header" v-model="settings.header_text" type="text"
                     placeholder="Napr. Meno a priezvisko: ______"
                     class="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                            bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                            focus:outline-none focus:ring-1 focus:ring-secondary" />

              <div class="flex items-center justify-between py-2">
                <div>
                  <p class="text-sm text-slate-800 dark:text-slate-100">Kľúč odpovedí</p>
                  <p class="text-xs text-gray-400">Strana so správnymi odpoveďami</p>
                </div>
                <ToggleSwitch v-model="settings.answer_key" />
              </div>
            </div>

            <hr class="border-slate-100 dark:border-slate-700" />

            <!-- Spacing -->
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <p class="text-xs text-slate-400 dark:text-slate-500 uppercase tracking-wider font-bold">
                  Vertikálne medzery
                </p>
                <span class="text-xs font-medium tabular-nums text-slate-700 dark:text-slate-200">
                  {{ settings.spacing }} px
                </span>
              </div>
              <input v-model.number="settings.spacing" type="range" min="8" max="64" step="4"
                     class="w-full accent-secondary cursor-pointer" />
              <button @click="settings.spacing = RECOMMENDED_SPACING"
                      class="flex items-center gap-1.5 text-xs transition-colors"
                      :class="settings.spacing === RECOMMENDED_SPACING
                        ? 'text-secondary'
                        : 'text-gray-400 hover:text-slate-700 dark:hover:text-slate-200'">
                <TeacherIcon name="reset" :size="12" />
                {{ settings.spacing === RECOMMENDED_SPACING
                  ? 'Odporúčané (aktívne)'
                  : `Nastaviť odporúčané (${RECOMMENDED_SPACING} px)` }}
              </button>
            </div>

            <hr class="border-slate-100 dark:border-slate-700" />

            <!-- Layout -->
            <div class="space-y-2">
              <p class="text-xs text-slate-400 dark:text-slate-500 uppercase tracking-wider font-bold">Rozloženie</p>
              <div class="grid grid-cols-2 gap-2">
                <label class="block">
                  <span class="text-[11px] font-semibold text-gray-400">Skupiny</span>
                  <select v-model.number="settings.groups"
                          class="mt-1 w-full px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                                 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                                 focus:outline-none focus:ring-1 focus:ring-secondary">
                    <option :value="1">1 (bez skupín)</option>
                    <option :value="2">2 (A, B)</option>
                    <option :value="3">3 (A–C)</option>
                    <option :value="4">4 (A–D)</option>
                  </select>
                </label>
                <label class="block">
                  <span class="text-[11px] font-semibold text-gray-400">Písomiek na A4</span>
                  <select v-model.number="settings.per_page"
                          class="mt-1 w-full px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                                 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                                 focus:outline-none focus:ring-1 focus:ring-secondary">
                    <option :value="1">1 (celá strana)</option>
                    <option :value="2">2 (šetrenie papiera)</option>
                  </select>
                </label>
              </div>
              <p v-if="settings.groups > 1" class="text-[11px] text-gray-400">
                Skupina A má tvoje poradie, ďalšie skupiny majú premiešané poradie príkladov.
              </p>
              <p v-if="settings.per_page === 2 && items.length > 12" class="text-[11px] text-gray-400">
                Pri 2 písomkách na A4 sa dlhšia sada rozdelí na viac strán (tá istá polovica pokračuje na ďalšej strane) — nič sa neoreže.
              </p>

              <div class="grid grid-cols-2 gap-2 pt-1">
                <label class="block">
                  <span class="text-[11px] font-semibold text-gray-400">Stĺpce (INLINE/FRAC)</span>
                  <select v-model.number="settings.columns"
                          class="mt-1 w-full px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                                 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                                 focus:outline-none focus:ring-1 focus:ring-secondary">
                    <option v-for="n in [1,2,3,4]" :key="n" :value="n">{{ n }}</option>
                  </select>
                </label>
                <label class="block">
                  <span class="text-[11px] font-semibold text-gray-400">Riadky (WORD/VAR)</span>
                  <select v-model.number="settings.default_answer_lines"
                          class="mt-1 w-full px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                                 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                                 focus:outline-none focus:ring-1 focus:ring-secondary">
                    <option v-for="n in [2,3,4,5,6]" :key="n" :value="n">{{ n }}</option>
                  </select>
                </label>
              </div>
            </div>

            <hr class="border-slate-100 dark:border-slate-700" />

            <!-- Summary -->
            <div class="rounded-lg bg-slate-50 dark:bg-slate-700/40 px-4 py-3.5 space-y-2">
              <div class="flex justify-between text-xs">
                <span class="text-gray-400">Celkom príkladov</span>
                <span class="font-medium tabular-nums text-slate-800 dark:text-slate-100">{{ items.length }}</span>
              </div>
              <div v-if="settings.show_points" class="flex justify-between text-xs">
                <span class="text-gray-400">Celkové body</span>
                <span class="font-medium tabular-nums text-slate-800 dark:text-slate-100">{{ totalPoints }}</span>
              </div>
              <div class="flex justify-between text-xs">
                <span class="text-gray-400">Odhadované strany</span>
                <span class="font-medium tabular-nums text-slate-800 dark:text-slate-100">~{{ estimatedPages }}</span>
              </div>
            </div>
          </div>
        </div>

        <button @click="generatePdf(false)" :disabled="generating || !items.length"
                class="w-full h-11 flex items-center justify-center gap-2 bg-secondary text-white rounded-lg
                       font-semibold text-sm hover:bg-blue-600 disabled:opacity-50">
          <TeacherIcon name="download" :size="16" />
          {{ generating ? 'Generujem…' : 'Generovať PDF' }}
        </button>
        <p v-if="!items.length" class="text-xs text-center text-gray-400">
          Najprv pridajte aspoň jeden príklad
        </p>
      </div>
    </div>
  </div>
</template>
