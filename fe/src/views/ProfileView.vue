<!--
================================================================================
 Component: ProfileView.vue
 Description:
        When logged in: shows student profile (level, XP, rank, badges).
        When logged out: shows login / signup form.
================================================================================
-->

<script setup>
import Signup from '@/components/Profile/Signup.vue'
import Login from '@/components/Profile/Login.vue'
import { useAuthStore } from '@/stores/useAuthStore'
import { useGamificationStore } from '@/stores/useGamificationStore'
import { useLanguageStore } from '@/stores/useLanguageStore'
import { dictionary } from '@/utils/dictionary'
import { RouterLink } from 'vue-router'
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { updateStudentGrade } from '@/api/apiClient'

const authStore = useAuthStore()
const gamStore = useGamificationStore()
const langStore = useLanguageStore()
const showLogin = ref(true)

const ICON_MAP = {
  star: '🌟', ten: '🔢', hundred: '💯', rocket: '🚀', map: '🗺️', compass: '🧭',
  target: '🎯', bolt: '⚡', bow: '🏹', grad: '🎓', muscle: '💪',
  wind: '💨', car: '🏎️', fire: '🔥', trophy: '🏆', star2: '⭐', crown: '👑', medal: '🥇',
  gem: '💎', books: '📚', calendar: '📅',
}
function iconEmoji(key) { return ICON_MAP[key] || '🏅' }

const categories = [
  { key: 'activity', label: 'Aktivita', icon: '📚' },
  { key: 'accuracy', label: 'Presnosť', icon: '🎯' },
  { key: 'speed', label: 'Rýchlosť', icon: '⚡' },
  { key: 'streak', label: 'Séria', icon: '🔥' },
  { key: 'milestone', label: 'Míľniky', icon: '🏆' },
]

const allBadges = ref([])
const loadingBadges = ref(false)

const earnedBadges = computed(() => allBadges.value.filter(b => b.earned))
const unearnedBadges = computed(() => allBadges.value.filter(b => !b.earned))

// Simple deterministic color from username for the avatar circle
function avatarColor(name) {
  const colors = ['bg-violet-500', 'bg-indigo-500', 'bg-blue-500', 'bg-teal-500', 'bg-green-500', 'bg-amber-500', 'bg-orange-500', 'bg-pink-500']
  let hash = 0
  for (const c of (name || '')) hash = (hash * 31 + c.charCodeAt(0)) & 0xffff
  return colors[hash % colors.length]
}

// Grade change
const gradeChanging = ref(false)
const gradeChangeError = ref('')
const selectedGrade = ref(null)

async function saveGrade() {
  if (!selectedGrade.value) return
  gradeChanging.value = true
  gradeChangeError.value = ''
  try {
    const res = await updateStudentGrade(authStore.id, selectedGrade.value)
    authStore.grade = res.grade
    authStore.grade_change_used = res.grade_change_used
    localStorage.setItem('grade', JSON.stringify(res.grade))
    localStorage.setItem('grade_change_used', JSON.stringify(res.grade_change_used))
    selectedGrade.value = null
  } catch (e) {
    gradeChangeError.value = typeof e === 'string' ? e : 'Chyba pri zmene ročníka'
  }
  gradeChanging.value = false
}

onMounted(async () => {
  if (!authStore.isAuthenticated || authStore.role === 'admin') return
  if (authStore.id) gamStore.fetchStats(authStore.id)
  loadingBadges.value = true
  try {
    const res = await axios.get('/api/gamification/badges/', { params: { student_id: authStore.id } })
    allBadges.value = res.data
  } catch (e) {
    console.error('ProfileView: failed to load badges', e)
  }
  loadingBadges.value = false
})
</script>

