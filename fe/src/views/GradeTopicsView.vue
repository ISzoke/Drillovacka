<!--
================================================================================
 Component: GradeTopicsView.vue
 Description:
      Displays tasks available for a specific grade level.
================================================================================
-->

<script setup>
import { useI18n } from 'vue-i18n';
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { getGradeLevels, getTasksByGrade } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import ExampleRequestSheet from '@/components/ExampleRequestSheet.vue';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { getTaskName } from '@/utils/contentNameMaps';

const router = useRouter();
const route = useRoute();
const langStore = useLanguageStore();
const { t } = useI18n();
const authStore = useAuthStore();

const gradeInfo = ref(null);
const tasks = ref([]);
const loading = ref(true);
const requestSheetOpen = ref(false);

onMounted(async () => {
  try {
    const storedGrade = sessionStorage.getItem('selectedGrade');
    if (storedGrade) {
      const parsedGrade = JSON.parse(storedGrade);
      if (parsedGrade && parsedGrade.id != null) gradeInfo.value = parsedGrade;
    }

    if (!gradeInfo.value) {
      const gradeId = Number(route.params.gradeId);
      const allGrades = await getGradeLevels();
      const normalized = Array.isArray(allGrades)
        ? allGrades.map(g => ({ id: Number(g?.id ?? g?.grade ?? g), grade: Number(g?.grade ?? g?.id ?? g) }))
        : [];
      gradeInfo.value = normalized.find(g => g.id === gradeId) || { id: gradeId, grade: gradeId };
    }

    tasks.value = await getTasksByGrade(gradeInfo.value.id, authStore.id || null);
  } catch (error) {
    console.error('Error fetching grade tasks:', error);
  } finally {
    loading.value = false;
  }
});

const goBack = () => router.push({ name: 'home' });

const openTaskExamples = (task) => {
  router.push({ name: 'taskDetail', params: { taskId: String(task.id) } });
};
</script>

<template>
  <div class="min-h-screen">
    <Spinner v-if="loading" class="pt-48" />

    <div v-else class="max-w-5xl mx-auto px-4 pt-8 pb-16">

      <!-- Header -->
      <div class="flex items-center mb-8">
        <button
          @click="goBack"
          class="flex items-center gap-2 text-slate-500 dark:text-slate-400 hover:text-violet-600 dark:hover:text-violet-400
                 transition font-black text-sm bg-slate-100 dark:bg-slate-800 px-4 py-2 rounded-2xl
                 border-2 border-slate-200 dark:border-slate-700 border-b-[4px] border-b-slate-300 dark:border-b-slate-600
                 hover:-translate-y-0.5 active:translate-y-1 active:border-b-[2px] flex-shrink-0"
        >
          <i class="fa-solid fa-arrow-left"></i>
          {{ t('back') }}
        </button>

        <h1 class="flex-1 text-2xl md:text-4xl font-black text-slate-800 dark:text-slate-100 text-center">
          {{ gradeInfo?.grade }}. {{ t('grade') }}
        </h1>

        <div class="w-16 md:w-20 flex-shrink-0"></div>
      </div>

      <!-- Tasks grid -->
      <div v-if="tasks.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <template v-for="task in tasks" :key="task.id">

          <!-- Private / AI-generated task -->
          <button
            v-if="task.is_private"
            @click="openTaskExamples(task)"
            class="text-left cursor-pointer rounded-3xl border-[3px] border-violet-300 dark:border-violet-600
                   border-b-[8px] border-b-violet-400 dark:border-b-violet-700
                   bg-violet-50 dark:bg-violet-900/20 p-5
                   hover:-translate-y-1 active:translate-y-1 active:border-b-[3px] transition-all shadow-sm"
          >
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xs font-black px-2 py-0.5 rounded-full bg-violet-200 dark:bg-violet-800 text-violet-700 dark:text-violet-300">
                {{ t('aiGeneratedBadge') }}
              </span>
            </div>
            <div class="text-xl font-black text-violet-800 dark:text-violet-200 break-words">{{ getTaskName(task.name, langStore.language) }}</div>
            <div class="mt-2 text-sm font-bold text-violet-400 dark:text-violet-500">{{ task.example_count }} {{ t('examplesCountPrivate') }}</div>
          </button>

          <!-- Public task -->
          <button
            v-else
            @click="openTaskExamples(task)"
            class="text-left cursor-pointer rounded-3xl border-[3px] border-slate-200 dark:border-slate-700
                   border-b-[8px] border-b-slate-300 dark:border-b-slate-600
                   bg-white dark:bg-slate-800 p-5
                   hover:-translate-y-1 active:translate-y-1 active:border-b-[3px] transition-all shadow-sm"
          >
            <div class="flex items-center gap-2 mb-1" v-if="task.generated_batch_id">
              <span class="text-xs font-black px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
                {{ t('aiGeneratedBadge') }}
              </span>
            </div>
            <div class="text-xl font-black text-slate-800 dark:text-slate-100 break-words">{{ getTaskName(task.name, langStore.language) }}</div>
            <div class="mt-2 text-sm font-bold text-slate-400 dark:text-slate-500">{{ task.example_count }} {{ t('examplesCount') }}</div>
          </button>

        </template>
      </div>

      <div v-else class="text-center py-20">
        <p class="text-xl font-bold text-slate-400 dark:text-slate-500">
          {{ t('noTasksForGrade') }}
        </p>
      </div>

      <!-- "Want more examples?" text link -->
      <div class="text-center mt-8">
        <button
          @click="requestSheetOpen = true"
          class="text-sm font-semibold text-slate-400 dark:text-slate-500 hover:text-violet-500 transition underline underline-offset-2"
        >
          {{ t('requestMoreExamples') }}
        </button>
      </div>

    </div>
  </div>

  <ExampleRequestSheet
    :open="requestSheetOpen"
    :grade="gradeInfo?.grade ?? null"
    @close="requestSheetOpen = false"
  />
</template>
