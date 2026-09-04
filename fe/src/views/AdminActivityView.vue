<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { getRecentActivity } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const activity = ref([]);
const loading = ref(true);
const error = ref(null);
const limit = ref(100);

const load = async () => {
  loading.value = true;
  error.value = null;
  try {
    activity.value = await getRecentActivity(limit.value);
  } catch (e) {
    error.value = String(e);
  }
  loading.value = false;
};

onMounted(load);

const fmt = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('sk-SK', { dateStyle: 'short', timeStyle: 'medium' });
};

const actionLabel = (a) => ({
  evaluated: t('evaluatedLabel'),
  skipped: t('skipped'),
  terminated: t('terminatedLabel'),
  no_match: t('noMatchLabel'),
  error: t('errorStatusLabel'),
}[a] || a);

const actionClass = (row) => {
  if (row.action !== 'evaluated') return 'text-slate-400';
  return row.is_correct ? 'text-green-600 dark:text-green-400 font-semibold' : 'text-red-500 dark:text-red-400';
};
</script>

<template>
  <div class="pt-24 px-4 max-w-7xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100">{{ t('activityAnalyticsTitle') }}</h1>
      <div class="flex items-center gap-3">
        <RouterLink to="/analytics/engagement"
                class="px-4 py-1.5 bg-accent text-white rounded-lg text-sm hover:opacity-90 whitespace-nowrap">
          🪢🎮🖨️ {{ t('navEngagement') }}
        </RouterLink>
        <select v-model="limit" @change="load"
                class="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-600
                       bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-sm">
          <option :value="50">{{ t('activityLast50') }}</option>
          <option :value="100">{{ t('activityLast100') }}</option>
          <option :value="200">{{ t('activityLast200') }}</option>
          <option :value="500">{{ t('activityLast500') }}</option>
        </select>
        <button @click="load"
                class="px-4 py-1.5 bg-secondary text-white rounded-lg text-sm hover:bg-blue-600">
          {{ t('refresh') }}
        </button>
      </div>
    </div>

    <Spinner v-if="loading" />
    <p v-else-if="error" class="text-red-500">{{ error }}</p>

    <div v-else class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-x-auto">
      <table class="w-full text-sm text-left">
        <thead class="border-b border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400 uppercase">
          <tr>
            <th class="px-4 py-3">{{ t('colTime') }}</th>
            <th class="px-4 py-3">{{ t('colUser') }}</th>
            <th class="px-4 py-3">{{ t('colType') }}</th>
            <th class="px-4 py-3">{{ t('colExample') }}</th>
            <th class="px-4 py-3">{{ t('colResult') }}</th>
            <th class="px-4 py-3">{{ t('colSource') }}</th>
            <th class="px-4 py-3">{{ t('colTimeMs') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
          <tr v-for="row in activity" :key="row.id"
              class="hover:bg-slate-50 dark:hover:bg-slate-700/30">
            <td class="px-4 py-2 whitespace-nowrap text-slate-500 dark:text-slate-400">{{ fmt(row.created_at) }}</td>
            <td class="px-4 py-2 font-medium text-slate-800 dark:text-slate-100">{{ row.user_label }}</td>
            <td class="px-4 py-2">
              <span :class="row.user_type === 'student'
                ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'"
                    class="text-xs px-2 py-0.5 rounded-full">
                {{ row.user_type === 'student' ? t('studentOption') : t('anonymousBadge') }}
              </span>
            </td>
            <td class="px-4 py-2 text-slate-700 dark:text-slate-300 max-w-xs truncate">{{ row.example_text || '—' }}</td>
            <td class="px-4 py-2" :class="actionClass(row)">
              {{ row.action === 'evaluated' ? (row.is_correct ? `✓ ${t('correctLabel')}` : `✗ ${t('incorrectLabel')}`) : actionLabel(row.action) }}
            </td>
            <td class="px-4 py-2 text-slate-500 dark:text-slate-400">{{ row.source }}</td>
            <td class="px-4 py-2 text-slate-500 dark:text-slate-400">{{ row.duration ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="activity.length === 0" class="text-center py-8 text-slate-400">{{ t('noActivityYet') }}</p>
    </div>
  </div>
</template>
