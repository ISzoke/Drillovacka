<!--
================================================================================
 Component: PersonalizedGradeHome.vue
 Description:
        Shown when the student has a grade set. Displays their own grade's
        topics front-and-centre. Two action buttons open bottom-sheet pickers
        for lower grades ("Základy") and higher grades ("Výzva").
================================================================================
-->

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/useAuthStore'
import { getGradeLevels, getTasksByGrade } from '@/api/apiClient'
import apiClient from '@/api/apiClient'
import TopicCard from '@/components/MainMenu/TopicCard.vue'
import Spinner from '@/components/Spinner.vue'

const authStore = useAuthStore()
const router = useRouter()

const allGrades   = ref([])   // [{id, grade}]
const skills      = ref([])
const manualTasks = ref([])
const loading     = ref(true)
const drawer      = ref(null) // null | 'basics' | 'challenge'

const myGradeLevel = computed(() =>
  allGrades.value.find(g => g.grade === authStore.grade)
)
const lowerGrades = computed(() =>
  allGrades.value.filter(g => g.grade < authStore.grade).sort((a,b) => b.grade - a.grade)
)
const higherGrades = computed(() =>
  allGrades.value.filter(g => g.grade > authStore.grade).sort((a,b) => a.grade - b.grade)
)

const gradeItems = computed(() => {
  const s = skills.value.map(x => ({ ...x, itemType: 'skill' }))
  const t = manualTasks.value.map(x => ({ ...x, itemType: 'task' }))
  return [...s, ...t].sort((a, b) => (a.name || '').localeCompare(b.name || ''))
})

onMounted(async () => {
  try {
    const raw = await getGradeLevels()
    allGrades.value = raw.map(g => ({ id: Number(g.id), grade: Number(g.grade) }))

    const gl = myGradeLevel.value
    if (gl) {
      const [skillsRes, tasksRes] = await Promise.all([
        apiClient.get(`skills/by-grade/${gl.id}/`),
        getTasksByGrade(gl.id),
      ])
      skills.value   = skillsRes.data
      manualTasks.value = tasksRes
    }
  } catch (e) {
    console.error('[PersonalizedGradeHome] fetch error:', e)
  } finally {
    loading.value = false
  }
})

function goToGrade(gradeLevel) {
  drawer.value = null
  sessionStorage.setItem('selectedGrade', JSON.stringify({ id: gradeLevel.id, grade: gradeLevel.grade }))
  router.push({ name: 'gradeTopics', params: { gradeId: String(gradeLevel.id) } })
}

function openTaskExamples(task) {
  router.push({ name: 'examples', query: { task_id: String(task.id), task_name: task.name } })
}
</script>

