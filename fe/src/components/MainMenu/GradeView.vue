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
const expandedGrade = ref(null);

onMounted(async () => {
  try {
    gradeLevels.value = await getGradeLevels();
  } catch (error) {
    console.error('Error fetching grade levels:', error);
  } finally {
    loading.value = false;
  }
});

// Toggle expanded grade
const toggleGrade = (gradeId) => {
  if (expandedGrade.value === gradeId) {
    expandedGrade.value = null;
  } else {
    expandedGrade.value = gradeId;
  }
};

// Navigate to topic view for specific grade
const selectGrade = (gradeId, gradeNumber) => {
  // Store grade info in sessionStorage for TopicView to use
  sessionStorage.setItem('selectedGrade', JSON.stringify({ id: gradeId, grade: gradeNumber }));
  router.push({ name: 'gradeTopics', params: { gradeId: gradeId } });
};
</script>

<template>
  <div>
    <Spinner v-if="loading" class="pt-48" />

    <!-- Grade Levels Grid -->
    <div v-else class="flex justify-center py-20">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl px-4">
        
        <div 
          v-for="grade in gradeLevels" 
          :key="grade.id"
          @click="selectGrade(grade.id, grade.grade)"
          class="cursor-pointer border border-gray-300 rounded-lg shadow-lg bg-white 
                 transition transform hover:shadow-xl hover:scale-105
                 hover:bg-secondary hover:border-secondary
                 flex flex-col items-center justify-center p-8
                 duration-300 ease-in-out group"
        >
          <!-- Grade Number -->
          <div class="text-6xl font-bold text-primary group-hover:text-white mb-2">
            {{ grade.grade }}.
          </div>
          
          <!-- Grade Label -->
          <div class="text-xl font-semibold text-gray-700 group-hover:text-white">
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
