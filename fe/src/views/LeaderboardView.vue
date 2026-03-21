<template>
  <div class="min-h-screen bg-gradient-to-b from-indigo-50 to-white p-4 md:p-8">
    <div class="max-w-2xl mx-auto">

      <!-- Header -->
      <div class="text-center mb-6">
        <div class="text-6xl mb-2">🏆</div>
        <h1 class="text-4xl font-black text-indigo-700">{{ dictionary[langStore.language].leaderboard }}</h1>
        <p class="text-gray-500 mt-1">{{ dictionary[langStore.language].topStudents }}</p>
      </div>

      <!-- Tabs -->
      <div class="flex bg-white rounded-2xl shadow-sm p-1 mb-6 gap-1">
        <button
          @click="activeTab = 'xp'"
          class="flex-1 py-2 rounded-xl font-bold text-sm transition-all"
          :class="activeTab === 'xp' ? 'bg-indigo-600 text-white shadow' : 'text-gray-500 hover:text-indigo-600'">
          ⭐ Podľa XP
        </button>
        <button
          @click="switchToAccuracy"
          class="flex-1 py-2 rounded-xl font-bold text-sm transition-all"
          :class="activeTab === 'accuracy' ? 'bg-indigo-600 text-white shadow' : 'text-gray-500 hover:text-indigo-600'">
          🎯 Podľa presnosti
        </button>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-16">
        <div class="text-5xl mb-4 animate-spin">⏳</div>
      </div>

      <!-- Empty -->
      <div v-else-if="currentList.length === 0" class="text-center py-16">
        <div class="text-6xl mb-4">🌱</div>
        <p class="text-gray-600 text-xl font-semibold">Zatiaľ tu nikto nie je. Buď prvý!</p>
        <router-link
          to="/"
          class="inline-block mt-6 px-8 py-3 bg-indigo-600 text-white rounded-2xl font-bold text-lg hover:bg-indigo-700 transition">
          {{ dictionary[langStore.language].practiceNow }}
        </router-link>
      </div>

      <!-- List -->
      <div v-else class="space-y-3">
        <div
          v-for="entry in currentList"
          :key="entry.student_id"
          class="bg-white rounded-2xl shadow-md p-4 flex items-center gap-4 transition-all hover:shadow-lg"
          :class="{
            'border-4 border-yellow-400 bg-yellow-50': entry.rank === 1,
            'border-4 border-gray-400 bg-gray-50': entry.rank === 2,
            'border-4 border-amber-600 bg-amber-50': entry.rank === 3,
            'border-2 border-indigo-400 bg-indigo-50': authStore.id && entry.student_id === authStore.id && entry.rank > 3,
          }">

          <!-- Rank badge -->
          <div class="text-3xl font-black w-12 text-center flex-shrink-0">
            <span v-if="entry.rank === 1">🥇</span>
            <span v-else-if="entry.rank === 2">🥈</span>
            <span v-else-if="entry.rank === 3">🥉</span>
            <span v-else class="text-gray-500 text-xl">#{{ entry.rank }}</span>
          </div>

          <!-- Student info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-bold text-lg text-gray-800 truncate">{{ entry.username }}</span>
              <span
                v-if="authStore.id && entry.student_id === authStore.id"
                class="text-xs bg-indigo-500 text-white px-2 py-0.5 rounded-full flex-shrink-0">
                Ty
              </span>
            </div>
            <div class="flex items-center gap-3 text-sm text-gray-500 mt-1 flex-wrap">
              <span>⭐ {{ dictionary[langStore.language].level }} {{ entry.level }}</span>
              <span>✅ {{ entry.solved_count }}</span>
              <span v-if="entry.current_streak > 1">🔥 {{ entry.current_streak }} {{ dictionary[langStore.language].days }}</span>
            </div>
          </div>

          <!-- Score -->
          <div class="text-right flex-shrink-0">
            <template v-if="activeTab === 'xp'">
              <div class="text-2xl font-black text-indigo-600">{{ entry.total_xp }}</div>
              <div class="text-xs text-gray-400 uppercase tracking-wide">XP</div>
            </template>
            <template v-else>
              <div class="text-2xl font-black text-indigo-600">{{ (entry.accuracy * 100).toFixed(1) }}%</div>
              <div class="text-xs text-gray-400 uppercase tracking-wide">presnosť</div>
            </template>
          </div>
        </div>
      </div>

      <!-- My rank when outside top 20 (XP tab only) -->
      <div
        v-if="activeTab === 'xp' && gamStore.rank && gamStore.rank > 20 && authStore.isAuthenticated && authStore.role !== 'admin'"
        class="mt-6 bg-indigo-50 rounded-2xl p-4 border-2 border-indigo-300 text-center">
        <span class="text-gray-600">{{ dictionary[langStore.language].myRank }}: </span>
        <span class="font-bold text-indigo-700 text-xl">#{{ gamStore.rank }}</span>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/useAuthStore'
import { useGamificationStore } from '@/stores/useGamificationStore'
import { useLanguageStore } from '@/stores/useLanguageStore'
import { dictionary } from '@/utils/dictionary'
import axios from 'axios'

const authStore = useAuthStore()
const gamStore = useGamificationStore()
const langStore = useLanguageStore()

const loading = ref(true)
const activeTab = ref('xp')
const accuracyList = ref([])
const accuracyLoaded = ref(false)

const currentList = computed(() =>
  activeTab.value === 'xp' ? gamStore.leaderboard : accuracyList.value
)

async function switchToAccuracy() {
  activeTab.value = 'accuracy'
  if (accuracyLoaded.value) return
  loading.value = true
  try {
    const res = await axios.get('/api/gamification/leaderboard/accuracy/')
    accuracyList.value = res.data
  } catch (e) {
    console.error('LeaderboardView: failed to load accuracy leaderboard', e)
  }
  accuracyLoaded.value = true
  loading.value = false
}

onMounted(async () => {
  await gamStore.fetchLeaderboard()
  if (authStore.id) await gamStore.fetchStats(authStore.id)
  loading.value = false
})
</script>
