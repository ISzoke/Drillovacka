<template>
  <div class="p-6 max-w-6xl mx-auto">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-3xl font-bold text-gray-800">Ahoj, {{ authStore.name }}! 👋</h1>
        <p class="text-gray-600 mt-1">Tu je tvoj prehľad pokroku</p>
      </div>
      <button 
        @click="fetchData" 
        :disabled="loading"
        class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 flex items-center gap-2">
        <i class="fa-solid fa-rotate" :class="{'fa-spin': loading}"></i>
        Obnoviť
      </button>
    </div>

    <div v-if="loading && skills.length === 0" class="text-gray-500 text-center py-12">
      <i class="fa-solid fa-spinner fa-spin text-4xl mb-4"></i>
      <p>Načítavam tvoj pokrok...</p>
    </div>
    
    <div v-else-if="error" class="text-red-600 bg-red-50 p-4 rounded border border-red-200">
      <i class="fa-solid fa-exclamation-triangle mr-2"></i>
      Chyba: {{ error }}
    </div>
    
    <div v-else-if="!authStore.isAuthenticated || authStore.role === 'admin'" class="text-gray-500 text-center py-12">
      <i class="fa-solid fa-user-lock text-4xl mb-4"></i>
      <p>Prihlás sa ako študent, aby si videl svoj dashboard.</p>
    </div>
    
    <div v-else>
      <!-- No data yet -->
      <div v-if="skills.length === 0" class="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
        <i class="fa-solid fa-book-open text-6xl text-gray-400 mb-4"></i>
        <h3 class="text-xl font-semibold text-gray-700 mb-2">Začni svoju cestu učenia!</h3>
        <p class="text-gray-600 mb-6">Zatiaľ si neriešil žiadne príklady. Vyber si skill a začni cvičiť!</p>
        <router-link to="/grade-view" class="inline-block px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-semibold">
          Vybrať témy
        </router-link>
      </div>

      <!-- Dashboard with data -->
      <div v-else>
        <!-- Overall Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div class="bg-gradient-to-br from-blue-500 to-blue-600 text-white p-6 rounded-lg shadow-lg">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-blue-100 text-sm font-medium">Cvičených príkladov</p>
                <p class="text-3xl font-bold mt-2">{{ totalExamples }}</p>
              </div>
              <i class="fa-solid fa-list-check text-4xl text-blue-200"></i>
            </div>
          </div>

          <div class="bg-gradient-to-br from-green-500 to-green-600 text-white p-6 rounded-lg shadow-lg">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-green-100 text-sm font-medium">Správne vyriešené</p>
                <p class="text-3xl font-bold mt-2">{{ totalSolved }}</p>
              </div>
              <i class="fa-solid fa-check-circle text-4xl text-green-200"></i>
            </div>
          </div>

          <div class="bg-gradient-to-br from-purple-500 to-purple-600 text-white p-6 rounded-lg shadow-lg">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-purple-100 text-sm font-medium">Celková presnosť</p>
                <p class="text-3xl font-bold mt-2">{{ (overallAccuracy * 100).toFixed(0) }}%</p>
              </div>
              <i class="fa-solid fa-bullseye text-4xl text-purple-200"></i>
            </div>
          </div>

          <div class="bg-gradient-to-br from-orange-500 to-orange-600 text-white p-6 rounded-lg shadow-lg">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-orange-100 text-sm font-medium">Priemerné zvládnutie</p>
                <p class="text-3xl font-bold mt-2">{{ (overallMastery * 100).toFixed(0) }}%</p>
              </div>
              <i class="fa-solid fa-star text-4xl text-orange-200"></i>
            </div>
          </div>
        </div>

        <!-- Recommended Skills Section -->
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
              v-for="skill in recommendedSkills" 
              :key="skill.skill_id"
              class="bg-white border-2 border-yellow-400 rounded-lg p-4 hover:shadow-lg transition-shadow">
              <div class="flex justify-between items-start mb-3">
                <h3 class="font-bold text-lg text-gray-800">{{ skill.combination_display }}</h3>
                <span class="bg-yellow-500 text-white text-xs px-2 py-1 rounded-full font-semibold">
                  #{{ recommendedSkills.indexOf(skill) + 1 }}
                </span>
              </div>
              
              <div class="space-y-2 text-sm mb-4">
                <div class="flex justify-between">
                  <span class="text-gray-600">Zvládnutie:</span>
                  <span :class="masteryColor(skill.mastery_mean)" class="font-semibold">
                    {{ (skill.mastery_mean * 100).toFixed(0) }}%
                  </span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-600">Presnosť:</span>
                  <span :class="accuracyColor(skill.accuracy)" class="font-semibold">
                    {{ (skill.accuracy * 100).toFixed(0) }}%
                  </span>
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

        <!-- Skills Overview with Progress Bars -->
        <div class="bg-white rounded-lg shadow-lg p-6">
          <h2 class="text-2xl font-bold mb-4 text-gray-800">
            <i class="fa-solid fa-chart-line mr-2 text-blue-500"></i>
            Tvoje zručnosti
          </h2>

          <div class="space-y-4">
            <div 
              v-for="skill in sortedSkills" 
              :key="skill.skill_id"
              class="border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition-all">
              
              <div class="flex justify-between items-center mb-3">
                <h3 class="font-bold text-lg text-gray-800">{{ skill.skill_name }}</h3>
                <div class="flex items-center gap-4 text-sm">
                  <span class="text-gray-600">
                    <i class="fa-solid fa-list-check mr-1"></i>
                    {{ skill.examples_practiced }} príkladov
                  </span>
                  <span class="text-green-600 font-semibold">
                    <i class="fa-solid fa-check mr-1"></i>
                    {{ skill.solved_count }} správne
                  </span>
                </div>
              </div>

              <!-- Mastery Progress Bar -->
              <div class="mb-3">
                <div class="flex justify-between text-sm mb-1">
                  <span class="text-gray-600 font-medium">Zvládnutie (Mastery)</span>
                  <span :class="masteryColor(skill.mastery_mean)" class="font-bold">
                    {{ (skill.mastery_mean * 100).toFixed(1) }}%
                  </span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div 
                    class="h-3 rounded-full transition-all duration-500 ease-out"
                    :class="masteryBarColor(skill.mastery_mean)"
                    :style="{ width: (skill.mastery_mean * 100) + '%' }">
                  </div>
                </div>
              </div>

              <!-- Accuracy Progress Bar -->
              <div class="mb-3">
                <div class="flex justify-between text-sm mb-1">
                  <span class="text-gray-600 font-medium">Presnosť (Accuracy)</span>
                  <span :class="accuracyColor(skill.accuracy)" class="font-bold">
                    {{ (skill.accuracy * 100).toFixed(1) }}%
                  </span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <div 
                    class="h-3 rounded-full transition-all duration-500 ease-out"
                    :class="accuracyBarColor(skill.accuracy)"
                    :style="{ width: (skill.accuracy * 100) + '%' }">
                  </div>
                </div>
              </div>

              <!-- Additional Info -->
              <div class="flex justify-between items-center text-sm text-gray-600">
                <span>
                  <i class="fa-solid fa-clock mr-1"></i>
                  Priem. čas: {{ (skill.avg_duration_ms / 1000).toFixed(1) }}s
                </span>
                <span>
                  <i class="fa-solid fa-calendar mr-1"></i>
                  {{ formatDate(skill.last_practiced) }}
                </span>
              </div>
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
import { useRoute, useRouter } from 'vue-router'
import { getStudentSkillCombinations } from '../api/apiClient'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const skills = ref([])
const loading = ref(false)
const error = ref('')

