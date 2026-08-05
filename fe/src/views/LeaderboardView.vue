<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900 p-4 md:p-8">
    <div class="max-w-2xl mx-auto">

      <!-- Card wrapper -->
      <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] p-6 sm:p-8">

        <!-- Header -->
        <div class="mb-6">
          <h2 class="text-3xl font-black text-slate-800 dark:text-slate-100 tracking-tight mb-1">
            {{ t('leaderboard') }} 🏆
          </h2>
          <p class="text-slate-500 font-medium">{{ t('topStudents') }}</p>
        </div>

        <!-- Tabs -->
        <div class="flex gap-3 mb-6 bg-slate-100 dark:bg-slate-700 p-2 rounded-2xl">
          <button
            @click="activeTab = 'xp'"
            class="flex-1 py-3 rounded-xl font-black text-sm transition-all"
            :class="activeTab === 'xp'
              ? 'bg-white dark:bg-slate-600 text-slate-800 dark:text-slate-100 shadow-sm border-2 border-slate-200 dark:border-slate-500 border-b-[4px]'
              : 'text-slate-500 dark:text-slate-400 hover:bg-slate-200/50 dark:hover:bg-slate-600/50'">
            {{ t('byXpLabel') }}
          </button>
          <button
            @click="activeTab = 'grade'"
            class="flex-1 py-3 rounded-xl font-black text-sm transition-all"
            :class="activeTab === 'grade'
              ? 'bg-white dark:bg-slate-600 text-slate-800 dark:text-slate-100 shadow-sm border-2 border-slate-200 dark:border-slate-500 border-b-[4px]'
              : 'text-slate-500 dark:text-slate-400 hover:bg-slate-200/50 dark:hover:bg-slate-600/50'">
            {{ t('byGradeLink') }}
          </button>
        </div>

        <!-- Grade picker -->
        <div v-if="activeTab === 'grade'" class="mb-6">
          <p class="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">{{ t('pickGradeLabel') }}</p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="g in 9"
              :key="g"
              @click="loadGrade(g)"
              class="w-12 h-12 rounded-2xl font-black text-lg transition-all"
              :class="selectedGrade === g
                ? 'bg-violet-500 text-white border-b-[4px] border-violet-700'
                : 'bg-slate-100 text-slate-600 border-b-[4px] border-slate-300 hover:bg-slate-200 active:border-b-0 active:translate-y-1'">
              {{ g }}
            </button>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="showLoading" class="text-center py-16 text-slate-400">
          <i class="fa-solid fa-spinner fa-spin text-3xl"></i>
        </div>

        <!-- Empty -->
        <div v-else-if="currentList.length === 0" class="text-center py-16">
          <p class="text-slate-500 text-lg font-bold mb-4">{{ t('leaderboardEmptyText') }}</p>
          <router-link
            to="/"
            class="inline-block px-6 py-3 bg-violet-500 text-white rounded-2xl font-black text-sm
                   border-b-[4px] border-violet-700 hover:-translate-y-0.5 transition-transform">
            {{ t('practiceNow') }}
          </router-link>
        </div>

        <template v-else>
          <!-- Top 3 Podium -->
          <div class="flex justify-center items-end gap-2 sm:gap-4 mb-8 pt-6">

            <!-- 2nd Place -->
            <div v-if="currentList.length >= 2" class="flex flex-col items-center w-1/3 group">
              <div class="relative mb-3 group-hover:-translate-y-2 transition-transform">
                <div class="w-16 h-16 sm:w-20 sm:h-20 rounded-3xl bg-slate-200 flex items-center justify-center
                            font-black text-slate-500 text-xl border-4 border-slate-300 shadow-sm">
                  {{ currentList[1].username.substring(0, 2).toUpperCase() }}
                </div>
                <div class="absolute -bottom-3 -right-3 w-8 h-8 bg-slate-400 rounded-xl flex items-center
                            justify-center text-white text-sm font-black border-4 border-white shadow-sm rotate-[-10deg]">
                  2
                </div>
              </div>
              <p class="font-black text-sm sm:text-base text-slate-700 dark:text-slate-200 truncate w-full text-center px-1">
                {{ currentList[1].username }}
              </p>
              <p class="font-bold text-violet-600 dark:text-violet-300 bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 rounded-lg mt-1 text-sm">
                {{ currentList[1].total_xp }} XP
              </p>
            </div>

            <!-- 1st Place -->
            <div v-if="currentList.length >= 1" class="flex flex-col items-center w-1/3 z-10 group">
              <div class="relative mb-3 -mt-6 group-hover:-translate-y-2 transition-transform">
                <div class="absolute -top-6 left-1/2 -translate-x-1/2 text-2xl animate-bounce">👑</div>
                <div class="w-20 h-20 sm:w-28 sm:h-28 rounded-3xl bg-amber-400 flex items-center justify-center
                            font-black text-amber-900 text-3xl border-4 border-amber-300 shadow-lg">
                  {{ currentList[0].username.substring(0, 2).toUpperCase() }}
                </div>
                <div class="absolute -bottom-3 -right-3 w-10 h-10 bg-amber-500 rounded-xl flex items-center
                            justify-center text-white text-lg font-black border-4 border-white shadow-sm rotate-[10deg]">
                  1
                </div>
              </div>
              <p class="font-black text-base sm:text-lg text-slate-800 dark:text-slate-100 truncate w-full text-center px-1">
                {{ currentList[0].username }}
              </p>
              <p class="font-black text-amber-600 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/40 px-3 py-1 rounded-xl mt-1">
                {{ currentList[0].total_xp }} XP
              </p>
            </div>

            <!-- 3rd Place -->
            <div v-if="currentList.length >= 3" class="flex flex-col items-center w-1/3 group">
              <div class="relative mb-3 group-hover:-translate-y-2 transition-transform">
                <div class="w-16 h-16 sm:w-20 sm:h-20 rounded-3xl bg-orange-300 flex items-center justify-center
                            font-black text-orange-900 text-xl border-4 border-orange-200 shadow-sm">
                  {{ currentList[2].username.substring(0, 2).toUpperCase() }}
                </div>
                <div class="absolute -bottom-3 -right-3 w-8 h-8 bg-orange-500 rounded-xl flex items-center
                            justify-center text-white text-sm font-black border-4 border-white shadow-sm rotate-[10deg]">
                  3
                </div>
              </div>
              <p class="font-black text-sm sm:text-base text-slate-700 dark:text-slate-200 truncate w-full text-center px-1">
                {{ currentList[2].username }}
              </p>
              <p class="font-bold text-violet-600 dark:text-violet-300 bg-violet-100 dark:bg-violet-900/40 px-2 py-0.5 rounded-lg mt-1 text-sm">
                {{ currentList[2].total_xp }} XP
              </p>
            </div>
          </div>

          <!-- Rest of list (4th+) -->
          <div class="space-y-3">
            <div
              v-for="entry in currentList.slice(3)"
              :key="entry.student_id"
              class="rounded-2xl p-4 transition-all hover:-translate-y-0.5"
              :class="isMe(entry)
                ? 'bg-violet-50 border-[3px] border-violet-200 border-b-[6px] shadow-sm'
                : 'bg-slate-50 dark:bg-slate-700/50 border-2 border-slate-100 dark:border-slate-700 hover:border-slate-200 dark:hover:border-slate-600'">
              <div class="flex items-center gap-4">
                <!-- Rank -->
                <div class="w-12 h-12 rounded-2xl bg-slate-200 dark:bg-slate-600 border-b-[4px] border-slate-300 dark:border-slate-500 flex items-center
                            justify-center text-slate-600 dark:text-slate-200 font-black text-lg flex-shrink-0">
                  {{ entry.rank }}
                </div>
                <!-- User info -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-0.5">
                    <p class="font-black text-lg truncate" :class="isMe(entry) ? 'text-violet-900' : 'text-slate-700'">
                      {{ entry.username }}
                    </p>
                    <span v-if="isMe(entry)"
                      class="text-[10px] bg-violet-500 text-white px-2.5 py-1 rounded-lg font-black uppercase tracking-wider shadow-sm flex-shrink-0">
                      {{ t('thatsYouLabel') }}
                    </span>
                  </div>
                  <p class="text-sm font-bold text-slate-400">
                    Lvl {{ entry.level }} · {{ entry.solved_count }} {{ t('correctSuffix') }}
                    <span v-if="entry.current_streak > 1"> · {{ entry.current_streak }}{{ t('dayStreakAbbrSuffix') }}</span>
                  </p>
                </div>
                <!-- XP -->
                <div class="flex-shrink-0 text-right bg-white dark:bg-slate-700 px-4 py-2 rounded-xl border-2 border-slate-100 dark:border-slate-600">
                  <p class="font-black text-violet-600 text-lg">{{ entry.total_xp }}</p>
                  <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest">XP</p>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- My rank when outside top 20 -->
        <div
          v-if="activeTab === 'xp' && gamStore.rank && gamStore.rank > 20 && authStore.isAuthenticated && authStore.role !== 'admin'"
          class="mt-4 bg-violet-50 rounded-2xl p-4 border-[3px] border-violet-200 border-b-[6px] text-center">
          <span class="text-slate-500 text-sm font-bold">{{ t('myRank') }}: </span>
          <span class="font-black text-violet-700 text-lg">#{{ gamStore.rank }}</span>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/useAuthStore'
