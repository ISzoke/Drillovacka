<!--
================================================================================
 View: MyGeneratedBatchesView.vue
 Description:
        Shows the logged-in student's generated example batches.
        Allows navigating to practice each set, completing the survey, and deleting.
        Route: /moje-priklady
================================================================================
-->

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/useAuthStore'
import { getMyGeneratedBatches, deleteGeneratedBatch } from '@/api/apiClient'

const { t } = useI18n()
const router = useRouter()
const auth   = useAuthStore()

const batches = ref([])
const loading = ref(true)
const error   = ref('')
const deleting = ref(null)

const STATUS_LABEL = computed(() => ({
  preview:        t('statusPendingEvaluation'),
  survey_done:    t('statusEvaluated'),
  pending_review: t('statusPendingApproval'),
  approved:       t('statusApproved'),
  rejected:       t('statusRejected'),
}))
const STATUS_COLOR = {
  preview:        'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
  survey_done:    'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
  pending_review: 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300',
  approved:       'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
  rejected:       'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
}

onMounted(async () => {
  if (!auth.id) { router.push({ name: 'home' }); return }
  try {
    batches.value = await getMyGeneratedBatches({ student_id: auth.id })
  } catch {
    error.value = t('loadExamplesFailedMessage')
  } finally {
    loading.value = false
  }
})

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('sk-SK', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

// Batch older than 1 day in 'preview' state → needs evaluation warning
function isOverdue(batch) {
  if (batch.status !== 'preview') return false
  const created = new Date(batch.created_at)
  return (Date.now() - created.getTime()) > 24 * 60 * 60 * 1000
}

async function remove(batch) {
  if (!confirm(t('confirmDeleteBatchMessage'))) return
  deleting.value = batch.id
  try {
    await deleteGeneratedBatch(batch.id, auth.id)
    batches.value = batches.value.filter(b => b.id !== batch.id)
  } catch {
    alert(t('deleteBatchFailedMessage'))
  } finally {
    deleting.value = null
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900 px-4 py-8">
    <div class="max-w-2xl mx-auto">

      <!-- Header -->
      <div class="mb-6">
        <button @click="router.back()" class="text-slate-400 hover:text-slate-600 text-sm font-bold mb-3 block">← {{ t('back') }}</button>
        <h1 class="text-3xl font-black text-slate-800 dark:text-slate-100">{{ t('myGeneratedExamplesTitle') }}</h1>
        <p class="text-slate-400 dark:text-slate-500 text-sm mt-1">{{ t('myGeneratedExamplesSubtitle') }}</p>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-slate-400 text-center py-12">{{ t('loadingEllipsis') }}</div>
      <div v-else-if="error" class="text-red-500 text-center py-12">{{ error }}</div>

      <!-- Empty -->
      <div v-else-if="!batches.length" class="text-center py-16 text-slate-400 dark:text-slate-500">
        <div class="text-5xl mb-4">🤖</div>
        <p class="font-bold text-lg">{{ t('noGeneratedExamplesYet') }}</p>
        <p class="text-sm mt-2">{{ t('noBatchesHint') }}</p>
      </div>

      <!-- Batch list -->
      <div v-else class="space-y-4">
        <div
          v-for="b in batches"
          :key="b.id"
          class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-600 p-5 shadow-sm"
          :class="{ 'border-amber-400 dark:border-amber-500': isOverdue(b) }"
        >
          <!-- Overdue warning -->
          <div v-if="isOverdue(b)" class="mb-3 px-3 py-2 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 text-xs text-amber-700 dark:text-amber-400 font-semibold">
            {{ t('overdueBatchWarning') }}
          </div>

          <!-- Top row -->
          <div class="flex items-start justify-between gap-3 mb-3">
            <div class="flex-1 min-w-0">
              <p class="font-black text-slate-800 dark:text-slate-100 text-lg leading-tight truncate">
                {{ b.raw_json?.task_name || t('generatedTaskFallbackName') }}
              </p>
              <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{{ formatDate(b.created_at) }} · {{ b.grade }}. {{ t('grade') }}</p>
            </div>
            <span
              class="flex-shrink-0 text-xs font-bold px-2.5 py-1 rounded-full"
              :class="STATUS_COLOR[b.status] || STATUS_COLOR.preview"
            >
              {{ STATUS_LABEL[b.status] || b.status }}
            </span>
          </div>

          <!-- Description -->
          <p class="text-sm text-slate-500 dark:text-slate-400 italic mb-3 line-clamp-2">„{{ b.description }}"</p>

          <!-- Examples count + type -->
          <p class="text-xs text-slate-400 dark:text-slate-500 mb-3">
            {{ b.raw_json?.examples?.length || 0 }} {{ t('taskSetsExamples') }}
          </p>

          <!-- Actions -->
          <div class="flex gap-2">
            <button
              v-if="b.created_task_id"
              @click="router.push({ name: 'examples', query: { task_id: b.created_task_id, batch_id: b.id } })"
              class="flex-1 py-2 rounded-xl font-black text-xs text-white
                     bg-emerald-500 border-[3px] border-emerald-600 border-b-[4px] border-b-emerald-700
                     hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-[3px] transition-all"
            >
              🎮 {{ b.status === 'preview' ? t('practiceAndEvaluateButton') : t('practiceButton') }}
            </button>
            <span v-else class="flex-1 py-2 text-center text-xs text-slate-400">{{ t('examplesUnavailableLabel') }}</span>
            <button
              @click="remove(b)"
              :disabled="deleting === b.id"
              class="px-3 py-2 rounded-xl font-black text-xs
                     bg-red-50 dark:bg-red-900/20 border-[3px] border-red-200 dark:border-red-700
                     text-red-500 dark:text-red-400
                     hover:bg-red-100 dark:hover:bg-red-900/40 transition-all
                     disabled:opacity-40"
            >
              🗑
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
