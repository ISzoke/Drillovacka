<!--
================================================================================
 Component: GradeView.vue
 Description:
        Displays skills organized by grade levels (1-9).
================================================================================
-->

<script setup>
import { ref, onMounted } from 'vue';
import { getGradeLevels } from '@/api/apiClient';
import { useRouter } from 'vue-router';
import Spinner from '../Spinner.vue';
import RegistrationPromptModal from '../RegistrationPromptModal.vue';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { dictionary } from '@/utils/dictionary';

const router = useRouter();
const langStore = useLanguageStore();
const authStore = useAuthStore();

const gradeLevels = ref([]);
const loading = ref(true);

const showRegPrompt = ref(false);
const pendingGradeId = ref(null);
const pendingGradeNumber = ref(null);

// Solid colored backgrounds (used for the card body)
const GRADE_COLORS = [
  { card: 'bg-violet-600',  border: 'border-violet-700',  borderB: 'border-b-violet-800',  icon: 'fa-solid fa-star' },
  { card: 'bg-emerald-600', border: 'border-emerald-700', borderB: 'border-b-emerald-800', icon: 'fa-solid fa-pencil' },
  { card: 'bg-sky-600',     border: 'border-sky-700',     borderB: 'border-b-sky-800',     icon: 'fa-solid fa-ruler-combined' },
  { card: 'bg-amber-600',   border: 'border-amber-700',   borderB: 'border-b-amber-800',   icon: 'fa-solid fa-calculator' },
  { card: 'bg-orange-600',  border: 'border-orange-700',  borderB: 'border-b-orange-800',  icon: 'fa-solid fa-bolt' },
  { card: 'bg-rose-600',    border: 'border-rose-700',    borderB: 'border-b-rose-800',    icon: 'fa-solid fa-fire' },
  { card: 'bg-teal-600',    border: 'border-teal-700',    borderB: 'border-b-teal-800',    icon: 'fa-solid fa-bullseye' },
  { card: 'bg-indigo-600',  border: 'border-indigo-700',  borderB: 'border-b-indigo-800',  icon: 'fa-solid fa-trophy' },
  { card: 'bg-pink-600',    border: 'border-pink-700',    borderB: 'border-b-pink-800',    icon: 'fa-solid fa-crown' },
]

// Subtle dot pattern overlay (SVG data URI)
const dotPattern = `url("data:image/svg+xml,%3Csvg width='20' height='20' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='2' cy='2' r='2' fill='rgba(255,255,255,0.18)'/%3E%3C/svg%3E")`

function colorOf(grade) {
  return GRADE_COLORS[(grade.grade - 1) % GRADE_COLORS.length]
}

function normalizeGradeLevels(items) {
  if (!Array.isArray(items)) return [];
  return items
    .map((item, index) => {
      if (item && typeof item === 'object') {
        const rawId = item.id ?? item.grade_id ?? item.pk ?? item.grade;
        const rawGrade = item.grade ?? item.grade_number ?? item.number ?? item.id;
        const id = Number(rawId);
        const grade = Number(rawGrade);
        if (Number.isFinite(id) && Number.isFinite(grade)) return { id, grade };
      }
      const numeric = Number(item);
      if (Number.isFinite(numeric)) return { id: numeric, grade: numeric };
      const fallback = index + 1;
      return { id: fallback, grade: fallback };
    })
    .filter(item => Number.isFinite(item.id) && Number.isFinite(item.grade))
    .sort((a, b) => a.grade - b.grade);
}

onMounted(async () => {
  try {
    const fetchedGradeLevels = await getGradeLevels();
    gradeLevels.value = normalizeGradeLevels(fetchedGradeLevels);
  } catch (error) {
    console.error('Error fetching grade levels:', error);
  } finally {
    loading.value = false;
  }
});

const doNavigate = (gradeId, gradeNumber) => {
  sessionStorage.setItem('selectedGrade', JSON.stringify({
    id: Number(gradeId),
    grade: Number.isFinite(Number(gradeNumber)) ? Number(gradeNumber) : Number(gradeId),
  }));
  router.push({ name: 'gradeTopics', params: { gradeId: String(gradeId) } });
};

const selectGrade = (gradeId, gradeNumber) => {
  if (!Number.isFinite(Number(gradeId))) {
    console.error('Missing or invalid gradeId:', gradeId, gradeNumber);
    return;
  }
  // Show registration prompt for anonymous users (only if not dismissed before)
  if (!authStore.isAuthenticated && !localStorage.getItem('regPromptDismissed')) {
    pendingGradeId.value = gradeId;
    pendingGradeNumber.value = gradeNumber;
    showRegPrompt.value = true;
    return;
  }
  doNavigate(gradeId, gradeNumber);
};

const onPromptSkip = () => {
  showRegPrompt.value = false;
  doNavigate(pendingGradeId.value, pendingGradeNumber.value);
};

const onPromptRegister = () => {
  showRegPrompt.value = false;
};
</script>

<template>
  <div>
    <RegistrationPromptModal
      v-if="showRegPrompt"
      @skip="onPromptSkip"
      @register="onPromptRegister"
    />
    <Spinner v-if="loading" class="pt-48" />

    <div v-else-if="gradeLevels.length === 0" class="flex justify-center py-16 px-4">
      <div class="w-full max-w-xl rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] bg-white dark:bg-slate-800 p-8 text-center">
        <h2 class="text-2xl font-black text-slate-800 dark:text-slate-100">Ročníky zatiaľ nie sú nastavené</h2>
        <p class="mt-3 text-slate-500 dark:text-slate-400">
          Databáza je v čistom stave po migráciách. Keď budú ročníky znovu pripravené, zobrazia sa tu automaticky.
        </p>
      </div>
    </div>

    <!-- Grade Levels Grid -->
    <div v-else class="flex justify-center py-8 md:py-12 px-4">
      <div class="w-full max-w-3xl grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-4 md:gap-5">
        <div
          v-for="grade in gradeLevels"
          :key="grade.id"
          @click="selectGrade(grade.id, grade.grade)"
          class="cursor-pointer rounded-3xl border-[3px] border-b-[8px]
                 transition-all hover:-translate-y-1 active:translate-y-1 active:border-b-[3px]
                 flex flex-col items-center justify-center py-7 px-3 text-white select-none"
          :class="[colorOf(grade).card, colorOf(grade).border, colorOf(grade).borderB]"
          :style="{ backgroundImage: dotPattern }"
        >
          <i :class="colorOf(grade).icon" class="text-3xl mb-3 opacity-80"></i>
          <div class="text-5xl font-black leading-none">{{ grade.grade }}.</div>
          <div class="text-sm font-bold mt-2 opacity-80 uppercase tracking-wider">
            {{ dictionary[langStore.language].grade }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
