<!--
================================================================================
 Component: GradeView.vue
 Description:
        Displays skills organized by grade levels (1-9).
 Author: Martin Eugen Minarčík (xminarm00)
================================================================================
-->

<script setup>
import { ref, onMounted } from 'vue';
import { getGradeLevels } from '@/api/apiClient';
import { useRouter } from 'vue-router';
import Spinner from '../Spinner.vue';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { dictionary } from '@/utils/dictionary';

const router = useRouter();
const langStore = useLanguageStore();

const gradeLevels = ref([]);
const loading = ref(true);

function normalizeGradeLevels(items) {
  if (!Array.isArray(items)) return [];

  return items
    .map((item, index) => {
      if (item && typeof item === 'object') {
        const rawId = item.id ?? item.grade_id ?? item.pk ?? item.grade;
        const rawGrade = item.grade ?? item.grade_number ?? item.number ?? item.id;
        const id = Number(rawId);
        const grade = Number(rawGrade);

        if (Number.isFinite(id) && Number.isFinite(grade)) {
          return { id, grade };
        }
      }

      const numeric = Number(item);
      if (Number.isFinite(numeric)) {
        return { id: numeric, grade: numeric };
      }

      const fallback = index + 1;
      return { id: fallback, grade: fallback };
    })
    .filter((item) => Number.isFinite(item.id) && Number.isFinite(item.grade))
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

// Navigate to topic view for specific grade
const selectGrade = (gradeId, gradeNumber) => {
  if (!Number.isFinite(Number(gradeId))) {
    console.error('Missing or invalid gradeId:', gradeId, gradeNumber);
    return;
  }

  // Store grade info in sessionStorage for TopicView to use
  sessionStorage.setItem('selectedGrade', JSON.stringify({
    id: Number(gradeId),
    grade: Number.isFinite(Number(gradeNumber)) ? Number(gradeNumber) : Number(gradeId),
  }));
  router.push({ name: 'gradeTopics', params: { gradeId: String(gradeId) } });
};
</script>

<template>
  <div>
    <Spinner v-if="loading" class="pt-48" />

    <div v-else-if="gradeLevels.length === 0" class="flex justify-center py-16 px-4">
      <div class="w-full max-w-xl rounded-2xl border border-gray-200 bg-white/90 p-8 text-center shadow-lg">
        <h2 class="text-2xl font-bold text-primary">Ročníky zatiaľ nie sú nastavené</h2>
        <p class="mt-3 text-gray-600">
          Databáza je v čistom stave po migráciách. Keď budú ročníky znovu pripravené, zobrazia sa tu automaticky.
        </p>
      </div>
    </div>

    <!-- Grade Levels Grid -->
    <div v-else class="flex justify-center py-8 md:py-12 px-4">
      <div class="w-full max-w-7xl grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 md:gap-6">
        
        <div 
          v-for="grade in gradeLevels" 
          :key="grade.id"
          @click="selectGrade(grade.id, grade.grade)"
          class="cursor-pointer border border-gray-300 rounded-xl shadow-lg bg-white 
                 transition transform hover:shadow-xl hover:scale-[1.03]
                 hover:bg-secondary hover:border-secondary
                 flex flex-col items-center justify-center min-h-[150px] md:min-h-[180px] p-5 md:p-7
                 duration-300 ease-in-out group"
        >
          <!-- Grade Number -->
          <div class="text-4xl md:text-6xl font-bold text-primary group-hover:text-white mb-2 leading-none">
            {{ grade.grade }}.
          </div>
          
          <!-- Grade Label -->
          <div class="text-base md:text-xl font-semibold text-gray-700 group-hover:text-white text-center">
            {{ dictionary[langStore.language].grade }}
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
/* Additional hover effects */
</style>
