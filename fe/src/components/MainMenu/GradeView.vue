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

onMounted(async () => {
  try {
    gradeLevels.value = await getGradeLevels();
  } catch (error) {
    console.error('Error fetching grade levels:', error);
  } finally {
    loading.value = false;
  }
});

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
