<script setup>
import { computed, onMounted, ref } from 'vue';
import Spinner from '@/components/Spinner.vue';
import { getGradeLevels, getTaskAssignmentOverview, updateTaskGradeLevels } from '@/api/apiClient';
import { useToastStore } from '@/stores/useToastStore';

const gradeLevels = ref([]);
const tasks = ref([]);
const selectedGradeId = ref(null);
const searchQuery = ref('');
const loading = ref(true);
const savingTaskIds = ref({});

const toastStore = useToastStore();

const normalizeText = (value = '') => String(value)
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase();

const sortTasksByName = (left, right) => left.name.localeCompare(right.name, 'sk');

const matchesSearch = (task, query) => {
  if (!query) return true;

  const haystack = [
    task.name,
    ...(task.skills || []).map((skill) => skill.name),
    ...(task.grade_levels || []).map((grade) => `${grade.grade}. rocnik`),
  ]
    .join(' ')
    .trim();

  return normalizeText(haystack).includes(query);
};

const hasSelectedGrade = (task) => (task.grade_levels || []).some((grade) => grade.id === selectedGradeId.value);

const selectedGrade = computed(() => (
  gradeLevels.value.find((grade) => grade.id === selectedGradeId.value) || null
));

const normalizedSearchQuery = computed(() => normalizeText(searchQuery.value));

const visibleTasks = computed(() => (
  tasks.value
    .filter((task) => matchesSearch(task, normalizedSearchQuery.value))
    .sort(sortTasksByName)
));

const assignedTasks = computed(() => visibleTasks.value.filter((task) => hasSelectedGrade(task)));

const availableTasks = computed(() => visibleTasks.value.filter((task) => !hasSelectedGrade(task)));

const setTaskSaving = (taskId, saving) => {
  savingTaskIds.value = {
    ...savingTaskIds.value,
    [taskId]: saving,
  };
};

const replaceTaskGradeLevels = (taskId, gradeLevelsPayload) => {
  const taskIndex = tasks.value.findIndex((task) => task.id === taskId);
  if (taskIndex === -1) return;

  tasks.value[taskIndex] = {
    ...tasks.value[taskIndex],
    grade_levels: gradeLevelsPayload || [],
  };
};

const updateTaskMembership = async (task, shouldAssign) => {
  if (!selectedGrade.value) return;

  const currentGradeIds = (task.grade_levels || []).map((grade) => grade.id);
  const nextGradeIds = shouldAssign
    ? Array.from(new Set([...currentGradeIds, selectedGrade.value.id])).sort((a, b) => a - b)
    : currentGradeIds.filter((gradeId) => gradeId !== selectedGrade.value.id);

  setTaskSaving(task.id, true);

  try {
    const result = await updateTaskGradeLevels(task.id, nextGradeIds);
    replaceTaskGradeLevels(task.id, result.grade_levels);

    toastStore.addToast({
      message: shouldAssign
        ? `Sada "${task.name}" bola pridaná do ${selectedGrade.value.grade}. ročníka`
        : `Sada "${task.name}" bola odobratá z ${selectedGrade.value.grade}. ročníka`,
      type: 'success',
      visible: true,
    });
  } catch (error) {
    toastStore.addToast({
      message: typeof error === 'string' ? error : 'Zmenu sa nepodarilo uložiť',
      type: 'error',
      visible: true,
    });
  } finally {
    setTaskSaving(task.id, false);
  }
};