// Computed stats
const totalExamples = computed(() => skills.value.reduce((sum, s) => sum + s.examples_practiced, 0))
const totalSolved = computed(() => skills.value.reduce((sum, s) => sum + s.solved_count, 0))
const overallAccuracy = computed(() => {
  const total = totalExamples.value
  const solved = totalSolved.value
  return total > 0 ? solved / total : 0
})
const overallMastery = computed(() => {
  if (skills.value.length === 0) return 0
  const sum = skills.value.reduce((acc, s) => acc + s.mastery_mean, 0)
  return sum / skills.value.length
})

// Recommended skills - top 3 by next_weight (weak + stale skills)
const recommendedSkills = computed(() => {
  if (skills.value.length === 0) return []
  return [...skills.value]
    .sort((a, b) => b.next_weight - a.next_weight)
    .slice(0, 3)
})

// Sorted skills by mastery (lowest first)
const sortedSkills = computed(() => {
  return [...skills.value].sort((a, b) => a.mastery_mean - b.mastery_mean)
})

function fetchData() {
  if (!authStore.id) {
    console.warn('StudentDashboardView: No id in authStore')
    return
  }
  console.log('StudentDashboardView: Fetching skill combinations for student ID:', authStore.id)
  loading.value = true
  error.value = ''
  getStudentSkillCombinations(authStore.id)
    .then(data => {
      console.log('StudentDashboardView: Received combinations:', data)
      skills.value = data
      loading.value = false
    })
    .catch(e => {
      console.error('StudentDashboardView: Error fetching combinations:', e)
      error.value = e.message || 'Chyba pri načítaní dát.'
      loading.value = false
    })
}

function startPractice(skillIds) {
  // Navigate to examples page with skill combination
  // skillIds is an array like [65, 69, 71] for "Sčítání + Celá čísla + Do 100"
  router.push({ 
    name: 'examples', 
    query: { 
      topics: JSON.stringify(skillIds) 
    } 
  })
}

function accuracyColor(val) {
  if (val >= 0.85) return 'text-green-700'
  if (val >= 0.6) return 'text-yellow-700'
  return 'text-red-700'
}

function masteryColor(val) {
  if (val >= 0.85) return 'text-green-700'
  if (val >= 0.6) return 'text-yellow-700'
  return 'text-red-700'
}

function accuracyBarColor(val) {
  if (val >= 0.85) return 'bg-green-500'
  if (val >= 0.6) return 'bg-yellow-500'
  return 'bg-red-500'
}

function masteryBarColor(val) {
  if (val >= 0.85) return 'bg-green-500'
  if (val >= 0.6) return 'bg-yellow-500'
  return 'bg-red-500'
}

function formatDate(dt) {
  if (!dt) return 'Nikdy'
  const date = new Date(dt)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) return 'Dnes'
  if (diffDays === 1) return 'Včera'
  if (diffDays < 7) return `Pred ${diffDays} dňami`
  if (diffDays < 30) return `Pred ${Math.floor(diffDays / 7)} týždňami`
  return date.toLocaleDateString('sk-SK')
}

onMounted(() => {
  fetchData()
})

// Auto-refresh when returning to this page
watch(() => route.path, (newPath) => {
  if (newPath === '/dashboard' && authStore.id) {
    fetchData()
  }
})
</script>

<style scoped>
/* Smooth animations */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.grid > div {
  animation: slideIn 0.3s ease-out;
}
</style>
