<template>
  <div class="p-6 max-w-7xl mx-auto">
    <h1 class="text-2xl font-bold mb-4">Moje zaznamenané dáta</h1>

    <div class="mb-4 grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
      <div>
        <label class="block text-sm font-semibold mb-1">Typ identity</label>
        <select v-model="identityType" class="border rounded px-3 py-2 w-full">
          <option value="student">Študent</option>
          <option value="session">Session ID</option>
        </select>
      </div>

      <div class="md:col-span-2">
        <label class="block text-sm font-semibold mb-1">
          {{ identityType === 'student' ? 'Filter študentov (meno alebo ID)' : 'Session ID' }}
        </label>
        <input
          v-model="filterText"
          type="text"
          class="border rounded px-3 py-2 w-full"
          :placeholder="identityType === 'student' ? 'napr. jan alebo 12' : 'napr. session_id z localStorage'"
          @keyup.enter="identityType === 'session' ? loadData() : null"
        />
      </div>

      <div>
        <button
          @click="identityType === 'session' ? loadData() : null"
          class="bg-blue-600 text-white px-4 py-2 rounded w-full"
          :class="identityType === 'student' ? 'opacity-60 cursor-not-allowed' : ''"
        >
          Načítať
        </button>
      </div>
    </div>

    <div v-if="identityType === 'student'" class="border rounded-lg p-4 mb-6">
      <h2 class="text-lg font-semibold mb-3">Všetci študenti</h2>
      <div v-if="studentsLoading" class="text-gray-500">Načítavam študentov...</div>
      <div v-else-if="allStudents.length === 0" class="text-gray-500">Žiadni študenti v databáze.</div>
      <div v-else class="max-h-64 overflow-auto border rounded">
        <table class="min-w-full border-collapse text-sm">
          <thead>
            <tr class="bg-gray-100">
              <th class="p-2 border">Meno</th>
              <th class="p-2 border text-center">ID</th>
              <th class="p-2 border text-center">Pokusy</th>
              <th class="p-2 border text-center">Presnosť</th>
              <th class="p-2 border text-center">Akcia</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="student in filteredStudents" :key="student.student_id">
              <td class="p-2 border font-semibold">{{ student.username }}</td>
              <td class="p-2 border text-center">{{ student.student_id }}</td>
              <td class="p-2 border text-center">{{ student.total_examples }}</td>
              <td class="p-2 border text-center">{{ formatPercent(student.accuracy) }}</td>
              <td class="p-2 border text-center">
                <button
                  class="text-blue-600 underline"
                  @click="selectStudent(student)"
                >
                  Zobraziť dáta
                </button>
              </td>
            </tr>
            <tr v-if="filteredStudents.length === 0">
              <td colspan="5" class="p-4 text-center text-gray-500">Žiadny študent podľa filtra.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="identityType === 'session'" class="border rounded-lg p-4 mb-6">
      <h2 class="text-lg font-semibold mb-3">Všetci anonymní používatelia</h2>
      <div v-if="anonymousLoading" class="text-gray-500">Načítavam anonymné sessions...</div>
      <div v-else-if="allAnonymousSessions.length === 0" class="text-gray-500">Žiadne anonymné sessions v databáze.</div>
      <div v-else class="max-h-64 overflow-auto border rounded">
        <table class="min-w-full border-collapse text-sm">
          <thead>
            <tr class="bg-gray-100">
              <th class="p-2 border">Používateľ</th>
              <th class="p-2 border text-center">Pokusy</th>
              <th class="p-2 border text-center">Presnosť</th>
              <th class="p-2 border text-center">Posledná aktivita</th>
              <th class="p-2 border text-center">Akcia</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="session in filteredAnonymousSessions" :key="session.session_id">
              <td class="p-2 border font-semibold">{{ session.display_name }}</td>
              <td class="p-2 border text-center">{{ session.total_attempts }}</td>
              <td class="p-2 border text-center">{{ formatPercent(session.accuracy) }}</td>
              <td class="p-2 border text-center">{{ formatDate(session.last_activity) }}</td>
              <td class="p-2 border text-center">
                <button
                  class="text-blue-600 underline"
                  @click="selectAnonymousSession(session)"
                >
                  Zobraziť dáta
                </button>
              </td>
            </tr>
            <tr v-if="filteredAnonymousSessions.length === 0">
              <td colspan="5" class="p-4 text-center text-gray-500">Žiadny anonym podľa filtra.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="loading" class="text-gray-500">Načítavam...</div>
    <div v-else-if="error" class="text-red-600 mb-4">{{ error }}</div>

    <div v-if="data" class="space-y-6">
      <div class="border rounded-lg p-4 bg-gray-50">
        <h2 class="text-lg font-semibold mb-3">Súhrn</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div><span class="font-semibold">Používateľ:</span> {{ displayUserLabel }}</div>
          <div><span class="font-semibold">Typ:</span> {{ data.user_type }}</div>
          <div><span class="font-semibold">Pokusy:</span> {{ data.summary?.total_attempts ?? 0 }}</div>
          <div><span class="font-semibold">Vyhodnotené:</span> {{ data.summary?.evaluated_count ?? 0 }}</div>
          <div><span class="font-semibold">Správne:</span> {{ data.summary?.correct_count ?? 0 }}</div>
          <div><span class="font-semibold">Nesprávne:</span> {{ data.summary?.incorrect_count ?? 0 }}</div>
          <div><span class="font-semibold">Presnosť:</span> {{ formatPercent(data.summary?.accuracy) }}</div>
          <div><span class="font-semibold">Priem. čas:</span> {{ Math.round(data.summary?.avg_duration_ms ?? 0) }} ms</div>
        </div>
      </div>

      <div class="border rounded-lg p-4">
        <h2 class="text-lg font-semibold mb-3">Všetky pokusy</h2>
        <div class="overflow-x-auto">
          <table class="min-w-full border-collapse text-sm">
            <thead>
              <tr class="bg-gray-100">
                <th class="p-2 border">Čas</th>
                <th class="p-2 border">Príklad</th>
                <th class="p-2 border">Transcript</th>
                <th class="p-2 border">Tvoja odpoveď</th>
                <th class="p-2 border">Správna odpoveď</th>
                <th class="p-2 border">Správne</th>
                <th class="p-2 border">Čas (ms)</th>
                <th class="p-2 border">Kategórie</th>
                <th class="p-2 border">Párovaný záznam (audio + JSON)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="attempt in data.all_attempts" :key="attempt.attempt_id">
                <td class="p-2 border whitespace-nowrap">{{ formatDate(attempt.timestamp) }}</td>
                <td class="p-2 border">{{ attempt.example_problem }}</td>
                <td class="p-2 border">{{ attempt.transcription }}</td>
                <td class="p-2 border">{{ attempt.your_answer }}</td>
                <td class="p-2 border">{{ attempt.correct_answer }}</td>
                <td class="p-2 border text-center">
                  <span v-if="attempt.is_correct === true" class="text-green-700 font-semibold">Áno</span>
                  <span v-else-if="attempt.is_correct === false" class="text-red-700 font-semibold">Nie</span>
                  <span v-else class="text-gray-500">-</span>
                </td>
                <td class="p-2 border text-center">{{ attempt.duration_ms }}</td>
                <td class="p-2 border">{{ (attempt.practiced_skills?.names || []).join(', ') }}</td>
                <td class="p-2 border">
                  <div v-if="attempt.audio_url || attempt.paired_json_url" class="space-y-2 min-w-56">
                    <audio :src="attempt.audio_url" controls preload="none" class="w-full" />
                    <div class="flex items-center gap-2 text-xs">
                      <a
                        v-if="attempt.paired_json_url"
                        :href="attempt.paired_json_url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-blue-600 underline"
                      >
                        JSON sidecar
                      </a>
                      <span v-else class="text-gray-500">JSON sidecar: -</span>
                    </div>
                    <div class="text-xs text-gray-600 break-all">{{ attempt.audio_file || '' }}</div>
                  </div>
                  <span v-else class="text-gray-500">-</span>
                </td>
              </tr>
              <tr v-if="!data.all_attempts || data.all_attempts.length === 0">
                <td colspan="9" class="p-4 text-center text-gray-500">Žiadne pokusy.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="border rounded-lg p-4 bg-gray-50">
        <h2 class="text-lg font-semibold mb-3">Raw JSON</h2>
        <pre class="text-xs overflow-auto whitespace-pre-wrap break-all">{{ prettyJson }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getAllAnonymousSessionsStats, getAllStudentsStats, getMyData } from '@/api/apiClient'

