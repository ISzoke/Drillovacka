<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import {
  getMyTeacherTasks, teacherListExamples, getTeacherTaskExamples, teacherPrintTest,
} from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import TeacherIcon from '@/components/TeacherIcon.vue';
import TeacherPageHeader from '@/components/TeacherPageHeader.vue';

const route = useRoute();
const authStore = useAuthStore();
const toastStore = useToastStore();

const loading = ref(true);
const myTasks = ref([]);
const sourceTaskId = ref(null);

// items = [{ id, example, answer, points }] in print order
const items = ref([]);

const settings = ref({
  title: 'Písomná práca',
  class_name: '',
  note: '',
  groups: 1,
  per_page: 1,
  show_points: true,
  answer_key: true,
});

const generating = ref(false);

const totalPoints = computed(() =>
  items.value.reduce((sum, it) => sum + (Number(it.points) || 0), 0)
);

watch(items, async () => {
  await nextTick();
  window.MathJax?.typeset();
}, { deep: false });

const toItem = (ex) => ({ id: ex.id, example: ex.example, answer: ex.answer, points: 1 });

const loadFromTask = async (taskId) => {
  loading.value = true;
  try {
    const data = await getTeacherTaskExamples(taskId, authStore.id);
    items.value = data.examples.map(toItem);
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri načítaní sady.', type: 'error', visible: true });
  }
  loading.value = false;
};

const loadFromIds = async (ids) => {
  loading.value = true;
  try {
    const all = await teacherListExamples(authStore.id);
    const byId = new Map(all.map(e => [e.id, e]));
    items.value = ids.filter(id => byId.has(id)).map(id => toItem(byId.get(id)));
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri načítaní príkladov.', type: 'error', visible: true });
  }
  loading.value = false;
};

onMounted(async () => {
  try {
    myTasks.value = await getMyTeacherTasks(authStore.id);
  } catch (e) {
    myTasks.value = [];
  }
  const ids = (route.query.ids || '').split(',').map(Number).filter(Boolean);
  const taskId = Number(route.query.taskId) || null;
  if (taskId) {
    sourceTaskId.value = taskId;
    const task = myTasks.value.find(t => t.id === taskId);
    if (task) settings.value.title = task.name;
    await loadFromTask(taskId);
  } else if (ids.length) {
    await loadFromIds(ids);
  } else {
    loading.value = false;
  }
});

watch(sourceTaskId, (taskId) => {
  if (!taskId) return;
  const task = myTasks.value.find(t => t.id === taskId);
  if (task) settings.value.title = task.name;
  loadFromTask(taskId);
});

const moveItem = (i, dir) => {
  const j = i + dir;
  if (j < 0 || j >= items.value.length) return;
  const arr = [...items.value];
  [arr[i], arr[j]] = [arr[j], arr[i]];
  items.value = arr;
};

const removeItem = (i) => { items.value = items.value.filter((_, idx) => idx !== i); };

