<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900 p-4 md:p-8">

    <!-- Not logged in -->
    <div v-if="!authStore.isAuthenticated || authStore.role === 'admin'"
         class="text-center py-16 text-slate-400">
      <i class="fa-solid fa-user-lock text-4xl mb-4"></i>
      <p>Prihlás sa ako študent, aby si videl svoj pokrok.</p>
    </div>

    <div v-else class="max-w-2xl mx-auto space-y-5">

      <!-- ── Level / XP card ── -->
      <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] p-6 sm:p-8">
        <div class="mb-6">
          <h2 class="text-3xl font-black text-slate-800 dark:text-slate-100 tracking-tight mb-1">Tvoj pokrok 📈</h2>
          <p class="text-slate-500 font-medium">Pozri sa, ako sa ti darí a čo si už dosiahol!</p>
        </div>

        <div class="bg-violet-50 dark:bg-violet-900/30 rounded-3xl p-5 border-[3px] border-violet-200 dark:border-violet-800 border-b-[6px]">
          <div class="flex justify-between items-center mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-violet-500 text-white rounded-xl flex items-center justify-center font-black text-xl shadow-sm">
                {{ gamStore.level }}
              </div>
              <span class="font-black text-violet-900 dark:text-violet-200 text-lg uppercase tracking-wider">Level {{ gamStore.level }}</span>
            </div>
            <span class="font-black text-violet-700 dark:text-violet-300 bg-white dark:bg-slate-700 px-3 py-1 rounded-xl shadow-sm text-sm">
              {{ gamStore.xp - gamStore.levelXpStart }} / {{ gamStore.levelXpEnd - gamStore.levelXpStart }} XP
            </span>
          </div>
          <div class="h-6 bg-white dark:bg-slate-700 rounded-full overflow-hidden border-2 border-violet-100 dark:border-violet-800 shadow-inner">
            <div
              class="h-full bg-violet-500 rounded-full relative transition-all duration-700"
              :style="{ width: gamStore.levelPercent() + '%' }">
              <div class="absolute top-1 left-2 right-2 h-2 bg-white/20 rounded-full"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loadingCombinations && combinations.length === 0" class="text-center py-16 text-slate-400">
        <i class="fa-solid fa-spinner fa-spin text-3xl"></i>
      </div>

      <div v-else-if="errorCombinations"
           class="bg-red-50 text-red-600 p-4 rounded-2xl border-2 border-red-200 font-semibold">
        {{ errorCombinations }}
      </div>

      <template v-else>
        <!-- ── No data ── -->
        <div v-if="combinations.length === 0"
             class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] p-8 text-center">
          <p class="text-2xl font-black text-slate-800 mb-2">Začni svoju cestu! 🚀</p>
          <p class="text-slate-500 font-medium mb-6">Zatiaľ si neriešil žiadne príklady. Vyber si tému a začni cvičiť!</p>
          <router-link to="/"
            class="inline-block px-8 py-4 bg-violet-500 text-white rounded-2xl font-black text-lg
                   border-b-[6px] border-violet-700 hover:-translate-y-0.5 transition-transform">
            Vybrať témy
          </router-link>
        </div>

        <template v-else>
          <!-- ── Stats grid ── -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-violet-50 dark:bg-violet-900/30 rounded-3xl border-[3px] border-violet-200 dark:border-violet-800 border-b-[6px] p-5 flex flex-col items-center text-center hover:-translate-y-1 transition-transform">
              <div class="inline-flex bg-violet-500 text-white p-3 rounded-2xl mb-3 shadow-sm border-b-4 border-violet-700">
                🎯
              </div>
              <p class="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Cvičených</p>
              <p class="text-2xl font-black text-slate-800 dark:text-slate-100">{{ totalExamples }}</p>
            </div>
            <div class="bg-emerald-50 dark:bg-emerald-900/30 rounded-3xl border-[3px] border-emerald-200 dark:border-emerald-800 border-b-[6px] p-5 flex flex-col items-center text-center hover:-translate-y-1 transition-transform">
              <div class="inline-flex bg-emerald-500 text-white p-3 rounded-2xl mb-3 shadow-sm border-b-4 border-emerald-700">
                ✅
              </div>
              <p class="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Správne</p>
              <p class="text-2xl font-black text-slate-800 dark:text-slate-100">{{ totalSolved }}</p>
            </div>
            <div class="bg-sky-50 dark:bg-sky-900/30 rounded-3xl border-[3px] border-sky-200 dark:border-sky-800 border-b-[6px] p-5 flex flex-col items-center text-center hover:-translate-y-1 transition-transform">
              <div class="inline-flex bg-sky-500 text-white p-3 rounded-2xl mb-3 shadow-sm border-b-4 border-sky-700">
                ⚡
              </div>
              <p class="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Presnosť</p>
              <p class="text-2xl font-black text-slate-800 dark:text-slate-100">{{ (overallAccuracy * 100).toFixed(0) }}%</p>
            </div>
            <div class="bg-amber-50 dark:bg-amber-900/30 rounded-3xl border-[3px] border-amber-200 dark:border-amber-800 border-b-[6px] p-5 flex flex-col items-center text-center hover:-translate-y-1 transition-transform">
              <div class="inline-flex bg-amber-500 text-white p-3 rounded-2xl mb-3 shadow-sm border-b-4 border-amber-700">
                🧠
              </div>
              <p class="text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Zvládnutie</p>
              <p class="text-2xl font-black text-slate-800 dark:text-slate-100">{{ (overallMastery * 100).toFixed(0) }}%</p>
            </div>
          </div>

          <!-- ── Recommended skills ── -->
          <div v-if="recommendedSkills.length > 0"
               class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] p-6 sm:p-8">
            <h3 class="text-2xl font-black text-slate-800 dark:text-slate-100 mb-6">Odporúčame precvičiť 🎯</h3>
            <div class="space-y-4">
              <div
                v-for="skill in recommendedSkills"
                :key="skill.skill_id"
                class="bg-orange-50 dark:bg-orange-900/20 border-[3px] border-orange-200 dark:border-orange-800 border-b-[6px] rounded-3xl p-5 hover:-translate-y-1 transition-transform">
                <div class="flex flex-col sm:flex-row items-start gap-4">
                  <div class="w-14 h-14 bg-orange-500 rounded-2xl flex items-center justify-center flex-shrink-0
                              shadow-sm border-b-4 border-orange-700 text-2xl">
                    📖
                  </div>
                  <div class="flex-1">
                    <h4 class="font-black text-xl text-slate-800 dark:text-slate-100 mb-1">{{ skill.combination_display }}</h4>
                    <p class="text-sm font-medium text-slate-600 dark:text-slate-400 mb-4">
                      Zvládnutie:
                      <span class="font-black px-2 py-0.5 rounded-lg"
                            :class="valueColor(skill.mastery_mean) + ' bg-orange-100 dark:bg-orange-900/40'">
                        {{ (skill.mastery_mean * 100).toFixed(0) }}%
                      </span>
                      · {{ formatDate(skill.last_practiced) }}
                    </p>
                    <button
                      @click="startPractice(skill.skill_ids)"
                      class="bg-orange-500 hover:bg-orange-400 active:bg-orange-600 text-white
                             px-6 py-3 rounded-2xl font-black text-base border-b-[4px] border-orange-700
                             active:border-b-0 active:translate-y-1 transition-all">
                      POĎ CVIČIŤ
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ── Skills overview ── -->
          <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] p-6 sm:p-8">
            <h3 class="text-2xl font-black text-slate-800 dark:text-slate-100 mb-6">Tvoje zručnosti 🧠</h3>
            <div class="space-y-4">
              <div
                v-for="skill in sortedCombinations"
                :key="skill.skill_id"
                class="bg-slate-50 dark:bg-slate-700/50 p-4 rounded-2xl border-2 border-slate-100 dark:border-slate-600">
                <div class="flex justify-between items-center mb-3">
                  <span class="font-black text-lg text-slate-700 dark:text-slate-200 truncate pr-2">{{ skill.combination_display }}</span>
                  <div class="flex items-center gap-3 flex-shrink-0">
                    <span class="text-sm font-bold text-slate-400 hidden sm:block">
                      {{ skill.examples_practiced }} príkl. · {{ skill.solved_count }} správne
                    </span>
                    <span class="font-black text-xl text-slate-800 dark:text-slate-100 bg-white dark:bg-slate-600 px-3 py-1 rounded-xl shadow-sm">
                      {{ (skill.mastery_mean * 100).toFixed(0) }}%
                    </span>
                  </div>
                </div>
                <!-- Mastery bar -->
                <div class="mb-2">
                  <div class="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span class="font-bold">Zvládnutie</span>
                    <span class="font-black" :class="valueColor(skill.mastery_mean)">{{ (skill.mastery_mean * 100).toFixed(0) }}%</span>
                  </div>
                  <div class="h-5 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden shadow-inner">
                    <div class="h-full rounded-full relative transition-all duration-500"
                         :class="barColor(skill.mastery_mean)"
                         :style="{ width: (skill.mastery_mean * 100) + '%' }">
                      <div class="absolute top-1 left-2 right-2 h-1.5 bg-white/20 rounded-full"></div>
                    </div>
                  </div>
                </div>
                <!-- Accuracy bar -->
                <div>
                  <div class="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span class="font-bold">Presnosť</span>
                    <span class="font-black" :class="valueColor(skill.accuracy)">{{ (skill.accuracy * 100).toFixed(0) }}%</span>
                  </div>
                  <div class="h-5 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden shadow-inner">
                    <div class="h-full rounded-full relative transition-all duration-500"
                         :class="barColor(skill.accuracy)"
                         :style="{ width: (skill.accuracy * 100) + '%' }">
                      <div class="absolute top-1 left-2 right-2 h-1.5 bg-white/20 rounded-full"></div>
                    </div>
                  </div>
                </div>
                <div class="flex justify-between text-[11px] text-slate-400 mt-2">
                  <span>Priem. čas: {{ (skill.avg_duration_ms / 1000).toFixed(1) }}s</span>
                  <span>{{ formatDate(skill.last_practiced) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- ── Streak cards ── -->
          <div class="grid sm:grid-cols-2 gap-4">
            <div class="bg-orange-500 rounded-3xl p-6 text-white border-b-[8px] border-orange-700 hover:-translate-y-1 transition-transform">
              <div class="flex items-center gap-4 mb-4">
                <div class="w-14 h-14 bg-white/20 rounded-2xl flex items-center justify-center border-2 border-white/20 text-3xl">
                  🔥
                </div>
                <div>
                  <p class="text-sm font-black text-orange-200 uppercase tracking-wider">Aktuálna séria</p>
                  <p class="text-4xl font-black">{{ gamStore.streak }} <span class="text-2xl">deň</span></p>
                </div>
              </div>
              <p class="text-sm font-bold text-orange-100 bg-black/10 p-3 rounded-xl">
                Pokračuj každý deň a udržuj si sériu! 🔥
              </p>
            </div>

            <div class="bg-amber-400 rounded-3xl p-6 text-white border-b-[8px] border-amber-600 hover:-translate-y-1 transition-transform">
              <div class="flex items-center gap-4 mb-4">
                <div class="w-14 h-14 bg-white/20 rounded-2xl flex items-center justify-center border-2 border-white/20 text-3xl">
                  🏆
                </div>
                <div>
                  <p class="text-sm font-black text-amber-100 uppercase tracking-wider">Najlepšia séria</p>
                  <p class="text-4xl font-black">{{ gamStore.longestStreak ?? gamStore.streak }} <span class="text-2xl">deň</span></p>
                </div>
              </div>
              <p class="text-sm font-bold text-amber-100 bg-black/10 p-3 rounded-xl">
                Skús prekonať svoj vlastný rekord! ⭐
              </p>
            </div>
          </div>

          <!-- ── Detail table (collapsible) ── -->
          <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] p-6 sm:p-8 mb-4">
            <button
              @click="showTable = !showTable"
              class="flex items-center justify-between w-full font-black text-slate-700 text-lg">
              <span>📊 Detailný prehľad</span>
              <i class="fa-solid text-slate-400" :class="showTable ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
            </button>
            <div v-if="showTable" class="mt-5 overflow-x-auto">
              <div v-if="loadingStats" class="text-slate-400 text-sm py-4 text-center">Načítavam...</div>
              <table v-else class="min-w-full text-sm">
                <thead>
                  <tr class="border-b-2 border-slate-100">
                    <th class="p-2 text-left text-slate-400 font-black text-xs uppercase tracking-wider">Zručnosť</th>
                    <th class="p-2 text-slate-400 font-black text-xs uppercase tracking-wider">Príkl.</th>
                    <th class="p-2 text-slate-400 font-black text-xs uppercase tracking-wider">Správne</th>
                    <th class="p-2 text-slate-400 font-black text-xs uppercase tracking-wider">Presnosť</th>
                    <th class="p-2 text-slate-400 font-black text-xs uppercase tracking-wider">Zvládnutie</th>
                    <th class="p-2 text-slate-400 font-black text-xs uppercase tracking-wider">Čas (s)</th>
                    <th class="p-2 text-slate-400 font-black text-xs uppercase tracking-wider">Posledné</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in skillStats" :key="row.skill_id"
                      class="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                    <td class="p-2 text-slate-700 dark:text-slate-200 font-bold">{{ row.skill_name }}</td>
                    <td class="p-2 text-center text-slate-600">{{ row.examples_practiced }}</td>
                    <td class="p-2 text-center text-slate-600">{{ row.solved_count }}</td>
                    <td class="p-2 text-center font-bold" :class="valueColor(row.accuracy)">{{ (row.accuracy * 100).toFixed(1) }}%</td>
                    <td class="p-2 text-center font-bold" :class="valueColor(row.mastery_mean)">{{ (row.mastery_mean * 100).toFixed(1) }}%</td>
                    <td class="p-2 text-center text-slate-600">{{ (row.avg_duration_ms / 1000).toFixed(1) }}</td>
                    <td class="p-2 text-center text-slate-400">{{ formatDate(row.last_practiced) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

        </template>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useAuthStore } from '@/stores/useAuthStore'
import { useGamificationStore } from '@/stores/useGamificationStore'
import { useRoute, useRouter } from 'vue-router'
import { getStudentSkillCombinations, getStudentSkillStats } from '../api/apiClient'

const authStore = useAuthStore()
const gamStore = useGamificationStore()
const route = useRoute()
const router = useRouter()

const combinations = ref([])
const skillStats = ref([])
const loadingCombinations = ref(false)
const loadingStats = ref(false)
const errorCombinations = ref('')
const showTable = ref(false)

const totalExamples = computed(() => combinations.value.reduce((sum, s) => sum + s.examples_practiced, 0))
const totalSolved = computed(() => combinations.value.reduce((sum, s) => sum + s.solved_count, 0))
const overallAccuracy = computed(() => totalExamples.value > 0 ? totalSolved.value / totalExamples.value : 0)
const overallMastery = computed(() => {
  if (combinations.value.length === 0) return 0
  return combinations.value.reduce((acc, s) => acc + s.mastery_mean, 0) / combinations.value.length
})
const recommendedSkills = computed(() =>
  [...combinations.value].sort((a, b) => b.next_weight - a.next_weight).slice(0, 3)
)
const sortedCombinations = computed(() =>
  [...combinations.value].sort((a, b) => a.mastery_mean - b.mastery_mean)
)

function fetchCombinations() {
  if (!authStore.id) return
  loadingCombinations.value = true
  errorCombinations.value = ''
  getStudentSkillCombinations(authStore.id)
    .then(data => { combinations.value = data })
    .catch(e => { errorCombinations.value = e.message || 'Chyba pri načítaní dát.' })
    .finally(() => { loadingCombinations.value = false })
}

function fetchStats() {
  if (!authStore.id) return
  loadingStats.value = true
  getStudentSkillStats(authStore.id)
    .then(data => { skillStats.value = data })
    .catch(() => {})
    .finally(() => { loadingStats.value = false })
}

function startPractice(skillIds) {
  router.push({ name: 'examples', query: { topics: JSON.stringify(skillIds) } })
}

function valueColor(val) {
  if (val >= 0.85) return 'text-emerald-600'
  if (val >= 0.6)  return 'text-amber-600'
  return 'text-red-500'
}
function barColor(val) {
  if (val >= 0.85) return 'bg-emerald-500'
  if (val >= 0.6)  return 'bg-amber-400'
  return 'bg-red-400'
}
function formatDate(dt) {
  if (!dt) return 'Nikdy'
  const diffDays = Math.floor((new Date() - new Date(dt)) / 86400000)
  if (diffDays === 0) return 'Dnes'
  if (diffDays === 1) return 'Včera'
  if (diffDays < 7)  return `Pred ${diffDays} dňami`
  if (diffDays < 30) return `Pred ${Math.floor(diffDays / 7)} týždňami`
  return new Date(dt).toLocaleDateString('sk-SK')
}

watch(showTable, (opened) => {
  if (opened && skillStats.value.length === 0) fetchStats()
})

watch(() => route.path, (newPath) => {
  if (newPath === '/progress' && authStore.id) fetchCombinations()
})

onMounted(() => {
  fetchCombinations()
  if (authStore.id) gamStore.fetchStats(authStore.id)
})
</script>