const identityType = ref('student')
const identityValue = ref('')
const filterText = ref('')
const loading = ref(false)
const studentsLoading = ref(false)
const anonymousLoading = ref(false)
const error = ref('')
const data = ref(null)
const selectedStudentName = ref('')
const allStudents = ref([])
const allAnonymousSessions = ref([])

const filteredStudents = computed(() => {
  const text = (filterText.value || '').trim().toLowerCase()
  if (!text) return allStudents.value

  return allStudents.value.filter((student) => {
    const username = (student.username || '').toLowerCase()
    const idString = String(student.student_id || '')
    return username.includes(text) || idString.includes(text)
  })
})

const filteredAnonymousSessions = computed(() => {
  const text = (filterText.value || '').trim().toLowerCase()
  if (!text) return allAnonymousSessions.value

  return allAnonymousSessions.value.filter((session) => {
    const displayName = (session.display_name || '').toLowerCase()
    const idText = (session.session_id || '').toLowerCase()
    return displayName.includes(text) || idText.includes(text)
  })
})

const prettyJson = computed(() => {
  if (!data.value) return ''
  return JSON.stringify(data.value, null, 2)
})

const displayUserLabel = computed(() => {
  if (!data.value) return '-'
  if (data.value.user_type === 'anonymous_session') {
    const raw = String(data.value.user_id || '')
    const suffix = raw.slice(0, 6) || 'unknown'
    return `anonym${suffix}`
  }
  return selectedStudentName.value || String(data.value.user_id || '-')
})

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function formatPercent(value) {
  if (value === null || value === undefined) return '-'
  return `${(value * 100).toFixed(1)}%`
}

