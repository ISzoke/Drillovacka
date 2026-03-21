<template>
  <div class="p-6 max-w-6xl mx-auto">

    <div v-if="!authStore.isAuthenticated || authStore.role === 'admin'" class="text-gray-500 text-center py-12">
      <i class="fa-solid fa-user-lock text-4xl mb-4"></i>
      <p>Prihlás sa ako študent, aby si videl svoj pokrok.</p>
    </div>

    <div v-else>
      <!-- Gamification banner -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <!-- Level & XP bar -->
        <div class="col-span-2 bg-gradient-to-br from-violet-500 to-indigo-600 text-white p-5 rounded-2xl shadow-lg">
          <div class="flex justify-between items-center mb-1">
            <span class="font-bold text-lg">⭐ Level {{ gamStore.level }}</span>
            <span class="text-sm text-violet-200">{{ gamStore.xp }} XP</span>
          </div>
          <div class="w-full bg-violet-800/40 rounded-full h-3 overflow-hidden">
            <div
              class="h-3 rounded-full bg-yellow-400 transition-all duration-700"
              :style="{ width: gamStore.levelPercent() + '%' }">
            </div>
          </div>
          <div class="text-xs text-violet-200 mt-1">
            {{ gamStore.xp - gamStore.levelXpStart }} / {{ gamStore.levelXpEnd - gamStore.levelXpStart }} XP do ďalšieho levelu
          </div>
        </div>

        <!-- Streak -->
        <div class="bg-gradient-to-br from-orange-400 to-red-500 text-white p-5 rounded-2xl shadow-lg flex flex-col justify-center">
          <div class="text-4xl">🔥</div>
          <div class="text-3xl font-black mt-1">{{ gamStore.streak }}</div>
          <div class="text-sm text-orange-100">dní za sebou</div>
        </div>

        <!-- Rank -->
        <div class="bg-gradient-to-br from-amber-400 to-yellow-500 text-white p-5 rounded-2xl shadow-lg flex flex-col justify-center">
          <div class="text-4xl">🏅</div>
          <div class="text-3xl font-black mt-1">
            <span v-if="gamStore.rank">#{{ gamStore.rank }}</span>
            <span v-else>–</span>
          </div>
          <div class="text-sm text-yellow-100">na rebríčku</div>
        </div>
      </div>

      <div v-if="loadingCombinations && combinations.length === 0" class="text-gray-500 text-center py-12">
        <i class="fa-solid fa-spinner fa-spin text-4xl mb-4"></i>
        <p>Načítavam tvoj pokrok...</p>
      </div>

      <div v-else-if="errorCombinations" class="text-red-600 bg-red-50 p-4 rounded border border-red-200 mb-6">
        <i class="fa-solid fa-exclamation-triangle mr-2"></i>Chyba: {{ errorCombinations }}
      </div>

      <div v-else>
        <!-- No data yet -->
        <div v-if="combinations.length === 0" class="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 mb-6">
          <i class="fa-solid fa-book-open text-6xl text-gray-400 mb-4"></i>
          <h3 class="text-xl font-semibold text-gray-700 mb-2">Začni svoju cestu učenia!</h3>
          <p class="text-gray-600 mb-6">Zatiaľ si neriešil žiadne príklady. Vyber si tému a začni cvičiť!</p>
          <router-link to="/" class="inline-block px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-semibold">
            Vybrať témy
          </router-link>
        </div>

        <div v-else>
          <!-- Overall Stats Cards -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-gradient-to-br from-blue-500 to-blue-600 text-white p-6 rounded-lg shadow-lg">
              <p class="text-blue-100 text-sm font-medium">Cvičených príkladov</p>
              <p class="text-3xl font-bold mt-2">{{ totalExamples }}</p>
            </div>
            <div class="bg-gradient-to-br from-green-500 to-green-600 text-white p-6 rounded-lg shadow-lg">
              <p class="text-green-100 text-sm font-medium">Správne vyriešené</p>
              <p class="text-3xl font-bold mt-2">{{ totalSolved }}</p>
            </div>
            <div class="bg-gradient-to-br from-purple-500 to-purple-600 text-white p-6 rounded-lg shadow-lg">
              <p class="text-purple-100 text-sm font-medium">Celková presnosť</p>
              <p class="text-3xl font-bold mt-2">{{ (overallAccuracy * 100).toFixed(0) }}%</p>
            </div>
            <div class="bg-gradient-to-br from-orange-500 to-orange-600 text-white p-6 rounded-lg shadow-lg">
              <p class="text-orange-100 text-sm font-medium">Priem. zvládnutie</p>
              <p class="text-3xl font-bold mt-2">{{ (overallMastery * 100).toFixed(0) }}%</p>
            </div>
          </div>

          <!-- Recommended Skills -->
          <div v-if="recommendedSkills.length > 0" class="mb-6 bg-yellow-50 border-2 border-yellow-300 rounded-lg p-6">
            <div class="flex items-center gap-3 mb-4">
              <i class="fa-solid fa-lightbulb text-3xl text-yellow-600"></i>
              <div>
                <h2 class="text-2xl font-bold text-yellow-900">Odporúčame na precvičenie</h2>
                <p class="text-yellow-700 text-sm">Tieto témy by si mal precvičiť – sú slabšie alebo si ich dlho necvičil</p>
              </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div
                v-for="(skill, idx) in recommendedSkills"
                :key="skill.skill_id"
                class="bg-white border-2 border-yellow-400 rounded-lg p-4 hover:shadow-lg transition-shadow">
                <div class="flex justify-between items-start mb-3">
                  <h3 class="font-bold text-lg text-gray-800">{{ skill.combination_display }}</h3>
                  <span class="bg-yellow-500 text-white text-xs px-2 py-1 rounded-full font-semibold">#{{ idx + 1 }}</span>
                </div>
                <div class="space-y-2 text-sm mb-4">
                  <div class="flex justify-between">
                    <span class="text-gray-600">Zvládnutie:</span>
                    <span :class="valueColor(skill.mastery_mean)" class="font-semibold">{{ (skill.mastery_mean * 100).toFixed(0) }}%</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-600">Presnosť:</span>
                    <span :class="valueColor(skill.accuracy)" class="font-semibold">{{ (skill.accuracy * 100).toFixed(0) }}%</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-600">Naposledy:</span>
                    <span class="text-gray-800 font-medium">{{ formatDate(skill.last_practiced) }}</span>
                  </div>
                </div>
                <button
                  @click="startPractice(skill.skill_ids)"
                  class="w-full bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-2 rounded transition-colors">
                  <i class="fa-solid fa-play mr-2"></i>Začať cvičiť
                </button>
              </div>
            </div>
          </div>

          <!-- Skills Progress Bars -->
          <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 class="text-2xl font-bold mb-4 text-gray-800">
              <i class="fa-solid fa-chart-line mr-2 text-blue-500"></i>Tvoje zručnosti
            </h2>
            <div class="space-y-4">
              <div
                v-for="skill in sortedCombinations"
                :key="skill.skill_id"
                class="border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all">
                <div class="flex justify-between items-center mb-3">
                  <h3 class="font-bold text-lg text-gray-800">{{ skill.skill_name }}</h3>
                  <div class="flex items-center gap-4 text-sm">
                    <span class="text-gray-600"><i class="fa-solid fa-list-check mr-1"></i>{{ skill.examples_practiced }} príkladov</span>
                    <span class="text-green-600 font-semibold"><i class="fa-solid fa-check mr-1"></i>{{ skill.solved_count }} správne</span>
                  </div>
                </div>
                <div class="mb-3">
                  <div class="flex justify-between text-sm mb-1">
                    <span class="text-gray-600 font-medium">Zvládnutie</span>
                    <span :class="valueColor(skill.mastery_mean)" class="font-bold">{{ (skill.mastery_mean * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div class="h-3 rounded-full transition-all duration-500" :class="valueBarColor(skill.mastery_mean)" :style="{ width: (skill.mastery_mean * 100) + '%' }"></div>
                  </div>
                </div>
                <div class="mb-3">
                  <div class="flex justify-between text-sm mb-1">
                    <span class="text-gray-600 font-medium">Presnosť</span>
                    <span :class="valueColor(skill.accuracy)" class="font-bold">{{ (skill.accuracy * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div class="h-3 rounded-full transition-all duration-500" :class="valueBarColor(skill.accuracy)" :style="{ width: (skill.accuracy * 100) + '%' }"></div>
                  </div>
                </div>
                <div class="flex justify-between items-center text-sm text-gray-600">
                  <span><i class="fa-solid fa-clock mr-1"></i>Priem. čas: {{ (skill.avg_duration_ms / 1000).toFixed(1) }}s</span>
                  <span><i class="fa-solid fa-calendar mr-1"></i>{{ formatDate(skill.last_practiced) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Detail table (collapsible) -->
          <div class="bg-white rounded-lg shadow p-4">
            <button
              @click="showTable = !showTable"
              class="flex items-center gap-2 text-lg font-semibold text-gray-700 w-full text-left">
              <i class="fa-solid fa-table mr-1 text-gray-400"></i>
              Detailný prehľad
              <i class="fa-solid ml-auto text-gray-400" :class="showTable ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
            </button>
            <div v-if="showTable" class="mt-4 overflow-x-auto">
              <div v-if="loadingStats" class="text-gray-400 text-sm py-4 text-center">Načítavam...</div>
              <table v-else class="min-w-full border text-sm">
                <thead>
                  <tr class="bg-gray-100">
                    <th class="p-2 border text-left">Zručnosť</th>
                    <th class="p-2 border">Príklady</th>
                    <th class="p-2 border">Správne</th>
                    <th class="p-2 border">Presnosť</th>
                    <th class="p-2 border">Mastery</th>
                    <th class="p-2 border">Priem. čas (s)</th>
                    <th class="p-2 border">Posledné cvičenie</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in skillStats" :key="row.skill_id" class="hover:bg-gray-50">
                    <td class="border p-2">{{ row.skill_name }}</td>
                    <td class="border p-2 text-center">{{ row.examples_practiced }}</td>
                    <td class="border p-2 text-center">{{ row.solved_count }}</td>
                    <td class="border p-2 text-center"><span :class="valueColor(row.accuracy)">{{ (row.accuracy * 100).toFixed(1) }}%</span></td>
                    <td class="border p-2 text-center"><span :class="valueColor(row.mastery_mean)">{{ (row.mastery_mean * 100).toFixed(1) }}%</span></td>
                    <td class="border p-2 text-center">{{ (row.avg_duration_ms / 1000).toFixed(1) }}</td>
                    <td class="border p-2 text-center">{{ formatDate(row.last_practiced) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
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
  if (val >= 0.85) return 'text-green-700 font-semibold'
  if (val >= 0.6) return 'text-yellow-700 font-semibold'
  return 'text-red-700 font-semibold'
}
function valueBarColor(val) {
  if (val >= 0.85) return 'bg-green-500'
  if (val >= 0.6) return 'bg-yellow-500'
  return 'bg-red-500'
}
function formatDate(dt) {
  if (!dt) return 'Nikdy'
  const diffDays = Math.floor((new Date() - new Date(dt)) / 86400000)
  if (diffDays === 0) return 'Dnes'
  if (diffDays === 1) return 'Včera'
  if (diffDays < 7) return `Pred ${diffDays} dňami`
  if (diffDays < 30) return `Pred ${Math.floor(diffDays / 7)} týždňami`
  return new Date(dt).toLocaleDateString('sk-SK')
}

// Load stats table lazily when user expands it
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

<style scoped>
table { border-collapse: collapse; }
</style>
