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
import { getGradeLevels, getTasksByGrade } from '@/api/apiClient';
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
const manualTasks = ref([]);
const loading = ref(true);

onMounted(async () => {
  try {
    // Get grade info from sessionStorage
    const storedGrade = sessionStorage.getItem('selectedGrade');
    if (storedGrade) {
      const parsedGrade = JSON.parse(storedGrade);
      if (parsedGrade && parsedGrade.id != null) {
        gradeInfo.value = parsedGrade;
      }
    }

    if (!gradeInfo.value) {
      // Fallback: fetch from params
      const gradeId = Number(route.params.gradeId);
      const allGrades = await getGradeLevels();
      const normalizedGrades = Array.isArray(allGrades)
        ? allGrades.map((grade) => ({
            id: Number(grade?.id ?? grade?.grade ?? grade),
            grade: Number(grade?.grade ?? grade?.id ?? grade),
          }))
        : [];
      gradeInfo.value = normalizedGrades.find((grade) => grade.id === gradeId) || {
        id: gradeId,
        grade: gradeId,
      };
    }

    // Fetch skills for this grade
    const [skillsResponse, taskResponse] = await Promise.all([
      apiClient.get(`skills/by-grade/${gradeInfo.value.id}/`),
      getTasksByGrade(gradeInfo.value.id),
    ]);
    skills.value = skillsResponse.data;
    manualTasks.value = taskResponse;

  } catch (error) {
    console.error('Error fetching grade skills:', error);
  } finally {
    loading.value = false;
  }
});

const goBack = () => {
  router.push({ name: 'home' });
};

const openTaskExamples = (task) => {
  router.push({
    name: 'examples',
    query: {
      task_id: String(task.id),
      task_name: task.name,
    },
  });
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

      <div v-if="manualTasks.length > 0" class="py-4">
        <h2 class="text-2xl font-bold text-primary text-center mb-6">
          Ručne priradené sady
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <button
            v-for="task in manualTasks"
            :key="task.id"
            @click="openTaskExamples(task)"
            class="text-left cursor-pointer border border-gray-300 rounded-lg shadow-lg bg-white p-5 transition transform hover:shadow-xl hover:bg-secondary hover:border-secondary group"
          >
            <div class="text-2xl font-bold text-primary transition duration-300 group-hover:text-white break-words">
              {{ task.name }}
            </div>
            <div class="mt-3 text-sm text-slate-600 group-hover:text-slate-100">
              {{ task.example_count }} príkladov
            </div>
          </button>
        </div>
      </div>

      <!-- No skills/tasks message -->
      <div v-if="skills.length === 0 && manualTasks.length === 0" class="text-center py-20">
        <p class="text-xl text-gray-600">
          {{ dictionary[langStore.language].noSkillsForGrade }}
        </p>
      </div>

    </div>

  </div>
</template>
