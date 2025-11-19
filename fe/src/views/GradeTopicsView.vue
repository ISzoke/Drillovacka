<!--
================================================================================
 Component: GradeTopicsView.vue
 Description:
      Displays skills available for a specific grade level.
 Author: Martin Eugen Minarčík (xminarm00)
================================================================================
-->

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { getGradeLevels } from '@/api/apiClient';
import apiClient from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import TopicCard from '@/components/MainMenu/TopicCard.vue';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { dictionary } from '@/utils/dictionary';

const router = useRouter();
const route = useRoute();
const langStore = useLanguageStore();

const gradeInfo = ref(null);
const skills = ref([]);
const loading = ref(true);

onMounted(async () => {
  try {
    // Get grade info from sessionStorage
    const storedGrade = sessionStorage.getItem('selectedGrade');
    if (storedGrade) {
      gradeInfo.value = JSON.parse(storedGrade);
    } else {
      // Fallback: fetch from params
      const gradeId = route.params.gradeId;
      const allGrades = await getGradeLevels();
      gradeInfo.value = allGrades.find(g => g.id == gradeId);
    }

    // Fetch skills for this grade
    const response = await apiClient.get(`skills/by-grade/${gradeInfo.value.id}/`);
    skills.value = response.data;

  } catch (error) {
    console.error('Error fetching grade skills:', error);
  } finally {
    loading.value = false;
  }
});

const goBack = () => {
  router.push({ name: 'home' });
};
</script>

<template>
  <div class="flex flex-col items-center min-h-screen">
    
    <Spinner v-if="loading" class="pt-48" />

    <div v-else class="w-full max-w-6xl px-4">
      
      <!-- Header with back button -->
      <div class="flex items-center justify-between pt-10 pb-6">
        <button 
          @click="goBack"
          class="flex items-center gap-2 text-primary hover:text-secondary transition font-semibold"
        >
          <i class="fa-solid fa-arrow-left"></i>
          {{ dictionary[langStore.language].back }}
        </button>

        <h1 class="text-4xl font-bold text-primary text-center flex-grow">
          {{ gradeInfo?.grade }}. 
          {{ dictionary[langStore.language].grade }}
        </h1>

        <div class="w-20"></div> <!-- Spacer for centering -->
      </div>

      <!-- Skills Grid -->
      <div v-if="skills.length > 0" class="flex justify-center py-10">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-20 gap-y-10">
          <TopicCard 
            v-for="skill in skills" 
            :key="skill.id" 
            :topic="skill.name" 
            :id="Number(skill.id)"
          />
        </div>
      </div>

      <!-- No skills message -->
      <div v-else class="text-center py-20">
        <p class="text-xl text-gray-600">
          {{ dictionary[langStore.language].noSkillsForGrade }}
        </p>
      </div>

    </div>

  </div>
</template>