const buildPayload = () => ({
  title: settings.value.title,
  class_name: settings.value.class_name,
  note: settings.value.note,
  groups: settings.value.groups,
  per_page: settings.value.per_page,
  show_points: settings.value.show_points,
  answer_key: settings.value.answer_key,
  items: items.value.map(it => ({ example_id: it.id, points: Number.isFinite(Number(it.points)) ? Number(it.points) : 1 })),
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
  <div class="pt-20 px-4 max-w-4xl mx-auto pb-16">

    <TeacherPageHeader
      title="Tlač písomky"
      subtitle="Vyber príklady, nastav body a skupiny a stiahni hotové PDF na tlač." />

    <div class="grid md:grid-cols-[1fr,290px] gap-5">

      <!-- Examples list -->
      <section>
        <div class="flex items-center justify-between mb-3 gap-2">
          <h2 class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
            Príklady v písomke
          </h2>
          <select v-model="sourceTaskId"
                  class="px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                         bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                         focus:outline-none focus:ring-1 focus:ring-secondary">
            <option :value="null">Načítať zo sady...</option>
            <option v-for="t in myTasks" :key="t.id" :value="t.id">{{ t.name }} ({{ t.example_count }})</option>
          </select>
        </div>

        <div v-if="loading" class="flex justify-center py-10"><Spinner /></div>

        <div v-else-if="!items.length"
             class="border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-2xl p-8 text-center">
          <div class="w-11 h-11 rounded-full bg-secondary/10 text-secondary flex items-center justify-center mx-auto mb-3">
            <TeacherIcon name="print" :size="22" />
          </div>
          <p class="font-semibold text-sm text-slate-700 dark:text-slate-200">Zatiaľ žiadne príklady</p>
          <p class="text-xs text-gray-400 mt-1">
            Vyber sadu vyššie, alebo označ príklady v
            <router-link :to="{ name: 'teacher-library' }" class="text-secondary hover:underline">knižnici</router-link>
            a klikni na „Tlačiť PDF".
          </p>
        </div>

        <div v-else class="space-y-1.5">
          <div v-for="(it, i) in items" :key="it.id"
               class="flex items-center gap-2 px-3 py-2 bg-white dark:bg-slate-800 rounded-xl
                      border border-slate-200 dark:border-slate-700">
            <span class="text-xs font-bold text-slate-400 w-5 text-right flex-shrink-0">{{ i + 1 }}.</span>
            <div class="flex-1 min-w-0 font-mono text-sm text-slate-800 dark:text-slate-100 truncate">
              {{ it.example }}
              <span class="text-secondary font-semibold">= {{ it.answer }}</span>
            </div>
            <label class="flex items-center gap-1 text-[11px] text-gray-400 flex-shrink-0">
              <input v-model.number="it.points" type="number" min="0" step="0.5"
                     class="w-14 px-1.5 py-1 rounded-lg border border-slate-200 dark:border-slate-600
                            bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs text-right
                            focus:outline-none focus:ring-1 focus:ring-secondary" />
              b.
            </label>
            <div class="flex items-center gap-0.5 pl-1.5 border-l border-slate-100 dark:border-slate-700 flex-shrink-0">
              <button @click="moveItem(i, -1)" :disabled="i === 0" title="Posunúť vyššie"
                      class="p-1 rounded-lg text-gray-400 hover:text-secondary hover:bg-secondary/10 disabled:opacity-30">
                <TeacherIcon name="chevronDown" :size="13" class="rotate-180" />
              </button>
              <button @click="moveItem(i, 1)" :disabled="i === items.length - 1" title="Posunúť nižšie"
                      class="p-1 rounded-lg text-gray-400 hover:text-secondary hover:bg-secondary/10 disabled:opacity-30">
                <TeacherIcon name="chevronDown" :size="13" />
              </button>
              <button @click="removeItem(i)" title="Odstrániť z písomky"
                      class="p-1 rounded-lg text-gray-400 hover:text-accent hover:bg-accent/10">
                <TeacherIcon name="delete" :size="13" />
              </button>
            </div>
          </div>

          <div class="text-xs text-gray-400 text-right pt-1">
            {{ items.length }} príkladov · spolu {{ totalPoints }} b.
          </div>
        </div>
      </section>

      <!-- Settings panel -->
      <aside>
        <h2 class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3">
          Nastavenia
        </h2>
        <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 space-y-3">

          <label class="block">
            <span class="text-[11px] font-semibold text-gray-400">Názov písomky</span>
            <input v-model="settings.title" type="text"
                   class="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                          bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                          focus:outline-none focus:ring-1 focus:ring-secondary" />
          </label>

          <label class="block">
            <span class="text-[11px] font-semibold text-gray-400">Trieda (voliteľné)</span>
            <input v-model="settings.class_name" type="text" placeholder="napr. 5.A"
                   class="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                          bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                          focus:outline-none focus:ring-1 focus:ring-secondary" />
          </label>

          <label class="block">
            <span class="text-[11px] font-semibold text-gray-400">Pokyny pre žiakov (voliteľné)</span>
            <input v-model="settings.note" type="text" placeholder="napr. Počítaj bez kalkulačky."
                   class="mt-1 w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                          bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                          focus:outline-none focus:ring-1 focus:ring-secondary" />
          </label>

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
          <p v-if="settings.groups > 1" class="text-[11px] text-gray-400 -mt-1">
            Skupina A má tvoje poradie, ďalšie skupiny majú premiešané poradie príkladov.
          </p>
          <p v-if="settings.per_page === 2 && items.length > 12" class="text-[11px] text-amber-500 -mt-1">
            Pri 2 písomkách na A4 sa zmestí len ~12 krátkych príkladov — dlhší zvyšok sa odreže.
          </p>

          <label class="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200 cursor-pointer">
            <input v-model="settings.show_points" type="checkbox" class="w-4 h-4 accent-secondary" />
            Zobraziť body pri príkladoch
          </label>
          <label class="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200 cursor-pointer">
            <input v-model="settings.answer_key" type="checkbox" class="w-4 h-4 accent-secondary" />
            Pridať kľúč správnych odpovedí
          </label>

          <div class="pt-2 space-y-2">
            <button @click="generatePdf(false)" :disabled="generating || !items.length"
                    class="w-full flex items-center justify-center gap-1.5 py-2.5 bg-secondary text-white rounded-lg
                           font-semibold text-sm hover:bg-blue-600 disabled:opacity-50">
              <TeacherIcon name="print" :size="15" />
              {{ generating ? 'Generujem…' : 'Stiahnuť PDF' }}
            </button>
            <button @click="generatePdf(true)" :disabled="generating || !items.length"
                    class="w-full py-2 rounded-lg text-secondary text-xs font-medium
                           bg-secondary/10 hover:bg-secondary/20 disabled:opacity-50">
              Otvoriť náhľad v novej karte
            </button>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>
