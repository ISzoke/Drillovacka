<!--
================================================================================
 Component: ProfileView.vue
 Description:
        When logged in: shows student profile (level, XP, rank, badges).
        When logged out: shows login / signup form.
================================================================================
-->

<script setup>
import { useI18n } from 'vue-i18n';
import Signup from '@/components/Profile/Signup.vue'
import Login from '@/components/Profile/Login.vue'
import { useAuthStore } from '@/stores/useAuthStore'
import { useGamificationStore } from '@/stores/useGamificationStore'
import { useLanguageStore } from '@/stores/useLanguageStore'
import { RouterLink } from 'vue-router'
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { updateStudentGrade } from '@/api/apiClient'
import { useDarkStore } from '@/stores/useDarkStore'

const authStore = useAuthStore()
const gamStore = useGamificationStore()
const langStore = useLanguageStore()
const { t } = useI18n()
const darkStore = useDarkStore()
const route = useRoute()
const showLogin = ref(route.query.register !== '1')

const ICON_MAP = {
  star: '🌟', ten: '🔢', hundred: '💯', rocket: '🚀', map: '🗺️', compass: '🧭',
  target: '🎯', bolt: '⚡', bow: '🏹', grad: '🎓', muscle: '💪',
  wind: '💨', car: '🏎️', fire: '🔥', trophy: '🏆', star2: '⭐', crown: '👑', medal: '🥇',
  gem: '💎', books: '📚', calendar: '📅', mic: '🎤',
}
function iconEmoji(key) { return ICON_MAP[key] || '🏅' }

const CATEGORY_COLORS = {
  activity:  { card: 'bg-violet-500',  border: 'border-violet-700' },
  accuracy:  { card: 'bg-emerald-500', border: 'border-emerald-700' },
  speed:     { card: 'bg-sky-500',     border: 'border-sky-700' },
  streak:    { card: 'bg-orange-500',  border: 'border-orange-700' },
  milestone: { card: 'bg-amber-500',   border: 'border-amber-700' },
  voice:     { card: 'bg-teal-500',    border: 'border-teal-700' },
}
const FALLBACK_COLORS = ['bg-violet-500', 'bg-emerald-500', 'bg-sky-500', 'bg-orange-500', 'bg-amber-500']
function badgeColor(badge, idx) {
  return CATEGORY_COLORS[badge.category] || { card: FALLBACK_COLORS[idx % FALLBACK_COLORS.length], border: 'border-black/30' }
}

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
    gradeChangeError.value = typeof e === 'string' ? e : t('errorSettingGrade')
  }
  gradeChanging.value = false
}

const allBadges = ref([])
const loadingBadges = ref(false)

