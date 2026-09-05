<script setup>
import { ref, onMounted, computed } from 'vue';
import { getEngagementStats } from '@/api/apiClient';
import Spinner from '@/components/Spinner.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const stats = ref(null);
const loading = ref(true);
const error = ref(null);

const load = async () => {
  loading.value = true;
  error.value = null;
  try {
    stats.value = await getEngagementStats();
  } catch (e) {
    error.value = String(e);
  }
  loading.value = false;
};

onMounted(load);

const fmt = (iso) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('sk-SK', { dateStyle: 'short', timeStyle: 'short' });
};

const maxDaily = (daily) => Math.max(1, ...daily.map((d) => d.count));

const statusBadgeClass = (s) => ({
  waiting: 'bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300',
  active: 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300',
  question: 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300',
  review: 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300',
  finished: 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400',
}[s] || 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400');

const printTotal = computed(() => stats.value?.print?.total ?? 0);
const towWinnerLabel = (g) => (g.status !== 'finished' ? '—' : g.winner_team ? `${t('duelTeam')} ${g.winner_team}` : t('towDraw'));
</script>

<template>
  <div class="pt-24 px-4 max-w-7xl mx-auto pb-12">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-slate-800 dark:text-slate-100">{{ t('engagementTitle') }}</h1>
      <button @click="load"
              class="px-4 py-1.5 bg-secondary text-white rounded-lg text-sm hover:bg-blue-600">
        {{ t('refresh') }}
      </button>
    </div>

    <Spinner v-if="loading" />
    <p v-else-if="error" class="text-red-500">{{ error }}</p>

    <div v-else class="space-y-8">

      <!-- Summary tiles -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div class="text-xs uppercase text-slate-400 mb-1">{{ t('engagementDuelSection') }}</div>
          <div class="text-3xl font-bold text-slate-800 dark:text-slate-100">{{ stats.duel.total }}</div>
          <div class="text-xs text-slate-400 mt-1">
            {{ t('engagementLast24h') }}: {{ stats.duel.last_24h }} · {{ t('engagementLast7d') }}: {{ stats.duel.last_7d }}
          </div>
        </div>
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div class="text-xs uppercase text-slate-400 mb-1">{{ t('engagementQuizSection') }}</div>
          <div class="text-3xl font-bold text-slate-800 dark:text-slate-100">{{ stats.quiz.total }}</div>
          <div class="text-xs text-slate-400 mt-1">
            {{ t('engagementLast24h') }}: {{ stats.quiz.last_24h }} · {{ t('engagementLast7d') }}: {{ stats.quiz.last_7d }}
          </div>
        </div>
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div class="text-xs uppercase text-slate-400 mb-1">{{ t('engagementPrintSection') }}</div>
          <div class="text-3xl font-bold text-slate-800 dark:text-slate-100">{{ printTotal }}</div>
          <div class="text-xs text-slate-400 mt-1">
            {{ t('engagementLast24h') }}: {{ stats.print.last_24h }} · {{ t('engagementLast7d') }}: {{ stats.print.last_7d }}
          </div>
        </div>
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div class="text-xs uppercase text-slate-400 mb-1">{{ t('engagementTowSection') }}</div>
          <div class="text-3xl font-bold text-slate-800 dark:text-slate-100">{{ stats.tow.total }}</div>
          <div class="text-xs text-slate-400 mt-1">
            {{ t('engagementLast24h') }}: {{ stats.tow.last_24h }} · {{ t('engagementLast7d') }}: {{ stats.tow.last_7d }}
          </div>
        </div>
      </div>

      <!-- Duel -->
      <section class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <h2 class="font-bold text-lg text-slate-800 dark:text-slate-100 mb-3">🪢 {{ t('engagementDuelSection') }}</h2>
        <div class="flex items-end gap-1 h-16 mb-4">
          <div v-for="d in stats.duel.daily" :key="d.date" class="flex-1 flex flex-col items-center justify-end gap-1" :title="`${d.date}: ${d.count}`">
            <div class="w-full bg-secondary/70 rounded-t" :style="{ height: `${(d.count / maxDaily(stats.duel.daily)) * 100}%`, minHeight: d.count ? '2px' : '0' }"></div>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm text-left">
            <thead class="border-b border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400 uppercase">
              <tr>
                <th class="px-3 py-2">{{ t('engagementCreated') }}</th>
                <th class="px-3 py-2">{{ t('engagementCode') }}</th>
                <th class="px-3 py-2">{{ t('engagementMode') }}</th>
                <th class="px-3 py-2">{{ t('engagementStatus') }}</th>
                <th class="px-3 py-2">{{ t('engagementParticipants') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
              <tr v-for="g in stats.duel.recent" :key="g.code">
                <td class="px-3 py-2 whitespace-nowrap text-slate-500 dark:text-slate-400">{{ fmt(g.created_at) }}</td>
                <td class="px-3 py-2 font-mono">{{ g.code }}</td>
                <td class="px-3 py-2">{{ g.mode }}<span v-if="g.vs_bot"> 🤖</span></td>
                <td class="px-3 py-2"><span class="text-xs px-2 py-0.5 rounded-full" :class="statusBadgeClass(g.status)">{{ g.status }}</span></td>
                <td class="px-3 py-2">{{ g.participants.join(', ') || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!stats.duel.recent.length" class="text-center py-6 text-slate-400 text-sm">{{ t('engagementNoData') }}</p>
        </div>
      </section>

      <!-- Quiz -->
      <section class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <h2 class="font-bold text-lg text-slate-800 dark:text-slate-100 mb-3">🎮 {{ t('engagementQuizSection') }}</h2>
        <div class="flex items-end gap-1 h-16 mb-4">
          <div v-for="d in stats.quiz.daily" :key="d.date" class="flex-1 flex flex-col items-center justify-end gap-1" :title="`${d.date}: ${d.count}`">
            <div class="w-full bg-accent/70 rounded-t" :style="{ height: `${(d.count / maxDaily(stats.quiz.daily)) * 100}%`, minHeight: d.count ? '2px' : '0' }"></div>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm text-left">
            <thead class="border-b border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400 uppercase">
              <tr>
                <th class="px-3 py-2">{{ t('engagementCreated') }}</th>
                <th class="px-3 py-2">{{ t('engagementCode') }}</th>
                <th class="px-3 py-2">{{ t('engagementTeacher') }}</th>
                <th class="px-3 py-2">{{ t('engagementStatus') }}</th>
                <th class="px-3 py-2">{{ t('engagementParticipants') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
              <tr v-for="g in stats.quiz.recent" :key="g.code">
                <td class="px-3 py-2 whitespace-nowrap text-slate-500 dark:text-slate-400">{{ fmt(g.created_at) }}</td>
                <td class="px-3 py-2 font-mono">{{ g.code }}</td>
                <td class="px-3 py-2">{{ g.teacher_name || '—' }}</td>
                <td class="px-3 py-2"><span class="text-xs px-2 py-0.5 rounded-full" :class="statusBadgeClass(g.status)">{{ g.status }}</span></td>
                <td class="px-3 py-2">{{ g.participants.join(', ') || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!stats.quiz.recent.length" class="text-center py-6 text-slate-400 text-sm">{{ t('engagementNoData') }}</p>
        </div>
      </section>

      <!-- Print -->
      <section class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <h2 class="font-bold text-lg text-slate-800 dark:text-slate-100 mb-3">🖨️ {{ t('engagementPrintSection') }}</h2>
        <div class="flex items-end gap-1 h-16 mb-4">
          <div v-for="d in stats.print.daily" :key="d.date" class="flex-1 flex flex-col items-center justify-end gap-1" :title="`${d.date}: ${d.count}`">
            <div class="w-full bg-purple-400/70 rounded-t" :style="{ height: `${(d.count / maxDaily(stats.print.daily)) * 100}%`, minHeight: d.count ? '2px' : '0' }"></div>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm text-left">
            <thead class="border-b border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400 uppercase">
              <tr>
                <th class="px-3 py-2">{{ t('engagementCreated') }}</th>
                <th class="px-3 py-2">{{ t('engagementKind') }}</th>
                <th class="px-3 py-2">{{ t('engagementTeacher') }}</th>
                <th class="px-3 py-2">{{ t('engagementItems') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
              <tr v-for="p in stats.print.recent" :key="`${p.created_at}-${p.kind}`">
                <td class="px-3 py-2 whitespace-nowrap text-slate-500 dark:text-slate-400">{{ fmt(p.created_at) }}</td>
                <td class="px-3 py-2">{{ p.kind === 'teacher' ? t('printKindTeacher') : t('printKindParent') }}</td>
                <td class="px-3 py-2">{{ p.teacher_name || '—' }}</td>
                <td class="px-3 py-2">{{ p.item_count }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!stats.print.recent.length" class="text-center py-6 text-slate-400 text-sm">{{ t('engagementNoData') }}</p>
        </div>
      </section>

      <!-- Tug of War -->
      <section class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <h2 class="font-bold text-lg text-slate-800 dark:text-slate-100 mb-3">🪢 {{ t('engagementTowSection') }}</h2>
        <div class="flex items-end gap-1 h-16 mb-4">
          <div v-for="d in stats.tow.daily" :key="d.date" class="flex-1 flex flex-col items-center justify-end gap-1" :title="`${d.date}: ${d.count}`">
            <div class="w-full bg-green-500/70 rounded-t" :style="{ height: `${(d.count / maxDaily(stats.tow.daily)) * 100}%`, minHeight: d.count ? '2px' : '0' }"></div>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm text-left">
            <thead class="border-b border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400 uppercase">
              <tr>
                <th class="px-3 py-2">{{ t('engagementCreated') }}</th>
                <th class="px-3 py-2">{{ t('engagementCode') }}</th>
                <th class="px-3 py-2">{{ t('engagementTeacher') }}</th>
                <th class="px-3 py-2">{{ t('engagementMode') }}</th>
                <th class="px-3 py-2">{{ t('engagementStatus') }}</th>
                <th class="px-3 py-2">{{ t('engagementParticipants') }}</th>
                <th class="px-3 py-2">{{ t('engagementTowWinner') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
              <tr v-for="g in stats.tow.recent" :key="g.code">
                <td class="px-3 py-2 whitespace-nowrap text-slate-500 dark:text-slate-400">{{ fmt(g.created_at) }}</td>
                <td class="px-3 py-2 font-mono">{{ g.code }}</td>
                <td class="px-3 py-2">{{ g.teacher_name || '—' }}</td>
                <td class="px-3 py-2">{{ g.end_mode === 'time' ? t('towEndModeTime') : t('towEndModeTarget') }}</td>
                <td class="px-3 py-2"><span class="text-xs px-2 py-0.5 rounded-full" :class="statusBadgeClass(g.status)">{{ g.status }}</span></td>
                <td class="px-3 py-2">A: {{ g.team_a_count }} · B: {{ g.team_b_count }}</td>
                <td class="px-3 py-2">{{ towWinnerLabel(g) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!stats.tow.recent.length" class="text-center py-6 text-slate-400 text-sm">{{ t('engagementNoData') }}</p>
        </div>
      </section>

    </div>
  </div>
</template>
