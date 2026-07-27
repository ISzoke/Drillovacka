<script setup>
import { ref, reactive, onMounted, nextTick, watch } from 'vue';
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

const loadingTasks = ref(true);
const myTasks = ref([]);

const loadingExamples = ref(true);
const examples = ref([]);
const gradeFilter = ref(null);
const locationFilter = ref(null); // null = all, 'unattached' = voľné, else a task id
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
  loadingTasks.value = true;
  try {
    myTasks.value = await getMyTeacherTasks(authStore.id);
  } catch (e) {
    myTasks.value = [];
  }
  loadingTasks.value = false;
};

const loadExamples = async () => {
  loadingExamples.value = true;
  try {
    examples.value = await teacherListExamples(authStore.id, {
      grade: gradeFilter.value,
      search: searchQuery.value,
      unattachedOnly: locationFilter.value === 'unattached',
      taskId: (locationFilter.value && locationFilter.value !== 'unattached') ? locationFilter.value : null,
    });
  } catch (e) {
    examples.value = [];
  }
  loadingExamples.value = false;
};

onMounted(() => { loadTasks(); loadExamples(); });
watch(gradeFilter, loadExamples);
watch(locationFilter, loadExamples);
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
    toastStore.addToast({ message: 'Ročník nastavený pre vybrané príklady.', type: 'success', visible: true });
    clearSelection();
    await loadExamples();
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri nastavovaní ročníka.', type: 'error', visible: true });
  }
  bulkGrading.value = false;
};

const bulkDeleteSelected = async () => {
  const n = selectedIds.value.size;
  if (!confirm(`Natrvalo zmazať ${n} príkladov? Zmaže sa aj história precvičovania žiakmi.`)) return;
  bulkDeleting.value = true;
  try {
    await teacherBulkDelete(authStore.id, [...selectedIds.value]);
    toastStore.addToast({ message: `${n} príkladov zmazaných.`, type: 'success', visible: true });
    clearSelection();
    await loadExamples();
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri mazaní.', type: 'error', visible: true });
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
    toastStore.addToast({ message: 'Príklad uložený.', type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri ukladaní príkladu.', type: 'error', visible: true });
  }
  saving.value = false;
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
      grade: newExample.grade,
    });
    if (gradeFilter.value === null || gradeFilter.value === created.grade) {
      examples.value.unshift(created);
    }
    newExample.example = ''; newExample.answer = ''; newExample.steps = []; newExample.grade = null;
    showNewForm.value = false;
    toastStore.addToast({ message: 'Príklad pridaný do knižnice.', type: 'success', visible: true });
  } catch (e) {
    toastStore.addToast({ message: 'Chyba pri vytváraní príkladu.', type: 'error', visible: true });
  }
  creating.value = false;
};
</script>

