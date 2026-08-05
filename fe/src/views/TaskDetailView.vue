<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { getTaskName } from '@/utils/contentNameMaps';
import { getTask, getTaskStats, getTaskHistory } from '@/api/apiClient';
import { useAuthStore } from '@/stores/useAuthStore';
import Spinner from '@/components/Spinner.vue';
import VueApexCharts from 'vue3-apexcharts';

const route = useRoute();
const router = useRouter();
const langStore = useLanguageStore();
const authStore = useAuthStore();
const { t } = useI18n();

const task = ref(null);
const stats = ref(null);
const history = ref([]);
const loading = ref(true);

const taskId = Number(route.params.taskId);

onMounted(async () => {
  try {
    const studentId = authStore.id;
    [task.value, stats.value, history.value] = await Promise.all([
      getTask(taskId),
      getTaskStats(taskId, studentId),
      getTaskHistory(taskId, studentId),
    ]);
  } catch (e) {
    console.error('Failed to load task:', e);
  } finally {
    loading.value = false;
  }
});

const displayName = computed(() =>
  task.value ? getTaskName(task.value.name, langStore.language) : ''
);

const fmtTime = (ms) => {
  if (!ms) return '—';
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(1)} s`;
  return `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`;
};

const startExamples = () => {
  if (!task.value) return;
  const query = { task_id: String(task.value.id), task_name: task.value.name };
  if (task.value.is_private && task.value.generated_batch_id) {
    query.batch_id = String(task.value.generated_batch_id);
  }
  router.push({ name: 'examples', query });
};

const goBack = () => router.back();

const MEDALS = ['🥇', '🥈', '🥉'];

const isDark = computed(() => document.documentElement.classList.contains('dark'));

const chartOptions = computed(() => ({
  chart: {
    type: 'line',
    toolbar: { show: false },
    background: 'transparent',
    fontFamily: 'inherit',
  },
  colors: ['#7c3aed', '#10b981'],
  stroke: { curve: 'smooth', width: [3, 3] },
  markers: { size: 5, hover: { size: 7 } },
  xaxis: {
    categories: history.value.map(h => h.label),
    labels: {
      style: { colors: isDark.value ? '#94a3b8' : '#64748b', fontSize: '11px' },
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: [
    {
      title: { text: t('timeSecondsAxisLabel'), style: { color: '#7c3aed', fontSize: '11px', fontWeight: 700 } },
      labels: {
        formatter: v => v == null ? '—' : `${v}s`,
        style: { colors: '#7c3aed', fontSize: '11px' },
      },
      min: 0,
    },
    {
      opposite: true,
      title: { text: t('masteryPercentAxisLabel'), style: { color: '#10b981', fontSize: '11px', fontWeight: 700 } },
      labels: {
        formatter: v => `${v}%`,
        style: { colors: '#10b981', fontSize: '11px' },
      },
      min: 0,
      max: 100,
    },
  ],
  tooltip: {
    theme: isDark.value ? 'dark' : 'light',
    y: [
      { formatter: v => v == null ? '—' : `${v} s` },
      { formatter: v => `${v}%` },
    ],
  },
  legend: {
    labels: { colors: isDark.value ? '#cbd5e1' : '#475569' },
  },
  grid: {
    borderColor: isDark.value ? '#1e293b' : '#e2e8f0',
    strokeDashArray: 4,
  },
}));

const chartSeries = computed(() => [
  {
    name: t('yourAvgTimeSeriesLabel'),
    data: history.value.map(h => h.avg_time != null ? Math.round(h.avg_time / 1000) : null),
  },
  {
    name: t('yourMasterySeriesLabel'),
    data: history.value.map(h => h.mastery),
  },
]);
</script>

<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-950">
    <Spinner v-if="loading" class="pt-48" />

    <div v-else-if="!task" class="flex flex-col items-center justify-center min-h-screen text-slate-400 dark:text-slate-500">
      <p class="text-lg font-semibold">{{ t('taskNotFound') }}</p>
      <button @click="goBack" class="mt-4 text-violet-600 underline font-bold">{{ t('back') }}</button>
    </div>

    <div v-else class="max-w-2xl mx-auto px-4 pt-10 pb-24">

      <!-- Back -->
      <button @click="goBack"
        class="flex items-center gap-2 text-slate-500 dark:text-slate-400 hover:text-violet-600 dark:hover:text-violet-400
               transition font-black text-sm bg-slate-100 dark:bg-slate-800 px-4 py-2 rounded-2xl
               border-2 border-slate-200 dark:border-slate-700 border-b-[4px] border-b-slate-300 dark:border-b-slate-600
               hover:-translate-y-0.5 active:translate-y-1 active:border-b-[2px] mb-8"
      >
        ← {{ t('back') }}
      </button>

      <!-- Task header -->
      <div class="rounded-3xl border-[3px] border-b-[8px] p-6 mb-4"
           :class="task.is_private
             ? 'border-violet-300 dark:border-violet-600 border-b-violet-400 dark:border-b-violet-700 bg-violet-50 dark:bg-violet-900/20'
             : 'border-slate-200 dark:border-slate-700 border-b-slate-300 dark:border-b-slate-600 bg-white dark:bg-slate-800'">
        <div v-if="task.is_private"
             class="text-xs font-black px-2 py-0.5 rounded-full bg-violet-200 dark:bg-violet-800 text-violet-700 dark:text-violet-300 inline-block mb-3">
          {{ t('aiGeneratedBadge') }}
        </div>
        <h1 class="text-2xl md:text-3xl font-black break-words mb-1"
            :class="task.is_private ? 'text-violet-800 dark:text-violet-200' : 'text-slate-800 dark:text-slate-100'">
          {{ displayName }}
        </h1>
        <p class="text-sm font-bold"
           :class="task.is_private ? 'text-violet-400 dark:text-violet-500' : 'text-slate-400 dark:text-slate-500'">
          {{ task.example_count }} {{ t('examplesCount') }}
        </p>
      </div>

      <!-- Start button -->
      <button @click="startExamples"
        class="w-full py-4 rounded-3xl text-xl font-black text-white mb-8
               bg-violet-600 hover:bg-violet-700 dark:bg-violet-700 dark:hover:bg-violet-600
               border-b-[6px] border-violet-800 hover:-translate-y-0.5 active:translate-y-1 active:border-b-[2px]
               transition-all shadow-md">
        {{ t('startExerciseButton') }} →
      </button>

      <div v-if="stats">

        <!-- My stats -->
        <div v-if="stats.my_stats && stats.my_stats.total_attempted > 0"
             class="bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700 p-5 mb-4">
          <h2 class="text-base font-black text-slate-700 dark:text-slate-200 mb-4">{{ t('yourResults') }}</h2>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-slate-50 dark:bg-slate-900 rounded-2xl p-3 text-center">
              <div class="text-2xl font-black text-violet-600 dark:text-violet-400">{{ stats.my_stats.solved }}</div>
              <div class="text-xs font-bold text-slate-500 dark:text-slate-400 mt-0.5">{{ t('solvedExamplesLabel') }}</div>
            </div>
            <div class="bg-slate-50 dark:bg-slate-900 rounded-2xl p-3 text-center">
              <div class="text-2xl font-black"
                   :class="stats.my_stats.success_rate >= 70 ? 'text-green-600 dark:text-green-400' : stats.my_stats.success_rate >= 50 ? 'text-amber-500' : 'text-red-500'">
                {{ stats.my_stats.success_rate }}%
              </div>
              <div class="text-xs font-bold text-slate-500 dark:text-slate-400 mt-0.5">{{ t('successRateLabel') }}</div>
            </div>
            <div class="bg-slate-50 dark:bg-slate-900 rounded-2xl p-3 text-center">
              <div class="text-2xl font-black text-blue-600 dark:text-blue-400">{{ fmtTime(stats.my_stats.avg_time) }}</div>
              <div class="text-xs font-bold text-slate-500 dark:text-slate-400 mt-0.5">{{ t('yourAvgTimePerExample') }}</div>
            </div>
            <div class="bg-slate-50 dark:bg-slate-900 rounded-2xl p-3 text-center">
              <div class="text-2xl font-black text-emerald-600 dark:text-emerald-400">{{ stats.my_stats.mastery }}%</div>
              <div class="text-xs font-bold text-slate-500 dark:text-slate-400 mt-0.5">
                {{ t('mastery') }}
                <span class="text-slate-400">({{ stats.my_stats.total_examples }} {{ t('examplesAbbrev') }})</span>
              </div>
            </div>
          </div>

          <!-- Global avg comparison -->
          <div v-if="stats.global_avg_time"
               class="mt-3 text-xs font-semibold text-slate-400 dark:text-slate-500 text-center">
            {{ t('avgTimeAllLabel') }} {{ fmtTime(stats.global_avg_time) }}
          </div>
        </div>

        <!-- Global avg (when no personal stats yet) -->
        <div v-else-if="stats.global_avg_time"
             class="bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700 p-4 mb-4 text-center">
          <div class="text-xs font-bold text-slate-400 dark:text-slate-500 mb-1">{{ t('avgTimePerExampleAllLabel') }}</div>
          <div class="text-xl font-black text-blue-600 dark:text-blue-400">{{ fmtTime(stats.global_avg_time) }}</div>
        </div>

        <!-- Leaderboard -->
        <div v-if="stats.leaderboard && stats.leaderboard.length > 0"
             class="bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700 p-5 mb-4">
          <h2 class="text-base font-black text-slate-700 dark:text-slate-200 mb-4">{{ t('leaderboard') }}</h2>
          <div class="flex flex-col gap-2">
            <div v-for="(entry, i) in stats.leaderboard" :key="i"
                 class="flex items-center justify-between rounded-2xl px-4 py-3"
                 :class="i === 0 ? 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700'
                               : 'bg-slate-50 dark:bg-slate-900'">
              <div class="flex items-center gap-3">
                <span class="text-xl">{{ MEDALS[i] }}</span>
                <span class="font-black text-slate-800 dark:text-slate-100">{{ entry.username }}</span>
              </div>
              <div class="text-right">
                <div class="text-sm font-black text-violet-600 dark:text-violet-400">{{ entry.solved }} {{ t('examplesAbbrev') }}</div>
                <div class="text-xs font-bold text-slate-400">{{ entry.success_rate }}% {{ t('successRateLabel') }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- No stats at all -->
        <div v-if="!stats.global_avg_time && (!stats.leaderboard || stats.leaderboard.length === 0) && (!stats.my_stats || stats.my_stats.total_attempted === 0)"
             class="rounded-3xl border-2 border-dashed border-slate-200 dark:border-slate-700 p-6 text-center text-slate-400 dark:text-slate-600">
          <p class="font-bold text-sm">{{ t('noStatsYetBeFirst') }}</p>
        </div>

      </div>

      <!-- Progress chart -->
      <div v-if="history.length >= 2"
           class="bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700 p-5 mt-4">
        <div class="flex items-baseline gap-2 mb-4">
          <h2 class="text-base font-black text-slate-700 dark:text-slate-200">{{ t('yourProgressHeading') }}</h2>
          <span class="text-xs text-slate-400 dark:text-slate-500 font-semibold">{{ t('onlyYourDataBySession') }}</span>
        </div>
        <VueApexCharts
          type="line"
          height="220"
          :options="chartOptions"
          :series="chartSeries"
        />
      </div>

    </div>
  </div>
</template>