<template>
  <!-- ── Logged in: student profile ── -->
  <div v-if="authStore.isAuthenticated && authStore.role !== 'admin'" class="min-h-screen bg-gradient-to-b from-violet-50 to-white p-4 md:p-8">
    <div class="max-w-2xl mx-auto">

      <!-- Avatar + username -->
      <div class="flex flex-col items-center mb-8">
        <div
          class="w-24 h-24 rounded-full flex items-center justify-center text-white text-4xl font-black shadow-lg mb-3"
          :class="avatarColor(authStore.name)">
          {{ (authStore.name || '?')[0].toUpperCase() }}
        </div>
        <h1 class="text-3xl font-black text-gray-800">{{ authStore.name }}</h1>
      </div>

      <!-- Level / XP / Streak / Rank cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <!-- Level + XP bar -->
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

      <!-- Grade card + one-time change -->
      <div class="bg-white rounded-2xl shadow p-5 mb-6">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-lg font-bold text-gray-700">🎓 Môj ročník</h2>
          <span v-if="authStore.grade" class="text-2xl font-black text-indigo-600">{{ authStore.grade }}. ročník</span>
          <span v-else class="text-sm text-gray-400 italic">nenastavený</span>
        </div>

        <!-- Change allowed once -->
        <div v-if="!authStore.grade_change_used">
          <p class="text-xs text-gray-400 mb-3">
            {{ authStore.grade ? 'Raz môžeš zmeniť svoj ročník:' : 'Nastav svoj ročník:' }}
          </p>
          <div class="grid grid-cols-9 gap-1 mb-3">
            <button
              v-for="g in 9"
              :key="g"
              @click="selectedGrade = selectedGrade === g ? null : g"
              class="py-2 rounded-lg text-sm font-bold border-2 transition"
              :class="selectedGrade === g
                ? 'bg-indigo-600 border-indigo-700 text-white'
                : 'bg-gray-100 border-gray-300 text-gray-500 hover:bg-indigo-50 hover:border-indigo-300'">
              {{ g }}
            </button>
          </div>
          <button
            :disabled="!selectedGrade || gradeChanging"
            @click="saveGrade"
            class="w-full py-2 rounded-xl font-bold text-sm transition"
            :class="selectedGrade && !gradeChanging
              ? 'bg-indigo-600 text-white hover:bg-indigo-700'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'">
            {{ gradeChanging ? 'Ukladám...' : (authStore.grade ? 'Zmeniť ročník' : 'Nastaviť ročník') }}
          </button>
          <p v-if="gradeChangeError" class="text-red-500 text-xs mt-2">{{ gradeChangeError }}</p>
          <p v-if="authStore.grade" class="text-xs text-amber-600 mt-2">⚠️ Túto zmenu môžeš urobiť len raz.</p>
        </div>
        <div v-else class="text-xs text-gray-400 italic mt-1">Ročník bol už zmenený a viac ho nie je možné meniť.</div>
      </div>

      <!-- Badges -->
      <div class="bg-white rounded-2xl shadow p-6">
        <div class="flex items-center justify-between mb-1">
          <h2 class="text-xl font-bold text-gray-700">🎖️ Odznaky</h2>
          <span class="text-sm font-semibold text-violet-600 bg-violet-50 px-3 py-1 rounded-full">
            {{ earnedBadges.length }} / {{ allBadges.length }}
          </span>
        </div>

        <div v-if="loadingBadges" class="text-center py-8 text-gray-400">
          <i class="fa-solid fa-spinner fa-spin text-3xl"></i>
        </div>

        <div v-else>
          <!-- Earned badges — prominent flex grid -->
          <div v-if="earnedBadges.length > 0" class="mb-6">
            <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Získané odznaky</p>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div
                v-for="badge in earnedBadges"
                :key="badge.key"
                class="rounded-2xl p-4 flex flex-col items-center text-center bg-gradient-to-br from-violet-50 to-indigo-50 border-2 border-violet-400 shadow-md ring-2 ring-violet-200 transition-transform hover:scale-105">
                <div class="text-5xl mb-2 drop-shadow">{{ iconEmoji(badge.icon) }}</div>
                <div class="font-extrabold text-gray-800 text-sm leading-tight">{{ badge.name }}</div>
                <div class="text-xs text-gray-500 mt-1 leading-snug">{{ badge.description }}</div>
                <div class="mt-2 text-xs font-bold text-violet-600">+{{ badge.xp_reward }} XP</div>
              </div>
            </div>
          </div>

          <div v-else class="text-center py-6 text-gray-400 text-sm mb-4">
            Zatiaľ žiadne odznaky. Riešte príklady a získajte prvý! 💪
          </div>

          <!-- Unearned badges — always visible with description -->
          <div v-if="unearnedBadges.length > 0" class="border-t border-gray-100 mt-4 pt-4">
            <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">🔒 Ešte neodomknuté ({{ unearnedBadges.length }})</p>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
              <div
                v-for="badge in unearnedBadges"
                :key="badge.key"
                class="rounded-2xl p-3 flex flex-col items-center text-center bg-gray-50 border-2 border-dashed border-gray-300 opacity-70">
                <div class="text-3xl mb-1 grayscale">{{ iconEmoji(badge.icon) }}</div>
                <div class="font-bold text-gray-500 text-xs leading-tight">{{ badge.name }}</div>
                <div class="text-xs text-gray-400 mt-1 leading-snug italic">{{ badge.description }}</div>
                <div class="mt-1 text-xs font-semibold text-gray-400">+{{ badge.xp_reward }} XP</div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- ── Logged out: login / signup ── -->
  <div v-else class="pt-12">
    <Login v-if="showLogin" />
    <Signup v-else />

    <button @click="showLogin = !showLogin" class="underline w-full text-secondary text-lg">
      {{ showLogin ? dictionary[langStore.language].registerText : dictionary[langStore.language].loginText }}
    </button>

    <RouterLink to="/admin" class="underline w-full text-secondary text-lg mt-12 flex justify-center">
      {{ dictionary[langStore.language].adminText }}
    </RouterLink>
  </div>
</template>
