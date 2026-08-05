<!--
================================================================================
 Component: Topics.vue
 Description:
        Displays landing page grade grid / personalized view, plus a searchable
        list of example sets (prikladové sady). Search is case- and
        diacritic-insensitive (Dĺžka = dlzka).
================================================================================
-->

<script setup>
import { useI18n } from 'vue-i18n';
import { onMounted, ref, computed } from 'vue';
import GradeView from '@/components/MainMenu/GradeView.vue';
import PersonalizedGradeHome from '@/components/MainMenu/PersonalizedGradeHome.vue';
import Spinner from '../Spinner.vue';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { browseTasks } from '@/api/apiClient';

const langStore = useLanguageStore();
const { t } = useI18n();
const authStore = useAuthStore();

const allTasks = ref([]);
const tasksLoading = ref(false);
const taskSearch = ref('');

// Strip diacritics and lowercase for comparison
const normalize = s =>
  (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

const filteredTasks = computed(() => {
  const q = normalize(taskSearch.value.trim());
  if (!q) return [];
  return allTasks.value.filter(t => normalize(t.task_name).includes(q));
});

onMounted(async () => {
  tasksLoading.value = true;
  try {
    allTasks.value = await browseTasks() || [];
  } catch (e) {
    allTasks.value = [];
  }
  tasksLoading.value = false;
});
</script>

<template>
  <div>
    <!-- Personalized view for students with a grade set -->
      <PersonalizedGradeHome
        v-if="authStore.isAuthenticated && authStore.role !== 'admin' && authStore.grade"
      />

      <!-- Generic grade grid for guests / students without a grade -->
      <template v-else>
        <div class="flex justify-center pt-10 px-4">
          <h2 class="text-3xl md:text-4xl font-black text-slate-800 dark:text-slate-100 text-center">
            {{ t('selectGrades') }}
          </h2>
        </div>
        <GradeView />
      </template>

      <!-- Task set search — visible to all users -->
      <div class="max-w-5xl mx-auto px-4 pb-16 mt-10">
        <h3 class="text-xl font-black text-slate-700 dark:text-slate-200 mb-4 text-center">
          {{ t('taskSetsTitle') }}
        </h3>

        <!-- Search bar -->
        <div class="flex justify-center mb-5">
          <div class="relative w-full max-w-lg">
            <div class="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none text-slate-400 dark:text-slate-500">
              <i class="fa-solid fa-magnifying-glass"></i>
            </div>
            <input
              v-model="taskSearch"
              type="text"
              :placeholder="t('searchTaskSetsPlaceholder')"
              class="w-full pl-11 pr-4 py-3 rounded-2xl border-[3px] border-slate-200 dark:border-slate-600
                     bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100
                     placeholder-slate-400 dark:placeholder-slate-500
                     focus:outline-none focus:border-violet-400 dark:focus:border-violet-500 transition font-semibold"
            />
          </div>
        </div>

        <!-- Results -->
        <template v-if="taskSearch.trim()">
          <div v-if="tasksLoading" class="flex justify-center py-6">
            <Spinner />
          </div>
          <div v-else-if="filteredTasks.length === 0"
               class="text-center py-8 text-slate-400 dark:text-slate-500 font-medium">
            {{ t('taskSetsNoResults') }}
          </div>
          <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <router-link
              v-for="task in filteredTasks"
              :key="task.task_id"
              :to="{ name: 'taskDetail', params: { taskId: task.task_id } }"
              class="flex flex-col gap-1 p-4 bg-white dark:bg-slate-800 rounded-2xl
                     border-[2px] border-slate-200 dark:border-slate-700
                     border-b-[4px] border-b-slate-300 dark:border-b-slate-600
                     hover:border-violet-400 dark:hover:border-violet-500
                     shadow-sm hover:shadow-md transition-all cursor-pointer"
            >
              <span class="font-bold text-slate-800 dark:text-slate-100 text-sm leading-snug">
                {{ task.task_name }}
              </span>
              <span class="text-xs text-slate-400 dark:text-slate-500">
                {{ task.example_count }}
                {{ t('taskSetsExamples') }}
                <template v-if="task.grade_levels?.length">
                  &middot;
                  {{ task.grade_levels.map(g => g + '.').join(', ') }}
                  {{ t('grade') }}
                </template>
              </span>
            </router-link>
          </div>
        </template>
      </div>
  </div>
</template>