const earnedBadges = computed(() => allBadges.value.filter(b => b.earned))
const unearnedBadges = computed(() => allBadges.value.filter(b => !b.earned))

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
  <!-- Logged in: student profile -->
  <div v-if="authStore.isAuthenticated && authStore.role !== 'admin'" class="min-h-screen bg-slate-50 dark:bg-slate-900 p-4 md:p-8">
    <div class="max-w-2xl mx-auto space-y-5">

      <!-- ── Profile card ── -->
      <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] p-6 sm:p-8 relative overflow-hidden">
        <!-- Decorative blur -->
        <div class="absolute -top-10 -right-10 w-40 h-40 bg-violet-100 rounded-full blur-3xl opacity-50 pointer-events-none" />

        <div class="flex flex-col sm:flex-row items-center sm:items-start gap-6 relative z-10">
          <!-- Avatar -->
          <div class="relative flex-shrink-0">
            <div class="w-28 h-28 rounded-3xl bg-violet-100 flex items-center justify-center
                        border-4 border-violet-200 shadow-inner">
              <div class="w-20 h-20 rounded-2xl bg-violet-500 flex items-center justify-center
                          text-white text-5xl font-black shadow-sm select-none">
                {{ (authStore.name || '?')[0].toUpperCase() }}
              </div>
            </div>
            <div class="absolute -bottom-3 -right-3 bg-emerald-500 text-white px-3 py-1.5 rounded-xl
                        text-sm font-black border-4 border-white shadow-sm rotate-[-6deg]">
              Lvl {{ gamStore.level }}
            </div>
          </div>

          <!-- User info -->
          <div class="flex-1 text-center sm:text-left">
            <h2 class="text-3xl font-black text-slate-800 dark:text-slate-100 mb-2">{{ authStore.name }}</h2>
            <p class="text-slate-500 dark:text-slate-400 font-bold mb-4 bg-slate-100 dark:bg-slate-700 inline-block px-3 py-1 rounded-xl">
              {{ authStore.grade ? t('gradeFullLabel', { grade: authStore.grade }) : t('noGrade') }}
            </p>

            <div class="flex flex-wrap justify-center sm:justify-start gap-2">
              <div class="bg-amber-100 dark:bg-amber-900/40 border-2 border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 px-4 py-2 rounded-2xl flex items-center gap-2 font-black shadow-sm">
                ⭐ {{ gamStore.xp }} XP
              </div>
              <div class="bg-blue-100 dark:bg-blue-900/40 border-2 border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300 px-4 py-2 rounded-2xl flex items-center gap-2 font-black shadow-sm">
                <span v-if="gamStore.rank"># {{ gamStore.rank }}</span>
                <span v-else>–</span>
              </div>
              <div class="bg-orange-100 dark:bg-orange-900/40 border-2 border-orange-300 dark:border-orange-700 text-orange-700 dark:text-orange-300 px-4 py-2 rounded-2xl flex items-center gap-2 font-black shadow-sm">
                🔥 {{ gamStore.streak }} {{ t('streakDaySuffix') }}
              </div>
            </div>
          </div>
        </div>

        <!-- XP bar -->
        <div class="mt-8 bg-slate-50 dark:bg-slate-700/50 p-4 rounded-3xl border-2 border-slate-100 dark:border-slate-600">
          <div class="flex justify-between items-center mb-3">
            <span class="text-sm font-black text-slate-500 uppercase tracking-wider">
              {{ t('pathToLevelLabel', { level: gamStore.level + 1 }) }}
            </span>
            <span class="text-sm font-black text-violet-600">
              {{ gamStore.xp - gamStore.levelXpStart }} / {{ gamStore.levelXpEnd - gamStore.levelXpStart }} XP
            </span>
          </div>
          <div class="h-5 bg-slate-200 dark:bg-slate-600 rounded-full overflow-hidden shadow-inner border border-slate-300 dark:border-slate-500">
            <div
              class="h-full bg-violet-500 rounded-full relative transition-all duration-700"
              :style="{ width: gamStore.levelPercent() + '%' }">
              <div class="absolute top-1 left-2 right-2 h-2 bg-white/20 rounded-full"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Grade card ── -->
      <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] p-6 sm:p-8">
        <h3 class="text-2xl font-black text-slate-800 dark:text-slate-100 mb-2">{{ t('myGradeHeading') }}</h3>
        <p class="text-slate-500 font-medium mb-6">{{ t('adjustDifficultyText') }}</p>

        <div v-if="!authStore.grade_change_used">
          <div class="grid grid-cols-5 sm:grid-cols-9 gap-2 sm:gap-3 mb-6">
            <button
              v-for="g in 9"
              :key="g"
              @click="selectedGrade = selectedGrade === g ? null : g"
              class="aspect-square rounded-2xl font-black text-xl transition-all"
              :class="selectedGrade === g
                ? 'bg-blue-500 text-white border-b-[4px] border-blue-700 translate-y-1 shadow-sm'
                : (authStore.grade === g
                    ? 'bg-violet-100 dark:bg-violet-900/50 text-violet-700 dark:text-violet-300 border-b-[4px] border-violet-300 dark:border-violet-700'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border-b-[4px] border-slate-300 dark:border-slate-600 hover:bg-slate-200 dark:hover:bg-slate-600 active:border-b-0 active:translate-y-1')">
              {{ g }}
            </button>
          </div>

          <button
            :disabled="!selectedGrade || gradeChanging"
            @click="saveGrade"
            class="w-full py-4 rounded-2xl font-black text-lg transition-all"
            :class="selectedGrade && !gradeChanging
              ? 'bg-emerald-500 hover:bg-emerald-400 text-white border-b-[6px] border-emerald-700 active:border-b-0 active:translate-y-[6px]'
              : 'bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500 border-b-[4px] border-slate-200 dark:border-slate-600 cursor-not-allowed'">
            {{ gradeChanging ? t('saving') : (authStore.grade ? t('changeGradeButtonCaps') : t('setGradeButtonCaps')) }}
          </button>

          <p v-if="gradeChangeError" class="text-red-500 text-sm mt-3 font-semibold">{{ gradeChangeError }}</p>
          <p v-if="authStore.grade" class="text-xs text-amber-600 dark:text-amber-400 mt-3 font-semibold bg-amber-50 dark:bg-amber-900/30 p-3 rounded-xl border border-amber-200 dark:border-amber-800">
            {{ t('gradeChangeOnceWarning') }}
          </p>
        </div>

        <div v-else class="bg-slate-50 dark:bg-slate-700/50 p-4 rounded-2xl border-2 border-slate-200 dark:border-slate-600 text-slate-500 dark:text-slate-400 font-semibold text-sm">
          {{ t('gradeAlreadyChangedText') }}
        </div>
      </div>

      <!-- ── Dark mode toggle ── -->
      <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] p-6 sm:p-8">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-2xl font-black text-slate-800 dark:text-slate-100">{{ darkStore.isDark ? t('darkModeOnLabel') : t('lightModeOnLabel') }}</h3>
            <p class="text-slate-500 dark:text-slate-400 font-medium text-sm mt-1">{{ t('toggleAppearanceText') }}</p>
          </div>
          <button
            @click="darkStore.toggle()"
            class="relative w-16 h-9 rounded-full border-[3px] border-b-[5px] transition-all duration-300 focus:outline-none flex-shrink-0"
            :class="darkStore.isDark
              ? 'bg-violet-600 border-violet-700 border-b-violet-800'
              : 'bg-slate-200 border-slate-300 border-b-slate-400'">
            <span
              class="absolute top-0.5 w-6 h-6 rounded-full bg-white shadow transition-all duration-300"
              :class="darkStore.isDark ? 'left-7' : 'left-0.5'">
            </span>
          </button>
        </div>
      </div>

      <!-- ── Badges ── -->
      <div class="bg-white dark:bg-slate-800 rounded-3xl border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] p-6 sm:p-8">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-2xl font-black text-slate-800 dark:text-slate-100">{{ t('yourBadgesHeading') }}</h3>
          <span class="bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 font-black px-4 py-1.5 rounded-xl border-2 border-amber-200 dark:border-amber-700">
            {{ earnedBadges.length }} / {{ allBadges.length }}
          </span>
        </div>

        <div v-if="loadingBadges" class="text-center py-8 text-slate-400">
          <i class="fa-solid fa-spinner fa-spin text-3xl"></i>
        </div>

        <div v-else>
          <!-- Earned badges -->
          <div v-if="earnedBadges.length > 0" class="mb-8">
            <h4 class="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">{{ t('earnedSectionLabel') }}</h4>
            <div class="grid sm:grid-cols-2 gap-4">
              <div
                v-for="(badge, idx) in earnedBadges"
                :key="badge.key"
                class="rounded-2xl p-5 text-white border-b-[6px] hover:-translate-y-1 transition-transform"
                :class="[badgeColor(badge, idx).card, badgeColor(badge, idx).border]">
                <div class="flex items-start gap-4">
                  <div class="bg-white/20 p-2.5 rounded-xl text-3xl leading-none flex-shrink-0">
                    {{ iconEmoji(badge.icon) }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <h5 class="font-black text-xl mb-1">{{ badge.name }}</h5>
                    <p class="text-sm font-medium opacity-90 mb-3 leading-tight">{{ badge.description }}</p>
                    <span class="inline-block bg-black/20 px-3 py-1 rounded-full text-xs font-black">
                      +{{ badge.xp_reward }} XP
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="text-center py-8 text-slate-400 mb-4">
            <p class="text-lg font-bold mb-1">{{ t('noBadgesYet') }}.</p>
            <p class="text-sm">{{ t('firstBadgeEncouragement') }}</p>
          </div>

          <!-- Locked badges -->
          <div v-if="unearnedBadges.length > 0">
            <h4 class="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">
              {{ t('lockedBadgesHeading', { n: unearnedBadges.length }) }}
            </h4>
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div
                v-for="badge in unearnedBadges"
                :key="badge.key"
                class="bg-slate-100 dark:bg-slate-700/50 border-2 border-slate-200 dark:border-slate-600 border-dashed rounded-2xl p-4
                       grayscale opacity-60 hover:grayscale-0 hover:opacity-100 transition-all duration-300">
                <div class="flex flex-col items-center text-center gap-2">
                  <div class="w-12 h-12 rounded-xl bg-slate-200 dark:bg-slate-600 flex items-center justify-center text-2xl">
                    {{ iconEmoji(badge.icon) }}
                  </div>
                  <div>
                    <h5 class="font-black text-slate-700 dark:text-slate-200 text-sm mb-1">{{ badge.name }}</h5>
                    <p class="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2 leading-tight">{{ badge.description }}</p>
                    <span class="inline-block bg-slate-200 dark:bg-slate-600 px-2 py-1 rounded-lg text-xs font-black text-slate-600 dark:text-slate-300">
                      +{{ badge.xp_reward }} XP
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- Logged out: login / signup -->
  <div v-else class="pt-12">
    <Login v-if="showLogin" />
    <Signup v-else />

    <button @click="showLogin = !showLogin" class="underline w-full text-slate-500 text-lg mt-4">
      {{ showLogin ? t('registerText') : t('loginText') }}
    </button>

    <RouterLink to="/admin" class="underline w-full text-slate-400 text-lg mt-12 flex justify-center">
      {{ t('adminText') }}
    </RouterLink>
  </div>
</template>
