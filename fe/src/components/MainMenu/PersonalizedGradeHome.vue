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
import { useLanguageStore } from '@/stores/useLanguageStore'
import { dictionary, getTaskName } from '@/utils/dictionary'
import { getGradeLevels, getTasksByGrade } from '@/api/apiClient'
import Spinner from '@/components/Spinner.vue'
import ExampleRequestSheet from '@/components/ExampleRequestSheet.vue'

const authStore = useAuthStore()
const langStore = useLanguageStore()
const router = useRouter()

const allGrades   = ref([])
const tasks   = ref([])
const loading = ref(true)
const drawer      = ref(null) // null | 'basics' | 'challenge' | 'request'

const myGradeLevel = computed(() =>
  allGrades.value.find(g => g.grade === authStore.grade)
)
const lowerGrades = computed(() =>
  allGrades.value.filter(g => g.grade < authStore.grade).sort((a,b) => b.grade - a.grade)
)
const higherGrades = computed(() =>
  allGrades.value.filter(g => g.grade > authStore.grade).sort((a,b) => a.grade - b.grade)
)

onMounted(async () => {
  try {
    const raw = await getGradeLevels()
    allGrades.value = raw.map(g => ({ id: Number(g.id), grade: Number(g.grade) }))
    const gl = myGradeLevel.value
    if (gl) {
      tasks.value = await getTasksByGrade(gl.id, authStore.id || null)
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
  router.push({ name: 'taskDetail', params: { taskId: String(task.id) } })
}
</script>

<template>
  <div class="min-h-screen pb-32">
    <Spinner v-if="loading" class="pt-48" />

    <div v-else class="max-w-5xl mx-auto px-4 pt-8">

      <!-- Header -->
      <div class="flex flex-col items-center mb-8">
        <span class="text-xs font-black uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">Tvoj ročník</span>
        <h1 class="text-3xl md:text-5xl font-black text-slate-800 dark:text-slate-100">{{ authStore.grade }}. ročník</h1>
      </div>

      <!-- My grade tasks grid -->
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
                {{ dictionary[langStore.language].aiGeneratedBadge }}
              </span>
            </div>
            <div class="text-xl font-black text-violet-800 dark:text-violet-200 break-words">{{ getTaskName(task.name, langStore.language) }}</div>
            <div class="mt-2 text-sm font-bold text-violet-400 dark:text-violet-500">{{ task.example_count }} {{ dictionary[langStore.language].examplesCountPrivate }}</div>
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
                {{ dictionary[langStore.language].aiGeneratedBadge }}
              </span>
            </div>
            <div class="text-xl font-black text-slate-800 dark:text-slate-100 break-words">{{ getTaskName(task.name, langStore.language) }}</div>
            <div class="mt-2 text-sm font-bold text-slate-400 dark:text-slate-500">{{ task.example_count }} {{ dictionary[langStore.language].examplesCount }}</div>
          </button>
        </template>
      </div>

      <div v-else class="text-center py-16 text-slate-400 dark:text-slate-500 text-lg font-semibold">
        Pre tento ročník zatiaľ nie sú žiadne príklady.
      </div>

      <!-- "Want more examples?" text link below the grid -->
      <div class="text-center mt-8 mb-4">
        <button
          @click="drawer = 'request'"
          class="text-sm font-semibold text-slate-400 dark:text-slate-500 hover:text-violet-500 transition underline underline-offset-2"
        >
          💡 Málo príkladov? Klikni sem.
        </button>
      </div>

    </div>

    <!-- Fixed bottom action bar -->
    <div class="fixed bottom-0 left-0 right-0 z-30 flex gap-3 p-4
                bg-white/90 dark:bg-slate-800/90 backdrop-blur
                border-t border-slate-200 dark:border-slate-700">

      <button
        v-if="lowerGrades.length > 0"
        @click="drawer = 'basics'"
        class="flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl font-black text-base
               bg-sky-50 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300
               border-[3px] border-sky-200 dark:border-sky-700 border-b-[6px] border-b-sky-300 dark:border-b-sky-600
               hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all"
      >
        📚 Základy
      </button>

      <button
        @click="drawer = 'request'"
        class="flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl font-bold text-sm
               bg-slate-50 dark:bg-slate-700 text-slate-500 dark:text-slate-400
               border-[3px] border-slate-200 dark:border-slate-600 border-b-[6px] border-b-slate-300 dark:border-b-slate-500
               hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all"
      >
        💡 Málo príkladov?
      </button>

      <button
        v-if="higherGrades.length > 0"
        @click="drawer = 'challenge'"
        class="flex-1 flex items-center justify-center gap-2 py-4 rounded-2xl font-black text-base
               bg-orange-50 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300
               border-[3px] border-orange-200 dark:border-orange-700 border-b-[6px] border-b-orange-300 dark:border-b-orange-600
               hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all"
      >
        🔥 Výzva
      </button>
    </div>

    <!-- Backdrop (only for basics/challenge) -->
    <Transition name="backdrop-fade">
      <div
        v-if="drawer === 'basics' || drawer === 'challenge'"
        class="fixed inset-0 bg-black/40 z-40"
        @click="drawer = null"
      />
    </Transition>

    <!-- Example request sheet -->
    <ExampleRequestSheet
      :open="drawer === 'request'"
      :grade="authStore.grade"
      @close="drawer = null"
    />

    <!-- Bottom sheet -->
    <Transition name="sheet-slide">
      <div
        v-if="drawer === 'basics' || drawer === 'challenge'"
        class="fixed bottom-0 left-0 right-0 z-50
               bg-white dark:bg-slate-800 rounded-t-3xl shadow-2xl
               px-5 pt-4 pb-10 max-h-[70vh] overflow-y-auto"
      >
        <!-- Handle -->
        <div class="w-12 h-1.5 bg-slate-300 dark:bg-slate-600 rounded-full mx-auto mb-5" />

        <!-- Basics sheet -->
        <template v-if="drawer === 'basics'">
          <h2 class="text-2xl font-black text-sky-700 dark:text-sky-300 mb-1">📚 Základy</h2>
          <p class="text-sm text-slate-400 dark:text-slate-500 mb-5">Precvičuj ľahší učebný materiál z nižších ročníkov.</p>
          <div class="grid grid-cols-3 sm:grid-cols-4 gap-3">
            <button
              v-for="g in lowerGrades"
              :key="g.id"
              @click="goToGrade(g)"
              class="flex flex-col items-center justify-center py-4 rounded-2xl
                     border-[3px] border-sky-600 border-b-[6px] border-b-sky-800
                     bg-sky-500 text-white
                     hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all font-black text-xl"
            >
              {{ g.grade }}.
              <span class="text-xs font-bold text-sky-100 mt-0.5">ročník</span>
            </button>
          </div>
        </template>

        <!-- Challenge sheet -->
        <template v-if="drawer === 'challenge'">
          <h2 class="text-2xl font-black text-orange-700 dark:text-orange-300 mb-1">🔥 Výzva</h2>
          <p class="text-sm text-slate-400 dark:text-slate-500 mb-5">Skús príklady z vyšších ročníkov a zarobi 1.5× viac XP!</p>
          <div class="grid grid-cols-3 sm:grid-cols-4 gap-3">
            <button
              v-for="g in higherGrades"
              :key="g.id"
              @click="goToGrade(g)"
              class="flex flex-col items-center justify-center py-4 rounded-2xl
                     border-[3px] border-orange-600 border-b-[6px] border-b-orange-800
                     bg-orange-500 text-white
                     hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all font-black text-xl"
            >
              {{ g.grade }}.
              <span class="text-xs font-bold text-orange-100 mt-0.5">ročník</span>
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
