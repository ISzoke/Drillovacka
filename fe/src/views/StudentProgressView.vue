<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-2xl font-bold">Môj pokrok</h1>
      <button 
        @click="fetchData" 
        :disabled="loading"
        class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400 flex items-center gap-2">
        <i class="fa-solid fa-rotate" :class="{'fa-spin': loading}"></i>
        Obnoviť
      </button>
    </div>
    
    <div v-if="loading && skills.length === 0" class="text-gray-500">Načítavam...</div>
    <div v-else-if="error" class="text-red-600">Chyba: {{ error }}</div>
    <div v-else-if="!authStore.isAuthenticated || authStore.role === 'admin'" class="text-gray-500">
      Prihlás sa ako študent, aby si videl svoj pokrok.
    </div>
    <div v-else>
      <div class="mb-6 p-4 bg-blue-50 rounded border border-blue-200">
        <h2 class="text-lg font-semibold mb-2">Celková štatistika</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p class="text-sm text-gray-600">Cvičených príkladov</p>
            <p class="text-2xl font-bold">{{ totalExamples }}</p>
          </div>
          <div>
            <p class="text-sm text-gray-600">Správne vyriešené</p>
            <p class="text-2xl font-bold text-green-600">{{ totalSolved }}</p>
          </div>
          <div>
            <p class="text-sm text-gray-600">Celková presnosť</p>
            <p class="text-2xl font-bold" :class="accuracyColor(overallAccuracy)">{{ (overallAccuracy * 100).toFixed(1) }}%</p>
          </div>
          <div>
            <p class="text-sm text-gray-600">Priemerné mastery</p>
            <p class="text-2xl font-bold" :class="masteryColor(overallMastery)">{{ (overallMastery * 100).toFixed(1) }}%</p>
          </div>
        </div>
      </div>

      <h2 class="text-xl font-semibold mb-3">Detail podľa zručností</h2>
      <table class="min-w-full border">
        <thead>
          <tr class="bg-gray-100">
            <th class="p-2 border">Zručnosť</th>
            <th class="p-2 border">Príklady</th>
            <th class="p-2 border">Správne</th>
            <th class="p-2 border">Presnosť</th>
            <th class="p-2 border">Mastery</th>
            <th class="p-2 border">Priem. čas (s)</th>
            <th class="p-2 border">Posledné cvičenie</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in skills" :key="row.skill_id">
            <td class="border p-2">{{ row.skill_name }}</td>
            <td class="border p-2 text-center">{{ row.examples_practiced }}</td>
            <td class="border p-2 text-center">{{ row.solved_count }}</td>
            <td class="border p-2 text-center">
              <span :class="accuracyColor(row.accuracy)">{{ (row.accuracy * 100).toFixed(1) }}%</span>
            </td>
            <td class="border p-2 text-center">
              <span :class="masteryColor(row.mastery_mean)">{{ (row.mastery_mean * 100).toFixed(1) }}%</span>
            </td>
            <td class="border p-2 text-center">{{ (row.avg_duration_ms / 1000).toFixed(1) }}</td>
            <td class="border p-2 text-center text-sm">{{ formatDate(row.last_practiced) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="skills.length === 0" class="mt-4 text-gray-500">
        Zatiaľ si neriešil žiadne príklady. Začni cvičiť, aby si videl svoj pokrok!
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onActivated, watch, computed } from 'vue'
import { useAuthStore } from '@/stores/useAuthStore'
import { useRoute } from 'vue-router'
import { getStudentSkillStats } from '../api/apiClient'

const authStore = useAuthStore()
const route = useRoute()
const skills = ref([])
const loading = ref(false)
const error = ref('')

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

function fetchData() {
  if (!authStore.id) {
    console.warn('StudentProgressView: No id in authStore')
    return
  }
  console.log('StudentProgressView: Fetching data for student ID:', authStore.id)
  loading.value = true
  error.value = ''
  getStudentSkillStats(authStore.id)
    .then(data => {
      console.log('StudentProgressView: Received data:', data)
      skills.value = data
      loading.value = false
    })
    .catch(e => {
      console.error('StudentProgressView: Error fetching data:', e)
      error.value = e.message || 'Chyba pri načítaní dát.'
      loading.value = false
    })
}

function accuracyColor(val) {
  if (val >= 0.85) return 'text-green-700 font-semibold'
  if (val >= 0.6) return 'text-yellow-700 font-semibold'
  return 'text-red-700 font-semibold'
}
function masteryColor(val) {
  if (val >= 0.85) return 'text-green-700 font-semibold'
  if (val >= 0.6) return 'text-yellow-700 font-semibold'
  return 'text-red-700 font-semibold'
}
function formatDate(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleDateString()
}

onMounted(() => {
  fetchData()
})

// Automaticky obnoviť dáta keď sa používateľ vráti na túto stránku
onActivated(() => {
  fetchData()
})

// Alternatívne: obnoviť dáta pri zmene cesty (funguje aj bez keep-alive)
watch(() => route.path, (newPath) => {
  if (newPath === '/student-progress' && authStore.id) {
    fetchData()
  }
})
</script>

<style scoped>
table { border-collapse: collapse; }
th, td { text-align: left; }
</style>