<template>
  <div class="pt-20 px-4 max-w-3xl mx-auto pb-16">

    <TeacherPageHeader
      title="Moja knižnica"
      subtitle="Vlastné sady a príklady, ktoré vieš voľne upravovať, mazať a preskladať." />

    <!-- Moje sady -->
    <section class="mb-8">
      <h2 class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3">
        Moje sady
      </h2>
      <div v-if="loadingTasks" class="flex justify-center py-6"><Spinner /></div>
      <div v-else-if="!myTasks.length"
           class="border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-2xl p-8 text-center">
        <div class="w-11 h-11 rounded-full bg-secondary/10 text-secondary flex items-center justify-center mx-auto mb-3">
          <TeacherIcon name="library" :size="22" />
        </div>
        <p class="font-semibold text-sm text-slate-700 dark:text-slate-200">Zatiaľ nemáš žiadne vlastné sady</p>
        <p class="text-xs text-gray-400 mt-1">Vytvor si novú, alebo si skopíruj existujúcu z prehľadu sád v triede.</p>
      </div>
      <div v-else class="grid sm:grid-cols-2 gap-3">
        <router-link v-for="t in myTasks" :key="t.id"
                     :to="{ name: 'teacher-edit-task-standalone', params: { taskId: t.id } }"
                     class="block px-4 py-3.5 bg-white dark:bg-slate-800 rounded-2xl
                            border border-slate-200 dark:border-slate-700 hover:border-secondary
                            hover:-translate-y-0.5 transition-all shadow-sm">
          <span class="font-semibold text-slate-800 dark:text-slate-100 text-sm">{{ t.name }}</span>
          <div class="flex items-center gap-1.5 mt-2">
            <span v-if="t.grade_levels.length" class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-tertiary/50 text-primary dark:bg-tertiary/20 dark:text-tertiary">
              {{ t.grade_levels.join(', ') }}. roč.
            </span>
            <span class="text-xs text-gray-400">{{ t.example_count }} príkladov</span>
            <button @click.stop.prevent="$router.push({ name: 'teacher-print', query: { taskId: t.id } })"
                    title="Tlačiť ako písomku (PDF)"
                    class="ml-auto flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full
                           text-gray-400 hover:text-secondary hover:bg-secondary/10 font-medium">
              <TeacherIcon name="print" :size="11" /> Tlačiť
            </button>
          </div>
        </router-link>
      </div>
    </section>

    <!-- Moje príklady -->
    <section>
      <div class="flex items-center justify-between mb-3 gap-2">
        <h2 class="text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
          Moje príklady
        </h2>
        <div class="flex items-center gap-2">
          <input v-model="searchQuery" type="text" placeholder="Hľadať..."
                 class="w-36 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                        bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                        focus:outline-none focus:ring-1 focus:ring-secondary" />
          <select v-model="gradeFilter"
                  class="px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                         bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                         focus:outline-none focus:ring-1 focus:ring-secondary">
            <option :value="null">Všetky ročníky</option>
            <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. ročník</option>
          </select>
          <select v-model="locationFilter"
                  class="px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                         bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                         focus:outline-none focus:ring-1 focus:ring-secondary">
            <option :value="null">Všetky umiestnenia</option>
            <option value="unattached">Voľné (mimo sady)</option>
            <option v-for="t in myTasks" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>
      </div>

      <!-- Selection toolbar -->
      <div v-if="selectedIds.size" class="flex items-center flex-wrap gap-2 mb-3 px-3 py-2 rounded-xl bg-secondary/10">
        <span class="text-xs font-semibold text-secondary mr-1">{{ selectedIds.size }} vybraných</span>
        <button @click="openOrganizeModal(false)"
                class="flex items-center gap-1 text-xs px-2.5 py-1.5 bg-white dark:bg-slate-800 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
          <TeacherIcon name="library" :size="12" /> Vytvoriť sadu
        </button>
        <button @click="openOrganizeModal(true)"
                class="flex items-center gap-1 text-xs px-2.5 py-1.5 bg-white dark:bg-slate-800 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
          <TeacherIcon name="calendar" :size="12" /> Priradiť ako DÚ
        </button>
        <router-link :to="{ name: 'teacher-print', query: { ids: [...selectedIds].join(',') } }"
                     class="flex items-center gap-1 text-xs px-2.5 py-1.5 bg-white dark:bg-slate-800 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
          <TeacherIcon name="print" :size="12" /> Tlačiť PDF
        </router-link>
        <div class="flex items-center gap-1">
          <select v-model="bulkGradeChoice"
                  class="px-2 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                         bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs">
            <option :value="null">roč. —</option>
            <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. roč.</option>
          </select>
          <button @click="bulkApplyGrade" :disabled="bulkGrading"
                  class="text-xs px-2.5 py-1.5 bg-white dark:bg-slate-800 text-secondary rounded-lg hover:bg-secondary/20 font-medium disabled:opacity-50">
            {{ bulkGrading ? '...' : 'Nastaviť ročník' }}
          </button>
        </div>
        <button @click="bulkDeleteSelected" :disabled="bulkDeleting"
                class="flex items-center gap-1 text-xs px-2.5 py-1.5 bg-white dark:bg-slate-800 text-accent rounded-lg hover:bg-accent/10 font-medium disabled:opacity-50">
          <TeacherIcon name="delete" :size="12" /> {{ bulkDeleting ? '...' : 'Zmazať' }}
        </button>
        <button @click="clearSelection" class="text-xs px-2 py-1.5 text-gray-400 hover:text-gray-600 ml-auto">
          Zrušiť výber
        </button>
      </div>

      <div v-if="loadingExamples" class="flex justify-center py-6"><Spinner /></div>

      <div v-else class="space-y-2 mb-4">
        <div v-if="examples.length" class="flex justify-end -mt-1">
          <button @click="selectAllVisible" class="text-xs text-secondary hover:underline">Vybrať všetky zobrazené</button>
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
              {{ ex.grade }}. roč.
            </span>
            <span v-else class="text-[11px] px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-gray-400 flex-shrink-0">
              bez ročníka
            </span>
            <div class="flex items-center gap-0.5 pl-2 border-l border-slate-100 dark:border-slate-700 flex-shrink-0" @click.stop>
              <button @click="startEdit(ex)" title="Upraviť"
                      class="p-1.5 rounded-lg text-gray-400 hover:text-secondary hover:bg-secondary/10">
                <TeacherIcon name="edit" :size="14" />
              </button>
              <button @click="deleteForever(ex)" title="Zmazať natrvalo"
                      class="p-1.5 rounded-lg text-gray-400 hover:text-accent hover:bg-accent/10">
                <TeacherIcon name="delete" :size="14" />
              </button>
            </div>
          </div>

          <!-- Expanded detail / edit -->
          <div v-if="expandedId === ex.id" class="border-t border-slate-100 dark:border-slate-700 px-3 py-3 bg-slate-50 dark:bg-slate-900/40">

            <div v-if="editingId !== ex.id" class="text-xs text-gray-500 dark:text-gray-400 space-y-1.5">
              <div><span class="text-gray-400">Typ:</span> {{ ex.input_type }}</div>
              <div>
                <span class="text-gray-400">Umiestnenie:</span>
                {{ ex.task_name ? `v sade „${ex.task_name}"` : 'voľný (nie je v žiadnej sade)' }}
              </div>
              <div v-if="ex.steps.length">
                <span class="text-gray-400">Kroky riešenia:</span>
                <ol class="list-decimal list-inside mt-1 space-y-0.5">
                  <li v-for="(s, i) in ex.steps" :key="i">{{ s }}</li>
                </ol>
              </div>
            </div>

            <div v-else class="space-y-2">
              <input v-model="editDraft.example" type="text" placeholder="Príklad"
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
                <input v-model="editDraft.answer" type="text" placeholder="Odpoveď"
                       class="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                              bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                              font-mono focus:outline-none focus:ring-1 focus:ring-secondary" />
                <select v-model="editDraft.grade"
                        class="w-20 px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                               bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs
                               focus:outline-none focus:ring-1 focus:ring-secondary">
                  <option :value="null">roč. —</option>
                  <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. roč.</option>
                </select>
              </div>
              <div class="space-y-1.5">
                <div v-for="(step, i) in editDraft.steps" :key="i" class="flex gap-2">
                  <input v-model="editDraft.steps[i]" type="text" :placeholder="`Krok ${i + 1}`"
                         class="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                                bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm
                                focus:outline-none focus:ring-1 focus:ring-secondary" />
                  <button @click="removeStep(editDraft, i)" class="text-accent/70 hover:text-accent text-lg leading-none">×</button>
                </div>
                <button @click="addStep(editDraft)" class="text-xs text-secondary hover:underline">+ Pridať krok</button>
              </div>
              <div class="flex gap-2 pt-1 justify-end">
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
        </div>

        <div v-if="!examples.length" class="text-sm text-gray-400 text-center py-6">
          <template v-if="searchQuery">Žiadne príklady pre „{{ searchQuery }}".</template>
          <template v-else-if="gradeFilter">Žiadne príklady pre {{ gradeFilter }}. ročník.</template>
          <template v-else>Knižnica je zatiaľ prázdna.</template>
        </div>
      </div>

      <button @click="showNewForm = !showNewForm"
              class="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-secondary/10 dark:bg-secondary/20 text-secondary rounded-lg hover:bg-secondary/20 font-medium">
        <TeacherIcon name="plus" :size="12" /> Nový príklad do knižnice
      </button>

      <div v-if="showNewForm" class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-3 space-y-2 mt-3">
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
          <select v-model="newExample.grade"
                  class="w-20 px-2 py-2 rounded-lg border border-slate-200 dark:border-slate-600
                         bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 text-xs
                         focus:outline-none focus:ring-1 focus:ring-secondary">
            <option :value="null">roč. —</option>
            <option v-for="g in [1,2,3,4,5,6,7,8,9]" :key="g" :value="g">{{ g }}. roč.</option>
          </select>
        </div>
        <div class="space-y-1.5">
          <div v-for="(step, i) in newExample.steps" :key="i" class="flex gap-2">
            <input v-model="newExample.steps[i]" type="text" :placeholder="`Krok ${i + 1}`"
                   class="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600
                          bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-100 text-sm
                          focus:outline-none focus:ring-1 focus:ring-secondary" />
            <button @click="removeStep(newExample, i)" class="text-accent/70 hover:text-accent text-lg leading-none">×</button>
          </div>
          <button @click="addStep(newExample)" class="text-xs text-secondary hover:underline">+ Pridať krok</button>
        </div>
        <button @click="submitNewExample" :disabled="creating"
                class="w-full py-2 bg-secondary text-white rounded-lg font-semibold text-sm hover:bg-blue-600 disabled:opacity-50">
          {{ creating ? 'Pridávam...' : 'Pridať do knižnice' }}
        </button>
      </div>
    </section>

    <TeacherBulkOrganizeModal v-if="showOrganizeModal"
                              :example-ids="[...selectedIds]"
                              :my-tasks="myTasks"
                              :default-homework="organizeDefaultHomework"
                              @close="showOrganizeModal = false"
                              @success="onOrganizeSuccess" />

  </div>
</template>
