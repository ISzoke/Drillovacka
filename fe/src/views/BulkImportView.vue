<script setup>
import { computed, onMounted, ref } from 'vue';
import Spinner from '@/components/Spinner.vue';
import { getGradeLevels, getSkillTree, bulkImportTasks } from '@/api/apiClient';
import { useToastStore } from '@/stores/useToastStore';

const toastStore = useToastStore();

const gradeLevels = ref([]);
const skills = ref([]);
const loading = ref(true);
const importing = ref(false);
const results = ref(null);

// Fallback selectors (used only if task in JSON has no skill_ids / grade_ids)
const selectedSkillIds = ref([]);
const selectedGradeIds = ref([]);
const taskForm = ref('classic');
const jsonInput = ref('');

const jsonPlaceholder = `{
  "tasks": [
    {
      "task_name": "Rimske cisla I.",
      "skill_name": "Rimske cisla",
      "task_form": "classic",
      "grade_ids": [5],
      "examples": [
        { "example": "VII =", "input_type": "INLINE", "answer": "7" },
        { "example": "XIV =", "input_type": "INLINE", "answer": "14" }
      ]
    }
  ]
}`;

// Flatten tree and keep ONLY leaf nodes (no children)
const leafSkills = computed(() => {
  const result = [];
  const flatten = (nodes, depth = 0) => {
    for (const node of nodes || []) {
      const hasChildren = node.children && node.children.length > 0;
      if (!hasChildren) {
        result.push({ ...node, depth });
      } else {
        flatten(node.children, depth + 1);
      }
    }
  };
  flatten(skills.value);
  return result.sort((a, b) => a.name.localeCompare(b.name, 'sk'));
});

const toggleSkill = (skillId) => {
  const idx = selectedSkillIds.value.indexOf(skillId);
  if (idx === -1) selectedSkillIds.value.push(skillId);
  else selectedSkillIds.value.splice(idx, 1);
};

const toggleGrade = (gradeId) => {
  const idx = selectedGradeIds.value.indexOf(gradeId);
  if (idx === -1) selectedGradeIds.value.push(gradeId);
  else selectedGradeIds.value.splice(idx, 1);
};

// Accept both {"tasks": [...]} and plain [...]
const parsedTasks = computed(() => {
  if (!jsonInput.value.trim()) return null;
  try {
    const parsed = JSON.parse(jsonInput.value.trim());
    if (Array.isArray(parsed)) return parsed;
    if (parsed && Array.isArray(parsed.tasks)) return parsed.tasks;
    return [parsed];
  } catch {
    return null;
  }
});

const jsonError = computed(() => {
  if (!jsonInput.value.trim()) return null;
  try {
    JSON.parse(jsonInput.value.trim());
    return null;
  } catch (e) {
    return e.message;
  }
});

const previewCount = computed(() => {
  if (!parsedTasks.value) return { tasks: 0, examples: 0 };
  return {
    tasks: parsedTasks.value.length,
    examples: parsedTasks.value.reduce((sum, t) => sum + (t.examples || []).length, 0),
  };
});

// Tasks are self-sufficient if each has skill_ids OR skill_name
const allTasksSelfSufficient = computed(() =>
  parsedTasks.value && parsedTasks.value.every(t =>
    (t.skill_ids && t.skill_ids.length > 0) || (t.skill_name && t.skill_name.trim())
  )
);

const canSubmit = computed(() =>
  parsedTasks.value &&
  !importing.value &&
  (allTasksSelfSufficient.value || selectedSkillIds.value.length > 0)
);

const handleImport = async () => {
  if (!canSubmit.value) return;
  importing.value = true;
  results.value = null;
  try {
    const tasks = parsedTasks.value.map((t) => ({
      task_name: t.task_name,
      task_form: t.task_form || taskForm.value,
      skill_ids: t.skill_ids?.length ? t.skill_ids : selectedSkillIds.value,
      grade_ids: t.grade_ids?.length ? t.grade_ids : selectedGradeIds.value,
      examples: t.examples || [],
    }));
    const response = await bulkImportTasks(tasks);
    results.value = response.results;
    const created = response.results.filter(r => r.status === 'created' || r.status === 'updated').length;
    const totalExamples = response.results.reduce((s, r) => s + (r.examples_added || 0), 0);
    toastStore.addToast({
      message: `Import dokončený: ${created} taskov, ${totalExamples} príkladov`,
      type: 'success',
      visible: true,
    });
  } catch (error) {
    toastStore.addToast({
      message: typeof error === 'string' ? error : 'Import sa nepodaril',
      type: 'error',
      visible: true,
    });
  } finally {
    importing.value = false;
  }
};