onMounted(async () => {
  try {
    const [gradeData, taskData] = await Promise.all([
      getGradeLevels(),
      getTaskAssignmentOverview(),
    ]);

    gradeLevels.value = gradeData || [];
    tasks.value = taskData || [];

    if (gradeLevels.value.length > 0) {
      selectedGradeId.value = gradeLevels.value[0].id;
    }
  } catch (error) {
    toastStore.addToast({
      message: 'Tasky podľa ročníka sa nepodarilo načítať',
      type: 'error',
      visible: true,
    });
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 pt-12 pb-16">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h1 class="text-4xl font-bold text-primary">Tasky podľa ročníka</h1>
        <p class="mt-2 text-slate-600">
          Vyber ročník a ručne mu priraď alebo odober sady príkladov.
        </p>
      </div>

      <div class="flex flex-col sm:flex-row gap-3">
        <RouterLink
          to="/tasks"
          class="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-3 font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          Všetky tasky
        </RouterLink>
        <RouterLink
          to="/bulk-import"
          class="inline-flex items-center justify-center rounded-lg bg-sky-600 px-4 py-3 font-semibold text-white transition hover:bg-sky-700"
        >
          Hromadný import
        </RouterLink>
        <RouterLink
          to="/sandbox"
          class="inline-flex items-center justify-center rounded-lg bg-green-600 px-4 py-3 font-semibold text-white transition hover:bg-green-700"
        >
          Vytvoriť novú sadu
        </RouterLink>
      </div>
    </div>

    <div class="mt-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div class="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Vybraný ročník
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <button
          v-for="grade in gradeLevels"
          :key="grade.id"
          type="button"
          @click="selectedGradeId = grade.id"
          class="rounded-full border px-4 py-2 text-sm font-semibold transition"
          :class="selectedGradeId === grade.id
            ? 'border-primary bg-primary text-white shadow'
            : 'border-slate-300 bg-white text-slate-700 hover:border-primary hover:text-primary'"
        >
          {{ grade.grade }}. ročník
        </button>
      </div>

      <div class="mt-4">
        <label for="task-grade-search" class="block text-sm font-semibold text-slate-700 mb-2">
          Hľadať task alebo zručnosť
        </label>
        <input
          id="task-grade-search"
          v-model="searchQuery"
          type="text"
          placeholder="Napr. zlomky, percentá, algebra..."
          class="w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
        >
      </div>
    </div>

    <Spinner v-if="loading" />

    <div v-else-if="selectedGrade" class="mt-6 grid gap-6 xl:grid-cols-2">
      <section class="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-4 shadow-sm">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-2xl font-bold text-slate-900">V {{ selectedGrade.grade }}. ročníku</h2>
            <p class="text-sm text-slate-600">Tasky, ktoré sa už v tomto ročníku zobrazujú.</p>
          </div>
          <span class="rounded-full bg-emerald-600 px-3 py-1 text-sm font-bold text-white">
            {{ assignedTasks.length }}
          </span>
        </div>

        <div v-if="assignedTasks.length === 0" class="mt-4 rounded-xl border border-dashed border-emerald-300 bg-white/70 px-4 py-6 text-sm text-slate-600">
          Pre tento ročník zatiaľ nemáš priradený žiadny task.
        </div>

        <div v-else class="mt-4 space-y-3">
          <article
            v-for="task in assignedTasks"
            :key="`assigned-${task.id}`"
            class="rounded-xl border border-white bg-white p-4 shadow-sm"
          >
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div class="min-w-0 flex-1">
                <h3 class="text-lg font-bold text-slate-900 break-words">{{ task.name }}</h3>

                <div class="mt-2 flex flex-wrap gap-2 text-xs font-semibold">
                  <span class="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
                    {{ task.example_count }} príkladov
                  </span>
                  <span
                    v-for="grade in task.grade_levels"
                    :key="`${task.id}-grade-${grade.id}`"
                    class="rounded-full bg-sky-100 px-3 py-1 text-sky-800"
                  >
                    {{ grade.grade }}. ročník
                  </span>
                </div>

                <div class="mt-3 flex flex-wrap gap-2">
                  <span
                    v-for="skill in task.skills"
                    :key="`${task.id}-skill-${skill.id}`"
                    class="rounded-full bg-slate-200 px-3 py-1 text-xs font-medium text-slate-700"
                  >
                    {{ skill.name }}
                  </span>
                  <span
                    v-if="(task.skills || []).length === 0"
                    class="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800"
                  >
                    Bez zručností
                  </span>
                </div>
              </div>

              <button
                type="button"
                :disabled="savingTaskIds[task.id]"
                @click="updateTaskMembership(task, false)"
                class="inline-flex items-center justify-center rounded-lg bg-red-600 px-4 py-3 font-semibold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-red-300"
              >
                {{ savingTaskIds[task.id] ? 'Ukladám...' : 'Odobrať z ročníka' }}
              </button>
            </div>
          </article>
        </div>
      </section>

      <section class="rounded-2xl border border-sky-200 bg-sky-50/70 p-4 shadow-sm">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h2 class="text-2xl font-bold text-slate-900">Dostupné na pridanie</h2>
            <p class="text-sm text-slate-600">Tasky, ktoré ešte k tomuto ročníku neprináležia.</p>
          </div>
          <span class="rounded-full bg-sky-600 px-3 py-1 text-sm font-bold text-white">
            {{ availableTasks.length }}
          </span>
        </div>

        <div v-if="availableTasks.length === 0" class="mt-4 rounded-xl border border-dashed border-sky-300 bg-white/70 px-4 py-6 text-sm text-slate-600">
          Nenašli sa žiadne ďalšie tasky na pridanie.
        </div>

        <div v-else class="mt-4 space-y-3">
          <article
            v-for="task in availableTasks"
            :key="`available-${task.id}`"
            class="rounded-xl border border-white bg-white p-4 shadow-sm"
          >
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div class="min-w-0 flex-1">
                <h3 class="text-lg font-bold text-slate-900 break-words">{{ task.name }}</h3>

                <div class="mt-2 flex flex-wrap gap-2 text-xs font-semibold">
                  <span class="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
                    {{ task.example_count }} príkladov
                  </span>
                  <span
                    v-for="grade in task.grade_levels"
                    :key="`${task.id}-available-grade-${grade.id}`"
                    class="rounded-full bg-slate-100 px-3 py-1 text-slate-700"
                  >
                    {{ grade.grade }}. ročník
                  </span>
                  <span
                    v-if="(task.grade_levels || []).length === 0"
                    class="rounded-full bg-amber-100 px-3 py-1 text-amber-800"
                  >
                    Zatiaľ nepriradené
                  </span>
                </div>

                <div class="mt-3 flex flex-wrap gap-2">
                  <span
                    v-for="skill in task.skills"
                    :key="`${task.id}-available-skill-${skill.id}`"
                    class="rounded-full bg-slate-200 px-3 py-1 text-xs font-medium text-slate-700"
                  >
                    {{ skill.name }}
                  </span>
                  <span
                    v-if="(task.skills || []).length === 0"
                    class="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800"
                  >
                    Bez zručností
                  </span>
                </div>
              </div>

              <button
                type="button"
                :disabled="savingTaskIds[task.id]"
                @click="updateTaskMembership(task, true)"
                class="inline-flex items-center justify-center rounded-lg bg-primary px-4 py-3 font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {{ savingTaskIds[task.id] ? 'Ukladám...' : 'Pridať do ročníka' }}
              </button>
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>
