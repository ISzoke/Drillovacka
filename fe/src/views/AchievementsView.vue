<template>
  <div class="min-h-screen bg-gradient-to-b from-violet-50 to-white p-4 md:p-8">
    <div class="max-w-3xl mx-auto">

      <!-- Header -->
      <div class="text-center mb-8">
        <div class="text-6xl mb-2">🎖️</div>
        <h1 class="text-4xl font-black text-violet-700">{{ t('achievements') }}</h1>
        <p class="text-gray-500 mt-1">
          {{ earnedCount }} / {{ allBadges.length }} {{ t('badgesCountSuffix') }}
        </p>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-16">
        <div class="text-5xl animate-spin">⏳</div>
      </div>

      <!-- Category sections -->
      <div v-else>
        <div v-for="cat in categories" :key="cat.key" class="mb-8">
          <h2 class="text-xl font-bold text-gray-700 mb-3 flex items-center gap-2">
            <span>{{ cat.icon }}</span> {{ cat.label }}
          </h2>

          <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div
              v-for="badge in badgesByCategory(cat.key)"
              :key="badge.key"
              class="rounded-2xl p-4 flex flex-col items-center text-center shadow-sm transition-all"
              :class="badge.earned
                ? 'bg-white border-2 border-violet-400 shadow-md'
                : 'bg-gray-100 border-2 border-gray-200 opacity-60'">

              <div class="text-4xl mb-2">{{ iconEmoji(badge.icon) }}</div>
              <div class="font-bold text-gray-800 text-sm leading-tight">{{ badge.name }}</div>
              <div class="text-xs text-gray-500 mt-1">{{ badge.description }}</div>
              <div class="mt-2 text-xs font-semibold" :class="badge.earned ? 'text-violet-600' : 'text-gray-400'">
                +{{ badge.xp_reward }} XP
              </div>
              <div v-if="badge.earned" class="mt-1 text-xs text-green-600 font-semibold">{{ t('earnedCheckLabel') }}</div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/useAuthStore'
import { useGamificationStore } from '@/stores/useGamificationStore'
import { useLanguageStore } from '@/stores/useLanguageStore'
import axios from 'axios'

const ICON_MAP = {
  star: '🌟', ten: '🔢', hundred: '💯', rocket: '🚀', map: '🗺️', compass: '🧭',
  target: '🎯', bolt: '⚡', bow: '🏹', grad: '🎓', muscle: '💪',
  wind: '💨', car: '🏎️', fire: '🔥', trophy: '🏆', star2: '⭐', crown: '👑', medal: '🥇',
  gem: '💎', books: '📚', calendar: '📅', mic: '🎤',
}
function iconEmoji(key) { return ICON_MAP[key] || '🏅' }

const authStore = useAuthStore()
const gamStore = useGamificationStore()
const langStore = useLanguageStore()
const { t } = useI18n()

const loading = ref(true)
const allBadges = ref([])

const categories = computed(() => [
  { key: 'activity', label: t('badgeCategoryActivity'), icon: '📚' },
  { key: 'accuracy', label: t('accuracy'), icon: '🎯' },
  { key: 'speed', label: t('badgeCategorySpeed'), icon: '⚡' },
  { key: 'voice', label: t('badgeCategoryVoice'), icon: '🎤' },
  { key: 'streak', label: t('streak'), icon: '🔥' },
  { key: 'milestone', label: t('badgeCategoryMilestone'), icon: '🏆' },
])

const earnedCount = computed(() => allBadges.value.filter(b => b.earned).length)

function badgesByCategory(cat) {
  return allBadges.value.filter(b => b.category === cat)
}

onMounted(async () => {
  const params = authStore.id ? { student_id: authStore.id } : {}
  try {
    const res = await axios.get('/api/gamification/badges/', { params })
    allBadges.value = res.data
  } catch (e) {
    console.error('AchievementsView: failed to load badges', e)
  }
  loading.value = false
})
</script>
