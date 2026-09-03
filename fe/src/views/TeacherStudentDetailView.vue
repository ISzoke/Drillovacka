<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '@/stores/useAuthStore';
import {
  getClassroomStudentDetail,
  getStudentAiInsight,
  generateStudentAiInsight,
  getStudentAttempts,
} from '@/api/apiClient';
import { useI18n } from 'vue-i18n';
import { useToastStore } from '@/stores/useToastStore';
import Spinner from '@/components/Spinner.vue';

const props = defineProps({
  classroomId: [String, Number],
  studentId: [String, Number],
});

const authStore = useAuthStore();
const toastStore = useToastStore();
const { t } = useI18n();
const data = ref(null);
const loading = ref(true);

const insight = ref(null);
const insightLoading = ref(false);

// Full attempt log (paginated). null = show data.recent_attempts only.
const allAttempts = ref(null);
const attemptsFilter = ref('all');      // all | wrong | correct
const attemptsLoading = ref(false);
const attemptsTotal = ref(0);
const PAGE = 100;

const shownAttempts = computed(() => allAttempts.value ?? (data.value?.recent_attempts || []));

const loadAttempts = async (reset = true) => {
  attemptsLoading.value = true;
  try {
    const offset = reset ? 0 : (allAttempts.value?.length || 0);
    const res = await getStudentAttempts(props.classroomId, props.studentId, authStore.id, {
      only: attemptsFilter.value, limit: PAGE, offset,
    });
    allAttempts.value = reset ? res.results : [...(allAttempts.value || []), ...res.results];
    attemptsTotal.value = res.count;
  } catch (e) {
    toastStore.addToast({ message: t('errorLoadingGeneric'), type: 'error', visible: true });
  }
  attemptsLoading.value = false;
};

const setFilter = (f) => { attemptsFilter.value = f; loadAttempts(true); };
const collapseAttempts = () => { allAttempts.value = null; attemptsFilter.value = 'all'; };

const fetchData = async () => {
  loading.value = true;
  try {
    data.value = await getClassroomStudentDetail(props.classroomId, props.studentId, authStore.id);
  } catch (e) {
    console.error('Error fetching student detail:', e);
  }
  loading.value = false;
};

const fetchInsight = async () => {
  try {
    const res = await getStudentAiInsight(props.classroomId, props.studentId, authStore.id);
    insight.value = res.insight || null;
  } catch (e) {
    console.error('Error fetching AI insight:', e);
  }
};

const runInsight = async () => {
  insightLoading.value = true;
  try {
    const res = await generateStudentAiInsight(props.classroomId, props.studentId, authStore.id);
    insight.value = res.insight || null;
  } catch (e) {
    toastStore.addToast({ message: t('aiInsightError'), type: 'error', visible: true });
  }
  insightLoading.value = false;
};

const fmtDate = (d) => (d ? new Date(d).toLocaleString('sk-SK', { dateStyle: 'short', timeStyle: 'short' }) : '');

