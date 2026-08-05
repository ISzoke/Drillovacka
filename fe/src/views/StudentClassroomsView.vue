<script setup>
import { useI18n } from 'vue-i18n';
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRouter } from 'vue-router';
import { getStudentClassrooms } from '@/api/apiClient';
import { useLanguageStore } from '@/stores/useLanguageStore';
import Spinner from '@/components/Spinner.vue';

const authStore = useAuthStore();
const router = useRouter();
const langStore = useLanguageStore();
const { t } = useI18n();

const classrooms = ref([]);
const loading = ref(true);

// Cycle through a few accent colors for classroom cards
const cardColors = [
  { bg: 'bg-secondary/10 dark:bg-secondary/20', icon: 'bg-secondary/20 dark:bg-secondary/30', text: 'text-secondary' },
  { bg: 'bg-tertiary/20 dark:bg-tertiary/10', icon: 'bg-tertiary/30 dark:bg-tertiary/20', text: 'text-teal-600 dark:text-teal-400' },
  { bg: 'bg-amber-50 dark:bg-amber-900/20', icon: 'bg-amber-100 dark:bg-amber-800/40', text: 'text-amber-600 dark:text-amber-400' },
  { bg: 'bg-violet-50 dark:bg-violet-900/20', icon: 'bg-violet-100 dark:bg-violet-800/40', text: 'text-violet-600 dark:text-violet-400' },
];

const fetchClassrooms = async () => {
  loading.value = true;
  try {
    classrooms.value = await getStudentClassrooms(authStore.id);
  } catch (e) {
    console.error('Error fetching classrooms:', e);
  }
  loading.value = false;
};

onMounted(fetchClassrooms);
</script>

<template>
  <div class="pt-20 px-4 max-w-4xl mx-auto pb-12">

    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold text-primary dark:text-white">
          {{ t('myClassrooms') || 'Moje triedy' }}
        </h1>
        <p v-if="!loading && classrooms.length > 0" class="text-sm text-gray-400 mt-1">
          {{ classrooms.length }} {{ classrooms.length === 1 ? (t('classroom') || 'trieda') : (t('classrooms') || 'tried') }}
        </p>
      </div>
      <router-link
        to="/join"
        class="flex items-center gap-2 px-4 py-2.5 bg-secondary text-white rounded-2xl
               font-semibold text-sm border-b-4 border-blue-700
               hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all"
      >
        <span class="text-lg leading-none">+</span>
        {{ t('joinClassroom') || 'Pridať sa' }}
      </router-link>
    </div>

    <Spinner v-if="loading" />

    <!-- Empty state -->
    <div v-else-if="classrooms.length === 0"
         class="text-center py-16 rounded-3xl border-2 border-dashed
                border-slate-200 dark:border-slate-700">
      <div class="text-5xl mb-4">🏫</div>
      <p class="text-gray-500 dark:text-gray-400 text-lg font-medium mb-1">
        {{ t('noClassroomsYet') || 'Nie si v žiadnej triede.' }}
      </p>
      <p class="text-gray-400 dark:text-gray-500 text-sm mb-6">
        {{ t('askTeacherForCode') || 'Požiadaj učiteľa o kód triedy.' }}
      </p>
      <router-link
        to="/join"
        class="inline-flex items-center gap-2 px-6 py-3 bg-secondary text-white rounded-2xl
               font-semibold border-b-4 border-blue-700
               hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2 transition-all"
      >
        {{ t('joinClassroom') || 'Pridať sa do triedy' }}
      </router-link>
    </div>

    <!-- Classroom cards -->
    <div v-else class="grid gap-4 sm:grid-cols-2">
      <router-link
        v-for="(c, i) in classrooms"
        :key="c.id"
        :to="{ name: 'student-classroom-detail', params: { classroomId: c.id } }"
        class="block rounded-3xl border-2 border-slate-200 dark:border-slate-700
               border-b-[8px] border-b-slate-300 dark:border-b-slate-600
               bg-white dark:bg-slate-800
               hover:-translate-y-1 active:translate-y-1 active:border-b-2 transition-all p-5"
      >
        <!-- Top row: icon + homework badge -->
        <div class="flex items-start justify-between mb-4">
          <div :class="['w-12 h-12 rounded-2xl flex items-center justify-center text-2xl flex-shrink-0',
                        cardColors[i % cardColors.length].icon]">
            🏫
          </div>
          <span v-if="c.homework_count > 0"
                class="text-xs bg-amber-100 dark:bg-amber-900/60 text-amber-700 dark:text-amber-300
                       px-2.5 py-1 rounded-full font-semibold border border-amber-200 dark:border-amber-700">
            📝 {{ c.homework_count }} {{ t('homeworkAbbrev') }}
          </span>
        </div>

        <!-- Name + description -->
        <h2 class="text-lg font-bold text-primary dark:text-white mb-0.5 leading-tight">
          {{ c.name }}
        </h2>
        <p v-if="c.description" class="text-sm text-gray-500 dark:text-gray-400 mb-3 line-clamp-1">
          {{ c.description }}
        </p>

        <!-- Footer -->
        <div class="flex items-center justify-between text-xs text-gray-400 mt-3 pt-3
                    border-t border-slate-100 dark:border-slate-700">
          <span class="flex items-center gap-1">
            👤 {{ c.teacher_name }}
          </span>
          <span :class="['font-semibold', cardColors[i % cardColors.length].text]">
            {{ c.task_count }} {{ t('tasks') || 'úloh' }}
          </span>
        </div>
      </router-link>
    </div>

  </div>
</template>
