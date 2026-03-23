<!--
================================================================================
 View: PracticeGeneratedView.vue
 Redirect: /prakticovat/:batchId → /examples?task_id=X&batch_id=Y
================================================================================
-->
<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/useAuthStore'
import { getMyGeneratedBatches } from '@/api/apiClient'

const route  = useRoute()
const router = useRouter()
const auth   = useAuthStore()

onMounted(async () => {
  if (!auth.id) { router.replace({ name: 'home' }); return }
  try {
    const batches = await getMyGeneratedBatches({ student_id: auth.id })
    const batch = batches.find(b => b.id === Number(route.params.batchId))
    if (batch?.created_task_id) {
      router.replace({ name: 'examples', query: { task_id: batch.created_task_id, batch_id: batch.id } })
    } else {
      router.replace({ name: 'my-generated-batches' })
    }
  } catch {
    router.replace({ name: 'my-generated-batches' })
  }
})
</script>
<template><div class="min-h-screen flex items-center justify-center text-slate-400">Načítavam…</div></template>
