<script setup>
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import { getClassroomStudentDetail } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({
  classroomId: [String, Number],
  studentId: [String, Number],
});

const authStore = useAuthStore();
const data = ref(null);
const loading = ref(true);

const fetchData = async () => {
  loading.value = true;
  try {
    data.value = await getClassroomStudentDetail(props.classroomId, props.studentId, authStore.id);
  } catch (e) {
    console.error('Error fetching student detail:', e);
  }
  loading.value = false;
};

const fmtTime = (ms) => {
  if (!ms) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

onMounted(fetchData);
</script>

<template>
  <div class="pt-24 px-4 max-w-4xl mx-auto">
    <Spinner v-if="loading" />

    <template v-else-if="data">
      <!-- Breadcrumb -->
      <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-4">
        <router-link :to="{ name: 'teacher-dashboard' }" class="hover:underline text-secondary">
          Dashboard
        </router-link>
        <span>&rsaquo;</span>
        <router-link :to="{ name: 'teacher-classroom', params: { classroomId } }" class="hover:underline text-secondary">
          {{ data.classroom_name }}
        </router-link>
        <span>&rsaquo;</span>
        <span>{{ data.student.username }}</span>
      </div>

      <!-- Header -->
      <div class="flex items-center gap-4 mb-8">
        <div class="w-16 h-16 rounded-full bg-secondary/20 flex items-center justify-center text-2xl font-bold text-secondary">
          {{ data.student.username[0]?.toUpperCase() }}
        </div>
        <div>
          <h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100">{{ data.student.username }}</h1>
          <p class="text-gray-500 dark:text-gray-400 text-sm">
            <span v-if="data.student.grade">{{ data.student.grade }}. ročník &nbsp;&middot;&nbsp;</span>
            Level {{ data.student.level }} &nbsp;&middot;&nbsp;
            {{ data.student.total_xp }} XP
          </p>
        </div>
      </div>

      <!-- Stats row -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 text-center">
          <div class="text-2xl font-bold text-secondary">{{ data.stats.examples_practiced }}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Príkladov</div>
        </div>
        <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 text-center">
          <div class="text-2xl font-bold text-green-600">{{ data.stats.accuracy }}%</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Úspešnosť</div>
        </div>
        <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 text-center">
          <div class="text-2xl font-bold text-amber-500">{{ data.stats.avg_mastery }}%</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Zvládnutie</div>
        </div>
        <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 text-center">
          <div class="text-2xl font-bold text-purple-500">{{ data.stats.streak_days }}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Séria dní</div>
        </div>
      </div>

      <!-- Task progress -->
      <div v-if="data.task_progress?.length" class="mb-8">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Priradené úlohy</h2>
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 dark:border-slate-700 text-gray-500 dark:text-gray-400 text-xs">
                <th class="py-2 px-4 text-left">Úloha</th>
                <th class="py-2 px-4 text-right">Spravne</th>
                <th class="py-2 px-4 text-right">Nesprávne</th>
                <th class="py-2 px-4 text-right">Ø čas</th>
                <th class="py-2 px-4 text-right">Dokončenie</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in data.task_progress" :key="t.task_id"
                  class="border-b border-slate-100 dark:border-slate-700/50 last:border-0">
                <td class="py-3 px-4 text-slate-700 dark:text-slate-300 font-medium">{{ t.task_name }}</td>
                <td class="py-3 px-4 text-right text-green-600 dark:text-green-400 font-medium">{{ t.correct }}</td>
                <td class="py-3 px-4 text-right text-red-500 dark:text-red-400">{{ t.incorrect }}</td>
                <td class="py-3 px-4 text-right text-slate-500 dark:text-slate-400">{{ fmtTime(t.avg_time_ms) }}</td>
                <td class="py-3 px-4 text-right">
                  <span :class="t.completion >= 100 ? 'text-green-600' : t.completion > 0 ? 'text-amber-500' : 'text-gray-400'"
                        class="font-medium">
                    {{ t.completion }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Skill mastery -->
      <div v-if="data.skill_mastery?.length" class="mb-8">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Zvládnutie zručností</h2>
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 dark:border-slate-700 text-gray-500 dark:text-gray-400 text-xs">
                <th class="py-2 px-4 text-left">Zručnosť</th>
                <th class="py-2 px-4 text-right">Zvládnutie</th>
                <th class="py-2 px-4 text-right">Príkladov</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="sm in data.skill_mastery" :key="sm.skill_id"
                  class="border-b border-slate-100 dark:border-slate-700/50 last:border-0">
                <td class="py-3 px-4 text-slate-700 dark:text-slate-300">{{ sm.skill_name }}</td>
                <td class="py-3 px-4 text-right">
                  <div class="flex items-center justify-end gap-2">
                    <div class="w-20 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
                      <div class="h-1.5 rounded-full"
                           :class="sm.mastery >= 80 ? 'bg-green-500' : sm.mastery >= 50 ? 'bg-amber-400' : 'bg-red-400'"
                           :style="{ width: sm.mastery + '%' }"></div>
                    </div>
                    <span class="text-xs text-gray-600 dark:text-gray-400 w-8 text-right">{{ sm.mastery }}%</span>
                  </div>
                </td>
                <td class="py-3 px-4 text-right text-slate-600 dark:text-slate-400">{{ sm.examples_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Recent attempts -->
      <div v-if="data.recent_attempts?.length">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">Posledné pokusy</h2>
        <div class="space-y-2">
          <div v-for="a in data.recent_attempts" :key="a.id"
               class="flex items-center justify-between p-3 bg-white dark:bg-slate-800 rounded-lg
                      border border-slate-200 dark:border-slate-700">
            <div class="flex items-center gap-3">
              <span :class="a.is_correct ? 'text-green-500' : 'text-red-400'" class="text-lg font-bold">
                {{ a.is_correct ? '✓' : '✗' }}
              </span>
              <div>
                <div class="text-sm text-slate-700 dark:text-slate-300">{{ a.example_text }}</div>
                <div class="text-xs text-gray-400">{{ a.transcription }}</div>
              </div>
            </div>
            <div class="text-xs text-gray-400 whitespace-nowrap">
              {{ new Date(a.created_at).toLocaleDateString('sk-SK') }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="!data.task_progress?.length && !data.skill_mastery?.length && !data.recent_attempts?.length"
           class="text-center py-12 text-gray-400">
        Žiadna aktivita zatiaľ.
      </div>
    </template>

    <div v-else-if="!loading" class="text-center py-16 text-gray-400">
      Študent nenájdený.
    </div>
  </div>
</template>