const fmtTime = (ms) => {
  if (!ms) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

onMounted(() => { fetchData(); fetchInsight(); });
</script>

<template>
  <div class="pt-24 px-4 max-w-4xl mx-auto">
    <Spinner v-if="loading" />

    <template v-else-if="data">
      <!-- Breadcrumb -->
      <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-4">
        <router-link :to="{ name: 'teacher-dashboard' }" class="hover:underline text-secondary">
          {{ t('dashboard') }}
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
            <span v-if="data.student.grade">{{ data.student.grade }}. {{ t('grade') }} &nbsp;&middot;&nbsp;</span>
            {{ t('level') }} {{ data.student.level }} &nbsp;&middot;&nbsp;
            {{ data.student.total_xp }} XP
          </p>
        </div>
      </div>

      <!-- Stats row -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 text-center">
          <div class="text-2xl font-bold text-secondary">{{ data.stats.examples_practiced }}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ t('examplesCount') }}</div>
        </div>
        <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 text-center">
          <div class="text-2xl font-bold text-green-600">{{ data.stats.accuracy }}%</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ t('accuracy') }}</div>
        </div>
        <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 text-center">
          <div class="text-2xl font-bold text-amber-500">{{ data.stats.avg_mastery }}%</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ t('mastery') }}</div>
        </div>
        <div class="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 text-center">
          <div class="text-2xl font-bold text-purple-500">{{ data.stats.streak_days }}</div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ t('streakDays') }}</div>
        </div>
      </div>

      <!-- Task progress -->
      <div v-if="data.task_progress?.length" class="mb-8">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">{{ t('assignedTasks') }}</h2>
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 dark:border-slate-700 text-gray-500 dark:text-gray-400 text-xs">
                <th class="py-2 px-4 text-left">{{ t('taskColumnLabel') }}</th>
                <th class="py-2 px-4 text-right">{{ t('correctSuffix') }}</th>
                <th class="py-2 px-4 text-right">{{ t('incorrectLabel') }}</th>
                <th class="py-2 px-4 text-right">{{ t('avgTimeShort') }}</th>
                <th class="py-2 px-4 text-right">{{ t('completionLabel') }}</th>
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

      <!-- Problem examples for this student -->
      <div v-if="data.weak_examples?.length" class="mb-8">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">{{ t('weakExamplesHeading') }}</h2>
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 dark:border-slate-700 text-gray-500 dark:text-gray-400 text-xs">
                <th class="py-2 px-4 text-left">{{ t('exampleLabel') }}</th>
                <th class="py-2 px-4 text-left">{{ t('colCorrectAnswer') }}</th>
                <th class="py-2 px-4 text-right">{{ t('correctSuffix') }}</th>
                <th class="py-2 px-4 text-right">{{ t('accuracy') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="w in data.weak_examples" :key="w.example_id"
                  class="border-b border-slate-100 dark:border-slate-700/50 last:border-0">
                <td class="py-2.5 px-4 font-mono text-slate-700 dark:text-slate-300">{{ w.question }}</td>
                <td class="py-2.5 px-4 font-mono text-green-600 dark:text-green-400">{{ w.correct_answer || '—' }}</td>
                <td class="py-2.5 px-4 text-right text-slate-500 dark:text-slate-400">{{ w.solved }}/{{ w.attempts }}</td>
                <td class="py-2.5 px-4 text-right font-medium"
                    :class="w.accuracy >= 50 ? 'text-amber-500' : 'text-red-500 dark:text-red-400'">
                  {{ w.accuracy }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Skill mastery -->
      <div v-if="data.skill_mastery?.length" class="mb-8">
        <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-100 mb-3">{{ t('skillMasteryHeading') }}</h2>
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-200 dark:border-slate-700 text-gray-500 dark:text-gray-400 text-xs">
                <th class="py-2 px-4 text-left">{{ t('skillLabel') }}</th>
                <th class="py-2 px-4 text-right">{{ t('mastery') }}</th>
                <th class="py-2 px-4 text-right">{{ t('examplesCount') }}</th>
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

      <!-- AI insight -->
      <div class="mb-8">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-100">{{ t('aiInsightHeading') }}</h2>
          <button v-if="insight" @click="runInsight" :disabled="insightLoading"
                  class="text-xs px-3 py-1 rounded border border-slate-300 dark:border-slate-600
                         text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50">
            {{ t('aiInsightRegenerate') }}
          </button>
        </div>

        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
          <div v-if="insightLoading" class="flex items-center gap-3 text-sm text-gray-500 py-4">
            <Spinner /> {{ t('aiInsightLoading') }}
          </div>

          <div v-else-if="!insight" class="text-center py-6">
            <p class="text-sm text-gray-400 mb-3">{{ t('aiInsightEmpty') }}</p>
            <button @click="runInsight"
                    class="px-4 py-2 bg-secondary text-white rounded-lg hover:bg-blue-600 font-semibold text-sm">
              ✨ {{ t('aiInsightGenerate') }}
            </button>
          </div>

          <div v-else class="space-y-4 text-sm">
            <div v-if="insight.payload.strengths?.length">
              <div class="font-semibold text-green-600 dark:text-green-400 mb-1">{{ t('aiInsightStrengths') }}</div>
              <ul class="space-y-1">
                <li v-for="(s, i) in insight.payload.strengths" :key="'s' + i"
                    class="text-slate-700 dark:text-slate-300">✓ {{ s }}</li>
              </ul>
            </div>

            <div v-if="insight.payload.mistake_patterns?.length">
              <div class="font-semibold text-red-500 dark:text-red-400 mb-1">{{ t('aiInsightMistakes') }}</div>
              <div v-for="(m, i) in insight.payload.mistake_patterns" :key="'m' + i" class="mb-2">
                <div class="text-slate-700 dark:text-slate-300">{{ m.pattern }}</div>
                <div v-if="m.examples?.length" class="flex flex-wrap gap-1 mt-1">
                  <span v-for="(ex, j) in m.examples" :key="j"
                        class="text-xs font-mono bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300
                               px-1.5 py-0.5 rounded">{{ ex }}</span>
                </div>
              </div>
            </div>

            <div v-if="insight.payload.recommendations?.length">
              <div class="font-semibold text-secondary dark:text-tertiary mb-1">{{ t('aiInsightRecommendations') }}</div>
              <ol class="list-decimal list-inside space-y-1">
                <li v-for="(r, i) in insight.payload.recommendations" :key="'r' + i"
                    class="text-slate-700 dark:text-slate-300">{{ r }}</li>
              </ol>
            </div>

            <div class="text-[11px] text-gray-400 pt-1">
              {{ t('aiInsightGeneratedAt', { date: fmtDate(insight.generated_at) }) }}
              <span v-if="insight.source_attempts"> · {{ t('aiInsightSourceAttempts', { n: insight.source_attempts }) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Attempts -->
      <div v-if="data.recent_attempts?.length || allAttempts">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h2 class="text-lg font-semibold text-slate-800 dark:text-slate-100">
            {{ allAttempts ? t('allAttemptsHeading') : t('recentAttempts') }}
            <span class="text-sm font-normal text-gray-400">({{ allAttempts ? attemptsTotal : data.total_attempts }})</span>
          </h2>
          <div class="flex items-center gap-1.5">
            <template v-if="allAttempts">
              <button v-for="f in ['all', 'wrong', 'correct']" :key="f" @click="setFilter(f)"
                      :class="['text-xs px-2.5 py-1 rounded-full border transition-colors',
                               attemptsFilter === f
                                 ? 'border-secondary text-secondary bg-secondary/10'
                                 : 'border-slate-300 dark:border-slate-600 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700']">
                {{ f === 'all' ? t('filterAll') : f === 'wrong' ? t('filterWrongOnly') : t('filterCorrectOnly') }}
              </button>
              <button @click="collapseAttempts"
                      class="text-xs px-2.5 py-1 rounded-full border border-slate-300 dark:border-slate-600 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700">
                {{ t('collapseAction') }}
              </button>
            </template>
            <button v-else @click="loadAttempts(true)" :disabled="attemptsLoading"
                    class="text-xs px-3 py-1 rounded border border-secondary text-secondary hover:bg-secondary/10 disabled:opacity-50">
              {{ t('showAllAttempts', { n: data.total_attempts }) }}
            </button>
          </div>
        </div>

        <div v-if="attemptsLoading && !shownAttempts.length" class="flex justify-center py-6"><Spinner /></div>

        <div v-else class="space-y-2">
          <div v-for="a in shownAttempts" :key="a.id"
               class="flex flex-wrap items-center gap-x-3 gap-y-2 p-3 bg-white dark:bg-slate-800 rounded-lg
                      border-l-4 border border-slate-200 dark:border-slate-700"
               :class="a.is_correct ? 'border-l-green-400' : a.is_correct === false ? 'border-l-red-400' : 'border-l-slate-300'">
            <span class="text-base font-bold w-4 flex-shrink-0 text-center"
                  :class="a.is_correct ? 'text-green-500' : a.is_correct === false ? 'text-red-400' : 'text-gray-400'">
              {{ a.is_correct ? '✓' : a.is_correct === false ? '✗' : '–' }}
            </span>

            <span class="font-mono text-base font-semibold text-slate-800 dark:text-slate-100 min-w-[4.5rem]">
              {{ a.example_text }}
            </span>

            <span class="flex items-baseline gap-1.5 px-2 py-0.5 rounded"
                  :class="a.is_correct ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'">
              <span class="text-[10px] uppercase tracking-wide text-gray-400">{{ t('attemptYourAnswer') }}</span>
              <span class="font-mono font-bold"
                    :class="a.is_correct ? 'text-green-700 dark:text-green-400' : 'text-red-600 dark:text-red-400'">
                {{ a.typed || '—' }}
              </span>
            </span>

            <span class="flex items-baseline gap-1.5 px-2 py-0.5 rounded bg-slate-50 dark:bg-slate-700/40">
              <span class="text-[10px] uppercase tracking-wide text-gray-400">{{ t('colCorrectAnswer') }}</span>
              <span class="font-mono font-bold text-slate-700 dark:text-slate-200">{{ a.correct_answer || '—' }}</span>
            </span>

            <span class="flex items-baseline gap-1.5">
              <span class="text-[10px] uppercase tracking-wide text-gray-400">{{ t('attemptLabel') }}</span>
              <span class="text-sm font-semibold text-slate-600 dark:text-slate-300">{{ a.attempt_number }}</span>
            </span>

            <span class="ml-auto text-xs text-gray-400 whitespace-nowrap">
              {{ new Date(a.created_at).toLocaleDateString('sk-SK') }}
            </span>
          </div>

          <div v-if="allAttempts && allAttempts.length < attemptsTotal" class="pt-2 text-center">
            <button @click="loadAttempts(false)" :disabled="attemptsLoading"
                    class="text-xs px-4 py-1.5 rounded border border-slate-300 dark:border-slate-600 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50">
              {{ attemptsLoading ? t('downloadingEllipsis') : t('loadMore') }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="!data.task_progress?.length && !data.skill_mastery?.length && !data.recent_attempts?.length"
           class="text-center py-12 text-gray-400">
        {{ t('noActivityYet') }}
      </div>
    </template>

    <div v-else-if="!loading" class="text-center py-16 text-gray-400">
      {{ t('studentNotFound') }}
    </div>
  </div>
</template>