async function loadStudents() {
  studentsLoading.value = true
  try {
    allStudents.value = await getAllStudentsStats()
  } catch (e) {
    error.value = typeof e === 'string' ? e : 'Chyba pri načítaní študentov.'
  } finally {
    studentsLoading.value = false
  }
}

async function loadAnonymousSessions() {
  anonymousLoading.value = true
  try {
    allAnonymousSessions.value = await getAllAnonymousSessionsStats()
  } catch (e) {
    error.value = typeof e === 'string' ? e : 'Chyba pri načítaní anonymných sessions.'
  } finally {
    anonymousLoading.value = false
  }
}

async function selectStudent(student) {
  identityType.value = 'student'
  identityValue.value = String(student.student_id)
  selectedStudentName.value = student.username
  await loadData()
}

async function selectAnonymousSession(session) {
  identityType.value = 'session'
  filterText.value = String(session.session_id || '')
  selectedStudentName.value = session.display_name || ''
  await loadData()
}

async function loadData() {
  if (identityType.value === 'student' && !identityValue.value) {
    error.value = 'Vyber študenta zo zoznamu.'
    return
  }

  if (identityType.value === 'session' && !filterText.value) {
    error.value = 'Zadaj student_id alebo session_id.'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const payload = identityType.value === 'student'
      ? { student_id: identityValue.value }
      : { session_id: filterText.value }

    data.value = await getMyData(payload)
  } catch (e) {
    error.value = typeof e === 'string' ? e : 'Chyba pri načítaní dát.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStudents()
  loadAnonymousSessions()
})
</script>

<style scoped>
table { border-collapse: collapse; }
th, td { text-align: left; vertical-align: top; }
</style>