<template>
  <div class="min-h-screen pb-32">
    <Spinner v-if="loading" class="pt-48" />

    <div v-else class="max-w-6xl mx-auto px-4 pt-8">

      <!-- Header -->
      <div class="flex flex-col items-center mb-8">
        <span class="text-sm font-bold uppercase tracking-widest text-gray-400 mb-1">Tvoj ročník</span>
        <h1 class="text-5xl font-black text-primary">{{ authStore.grade }}. ročník</h1>
      </div>

      <!-- My grade topics grid -->
      <div v-if="gradeItems.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <template v-for="item in gradeItems" :key="`${item.itemType}-${item.id}`">
          <TopicCard
            v-if="item.itemType === 'skill'"
            :topic="item.name"
            :id="Number(item.id)"
          />
          <button
            v-else
            @click="openTaskExamples(item)"
            class="text-left cursor-pointer border border-gray-300 rounded-xl shadow bg-white p-5 transition hover:shadow-xl hover:bg-secondary hover:border-secondary group"
          >
            <div class="text-xl font-bold text-primary group-hover:text-white break-words">{{ item.name }}</div>
            <div class="mt-2 text-sm text-slate-500 group-hover:text-slate-100">{{ item.example_count }} príkladov</div>
          </button>
        </template>
      </div>

      <div v-else class="text-center py-16 text-gray-400 text-lg">
        Pre tento ročník zatiaľ nie sú žiadne príklady.
      </div>

    </div>

    <!-- ── Fixed bottom action bar ── -->
    <div class="fixed bottom-0 left-0 right-0 z-30 flex gap-3 p-4 bg-white/80 backdrop-blur border-t border-gray-100">
      <!-- Basics button — only if lower grades exist -->
      <button
        v-if="lowerGrades.length > 0"
        @click="drawer = 'basics'"
        class="flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl font-extrabold text-base
               bg-gradient-to-br from-sky-100 to-blue-200 text-blue-800 border-2 border-blue-300
               hover:from-sky-200 hover:to-blue-300 transition active:scale-95"
      >
        📚 Základy
      </button>

      <!-- Challenge button — only if higher grades exist -->
      <button
        v-if="higherGrades.length > 0"
        @click="drawer = 'challenge'"
        class="flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl font-extrabold text-base
               bg-gradient-to-br from-orange-100 to-red-200 text-red-800 border-2 border-red-300
               hover:from-orange-200 hover:to-red-300 transition active:scale-95"
      >
        🔥 Výzva
      </button>
    </div>

    <!-- ── Bottom sheet backdrop ── -->
    <Transition name="backdrop-fade">
      <div
        v-if="drawer"
        class="fixed inset-0 bg-black/40 z-40"
        @click="drawer = null"
      />
    </Transition>

    <!-- ── Bottom sheet ── -->
    <Transition name="sheet-slide">
      <div
        v-if="drawer"
        class="fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-3xl shadow-2xl px-5 pt-4 pb-10 max-h-[70vh] overflow-y-auto"
      >
        <!-- Handle -->
        <div class="w-12 h-1.5 bg-gray-300 rounded-full mx-auto mb-5" />

        <!-- Basics sheet -->
        <template v-if="drawer === 'basics'">
          <h2 class="text-2xl font-black text-blue-700 mb-1">📚 Základy</h2>
          <p class="text-sm text-gray-400 mb-5">Precvičuj ľahší učebný materiál z nižších ročníkov.</p>
          <div class="grid grid-cols-3 sm:grid-cols-4 gap-3">
            <button
              v-for="g in lowerGrades"
              :key="g.id"
              @click="goToGrade(g)"
              class="flex flex-col items-center justify-center py-4 rounded-2xl border-2 border-sky-200
                     bg-gradient-to-br from-sky-50 to-blue-100 text-blue-800
                     hover:from-sky-200 hover:to-blue-200 transition font-bold text-xl active:scale-95"
            >
              {{ g.grade }}.
              <span class="text-xs font-normal text-blue-500 mt-0.5">ročník</span>
            </button>
          </div>
        </template>

        <!-- Challenge sheet -->
        <template v-if="drawer === 'challenge'">
          <h2 class="text-2xl font-black text-red-700 mb-1">🔥 Výzva</h2>
          <p class="text-sm text-gray-400 mb-5">Skús príklady z vyšších ročníkov a zarobi 1.5× viac XP!</p>
          <div class="grid grid-cols-3 sm:grid-cols-4 gap-3">
            <button
              v-for="g in higherGrades"
              :key="g.id"
              @click="goToGrade(g)"
              class="flex flex-col items-center justify-center py-4 rounded-2xl border-2 border-orange-200
                     bg-gradient-to-br from-orange-50 to-red-100 text-red-800
                     hover:from-orange-100 hover:to-red-200 transition font-bold text-xl active:scale-95"
            >
              {{ g.grade }}.
              <span class="text-xs font-normal text-red-400 mt-0.5">ročník</span>
            </button>
          </div>
        </template>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.backdrop-fade-enter-active, .backdrop-fade-leave-active { transition: opacity 0.25s ease; }
.backdrop-fade-enter-from, .backdrop-fade-leave-to       { opacity: 0; }

.sheet-slide-enter-active, .sheet-slide-leave-active { transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1); }
.sheet-slide-enter-from, .sheet-slide-leave-to       { transform: translateY(100%); }
</style>
