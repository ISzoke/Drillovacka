<template>
  <div class="p-6 max-w-6xl mx-auto">
    <h1 class="text-2xl font-bold mb-4">Analytika zručností</h1>
    
    <!-- Filter: Student ID or All Students -->
    <div class="mb-4 flex gap-2 items-end">
      <label class="font-semibold">Študent ID:</label>
      <input v-model="studentId" type="number" class="border rounded px-2 py-1 w-32" @keyup.enter="fetchData" placeholder="alebo prázdne pre všetkých" />
      <button @click="fetchData" class="bg-blue-600 text-white px-3 py-1 rounded">Načítať</button>
    </div>

    <div v-if="loading" class="text-gray-500">Načítavam...</div>
    <div v-else-if="error" class="text-red-600">Chyba: {{ error }}</div>

    <!-- All Students View -->
    <div v-else-if="showingAllStudents">
      <h2 class="text-xl font-semibold mb-3">Všetci študenti</h2>
      <table class="min-w-full border mt-4">
        <thead>
          <tr class="bg-gray-100">
            <th class="p-2 border">Používateľ</th>
            <th class="p-2 border">Príklady</th>
            <th class="p-2 border">Správne</th>
            <th class="p-2 border">Presnosť</th>
            <th class="p-2 border">Pokusy</th>
            <th class="p-2 border">Priem. čas (ms)</th>
            <th class="p-2 border">Posledné cvičenie</th>
            <th class="p-2 border">Detail</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="st in allStudents" :key="st.student_id">
            <td class="border p-2 font-semibold">{{ st.username }}</td>
            <td class="border p-2 text-center">{{ st.total_examples }}</td>
            <td class="border p-2 text-center">{{ st.solved_count }}</td>
            <td class="border p-2 text-center">
              <span :class="accuracyColor(st.accuracy)">{{ formatPercent(st.accuracy) }}</span>
            </td>
            <td class="border p-2 text-center">{{ st.total_attempts }}</td>
            <td class="border p-2 text-center">{{ formatDuration(st.avg_duration_ms) }}</td>
            <td class="border p-2 text-center">{{ formatDate(st.last_practiced) }}</td>
            <td class="border p-2 text-center">
              <button @click="viewStudentDetail(st.student_id)" class="text-blue-600 underline">Zobraziť</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="allStudents.length === 0" class="mt-4 text-gray-500">Žiadni študenti v databáze.</div>
    </div>

    <!-- Single Student Skill Breakdown -->
    <div v-else>
      <h2 class="text-xl font-semibold mb-3">Detail študenta ID: {{ studentId }}</h2>
      <button @click="backToAll" class="text-blue-600 underline mb-3">← Späť na zoznam študentov</button>
      <table class="min-w-full border mt-4">
        <thead>
          <tr class="bg-gray-100">
            <th class="p-2 border">Zručnosť</th>
            <th class="p-2 border">Pokusy</th>
            <th class="p-2 border">Správne</th>
            <th class="p-2 border">Presnosť</th>
            <th class="p-2 border">Mastery</th>
            <th class="p-2 border">Priem. pokusy</th>
            <th class="p-2 border">Priem. čas (ms)</th>
            <th class="p-2 border">Posledné cvičenie</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in skills" :key="row.skill_id">
            <td class="border p-2">{{ row.skill_name }}</td>
            <td class="border p-2 text-center">{{ row.examples_practiced }}</td>
            <td class="border p-2 text-center">{{ row.solved_count }}</td>
            <td class="border p-2 text-center">
              <span :class="accuracyColor(row.accuracy)">{{ formatPercent(row.accuracy) }}</span>
            </td>
            <td class="border p-2 text-center">
              <span :class="masteryColor(row.mastery_mean)">{{ formatPercent(row.mastery_mean) }}</span>
            </td>
            <td class="border p-2 text-center">{{ formatValue(row.avg_attempts_per_example) }}</td>
            <td class="border p-2 text-center">{{ formatDuration(row.avg_duration_ms) }}</td>
            <td class="border p-2 text-center">{{ formatDate(row.last_practiced) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="skills.length === 0" class="mt-4 text-gray-500">Žiadne dáta pre tohto študenta.</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { getStudentSkillStats, getAllStudentsStats } from '../api/apiClient'

const studentId = ref('')
const skills = ref([])
const allStudents = ref([])
const loading = ref(false)
const error = ref('')
const showingAllStudents = ref(true)

function fetchData() {
  if (!studentId.value) {
    // Load all students
    loading.value = true
    error.value = ''
    showingAllStudents.value = true
    getAllStudentsStats()
      .then(data => {
        allStudents.value = data
        loading.value = false
      })
      .catch(e => {
        error.value = e.message || 'Chyba pri načítaní študentov.'
        loading.value = false
      })
  } else {
    // Load single student detail
    loading.value = true
    error.value = ''
    showingAllStudents.value = false
    getStudentSkillStats(studentId.value)
      .then(data => {
        skills.value = data
        loading.value = false
      })
      .catch(e => {
        error.value = e.message || 'Chyba pri načítaní dát.'
        loading.value = false
      })
  }
}

function viewStudentDetail(id) {
  studentId.value = id
  fetchData()
}

function backToAll() {
  studentId.value = ''
  fetchData()
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

function formatPercent(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '-'
  return `${(numeric * 100).toFixed(1)}%`
}

function formatDuration(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '-'
  return Math.round(numeric)
}

function formatValue(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '-'
  return numeric
}

function formatDate(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleString()
}

// Auto-load all students on mount
fetchData()
</script>

<style scoped>
table { border-collapse: collapse; }
th, td { text-align: left; }
</style>