onMounted(async () => {
  try {
    const [gradeData, skillData] = await Promise.all([
      getGradeLevels(),
      getSkillTree(),
    ]);
    gradeLevels.value = gradeData || [];
    skills.value = skillData || [];
  } catch {
    toastStore.addToast({ message: 'Nepodarilo sa načítať dáta', type: 'error', visible: true });
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 pt-12 pb-16">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h1 class="text-4xl font-bold text-primary">Hromadný import</h1>
        <p class="mt-2 text-slate-600">
          Vlož JSON s taskami a príkladmi. Ak každý task obsahuje <code>skill_ids</code> a <code>grade_ids</code>,
          selektory nižšie sú voliteľné záloha.
        </p>
      </div>
      <div class="flex gap-3">
        <RouterLink to="/tasks"
          class="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-3 font-semibold text-slate-700 transition hover:bg-slate-50">
          Všetky tasky
        </RouterLink>
        <RouterLink to="/tasks/grades"
          class="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-3 font-semibold text-slate-700 transition hover:bg-slate-50">
          Podľa ročníka
        </RouterLink>
      </div>
    </div>

    <Spinner v-if="loading" />

    <div v-else class="mt-6 space-y-6">

      <!-- JSON input FIRST -->
      <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-bold text-slate-900">JSON dáta</h2>
        <p class="text-sm text-slate-500 mb-3">
          Podporuje formát <code>{"tasks": [...]}</code> aj priame pole <code>[...]</code>.
          Každý task môže mať vlastné <code>skill_ids</code> a <code>grade_ids</code> — vtedy selektory nižšie nie sú potrebné.
        </p>
        <textarea
          v-model="jsonInput"
          :placeholder="jsonPlaceholder"
          rows="16"
          class="w-full rounded-xl border border-slate-300 px-4 py-3 font-mono text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
        ></textarea>

        <div v-if="jsonError" class="mt-2 rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">
          JSON chyba: {{ jsonError }}
        </div>
        <div v-else-if="parsedTasks" class="mt-2 rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-2 text-sm text-emerald-800">
          ✓ Rozpoznaných <strong>{{ previewCount.tasks }}</strong> taskov
          s <strong>{{ previewCount.examples }}</strong> príkladmi
          <span v-if="allTasksSelfSufficient" class="ml-2 text-emerald-600 font-semibold">
            · skill_ids a grade_ids sú v JSON ✓
          </span>
        </div>
      </section>

      <!-- Fallback: Leaf skills selector -->
      <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-bold text-slate-900">
          Záložné zručnosti
          <span class="ml-2 text-sm font-normal text-slate-400">(použijú sa ak task v JSON nemá skill_ids)</span>
        </h2>
        <p class="text-sm text-slate-500 mb-3">
          Zobrazené sú len leaf skills (bez podskills).
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="skill in leafSkills"
            :key="skill.id"
            type="button"
            @click="toggleSkill(skill.id)"
            class="rounded-full border px-3 py-1.5 text-sm font-medium transition"
            :class="selectedSkillIds.includes(skill.id)
              ? 'border-primary bg-primary text-white'
              : 'border-slate-300 bg-white text-slate-700 hover:border-primary hover:text-primary'"
          >
            {{ skill.name }}
          </button>
        </div>
        <p v-if="!allTasksSelfSufficient && selectedSkillIds.length === 0"
           class="mt-2 text-sm text-amber-600 font-medium">
          Niektoré tasky v JSON nemajú skill_ids — vyber záložnú zručnosť
        </p>
      </section>

      <!-- Fallback: Grade selector -->
      <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-bold text-slate-900">
          Záložné ročníky
          <span class="ml-2 text-sm font-normal text-slate-400">(použijú sa ak task v JSON nemá grade_ids)</span>
        </h2>
        <div class="flex flex-wrap gap-2 mt-3">
          <button
            v-for="grade in gradeLevels"
            :key="grade.id"
            type="button"
            @click="toggleGrade(grade.id)"
            class="rounded-full border px-4 py-2 text-sm font-semibold transition"
            :class="selectedGradeIds.includes(grade.id)
              ? 'border-primary bg-primary text-white shadow'
              : 'border-slate-300 bg-white text-slate-700 hover:border-primary hover:text-primary'"
          >
            {{ grade.grade }}. ročník
          </button>
        </div>
      </section>

      <!-- Form type fallback -->
      <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-bold text-slate-900">
          Záložný typ tasku
          <span class="ml-2 text-sm font-normal text-slate-400">(ak task v JSON nemá task_form)</span>
        </h2>
        <div class="flex gap-3 mt-3">
          <button type="button" @click="taskForm = 'classic'"
            class="rounded-lg border px-4 py-2 text-sm font-semibold transition"
            :class="taskForm === 'classic' ? 'border-primary bg-primary text-white' : 'border-slate-300 bg-white text-slate-700'">
            Classic
          </button>
          <button type="button" @click="taskForm = 'word-problem'"
            class="rounded-lg border px-4 py-2 text-sm font-semibold transition"
            :class="taskForm === 'word-problem' ? 'border-primary bg-primary text-white' : 'border-slate-300 bg-white text-slate-700'">
            Word Problem
          </button>
        </div>
      </section>

      <!-- Submit -->
      <div class="flex items-center gap-4">
        <button
          type="button"
          :disabled="!canSubmit"
          @click="handleImport"
          class="rounded-xl bg-green-600 px-6 py-3 text-lg font-bold text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {{ importing ? 'Importujem...' : 'Importovať' }}
        </button>
        <a :href="'/api/export/csv/?all_actions=true'" target="_blank"
          class="rounded-xl border border-slate-300 bg-white px-6 py-3 text-lg font-bold text-slate-700 transition hover:bg-slate-50">
          Stiahnuť CSV export
        </a>
      </div>

      <!-- Results -->
      <section v-if="results" class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-bold text-slate-900 mb-3">Výsledky importu</h2>
        <div class="space-y-2">
          <div
            v-for="(r, idx) in results"
            :key="idx"
            class="flex items-center gap-3 rounded-lg px-4 py-2 text-sm"
            :class="r.status === 'skipped'
              ? 'bg-amber-50 border border-amber-200 text-amber-800'
              : 'bg-emerald-50 border border-emerald-200 text-emerald-800'"
          >
            <span class="font-bold">{{ r.task_name || '(bez názvu)' }}</span>
            <span class="ml-auto">
              <template v-if="r.status === 'skipped'">Preskočené: {{ r.reason }}</template>
              <template v-else>
                {{ r.status === 'created' ? 'Vytvorené' : 'Aktualizované' }}
                — {{ r.examples_added }} príkladov
              </template>
            </span>
          </div>
        </div>
      </section>

    </div>
  </div>
</template>