import { useGamificationStore } from '@/stores/useGamificationStore'
import { useLanguageStore } from '@/stores/useLanguageStore'
import axios from 'axios'

const authStore = useAuthStore()
const gamStore = useGamificationStore()
const langStore = useLanguageStore()
const { t } = useI18n()

const loading = ref(true)
const gradeLoading = ref(false)
const activeTab = ref('xp')
const gradeList = ref([])
const selectedGrade = ref(authStore.grade ? Number(authStore.grade) : 1)

const currentList = computed(() =>
  activeTab.value === 'xp' ? gamStore.leaderboard : gradeList.value
)
const showLoading = computed(() =>
  activeTab.value === 'xp' ? loading.value : gradeLoading.value
)

function isMe(entry) {
  return authStore.id && entry.student_id === Number(authStore.id)
}

async function loadGrade(g) {
  g = Number(g)
  if (selectedGrade.value === g && gradeList.value.length) return
  selectedGrade.value = g
  gradeLoading.value = true
  try {
    const res = await axios.get('/api/gamification/leaderboard/grade/', { params: { grade: g } })
    gradeList.value = res.data
  } catch (e) {
    console.error('LeaderboardView: failed to load grade leaderboard', e)
  } finally {
    gradeLoading.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'grade' && !gradeList.value.length) {
    loadGrade(selectedGrade.value)
  }
})

onMounted(async () => {
  await gamStore.fetchLeaderboard()
  if (authStore.id) await gamStore.fetchStats(authStore.id)
  loading.value = false
})
</script>
