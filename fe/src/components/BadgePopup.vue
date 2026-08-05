<!--
================================================================================
 Component: BadgePopup.vue
 Description:
        Corner toast that appears when a new badge is earned. Does not block
        the page — positioned bottom-right, queues multiple badges.
================================================================================
-->

<script setup>
import { watch, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGamificationStore } from '@/stores/useGamificationStore'

const gamStore = useGamificationStore()
const { t } = useI18n()

const ICON_MAP = {
  star: '🌟', ten: '🔢', hundred: '💯', rocket: '🚀', map: '🗺️', compass: '🧭',
  target: '🎯', bolt: '⚡', bow: '🏹', grad: '🎓', muscle: '💪',
  wind: '💨', car: '🏎️', fire: '🔥', trophy: '🏆', star2: '⭐', crown: '👑', medal: '🥇',
  gem: '💎', books: '📚', calendar: '📅', mic: '🎤',
}

const BADGE_META = {
  first_correct:        { nameKey: 'badgeFirstCorrect',        icon: 'star',     xp: 15  },
  ten_correct:          { nameKey: 'badgeTenCorrect',          icon: 'ten',      xp: 30  },
  hundred_correct:      { nameKey: 'badgeHundredCorrect',      icon: 'hundred',  xp: 80  },
  three_hundred_correct:{ nameKey: 'badgeThreeHundredCorrect', icon: 'rocket',   xp: 180 },
  five_hundred_correct: { nameKey: 'badgeFiveHundredCorrect',  icon: 'crown',    xp: 300 },
  thousand_correct:     { nameKey: 'badgeThousandCorrect',     icon: 'gem',      xp: 600 },
  five_skills:          { nameKey: 'badgeFiveSkills',          icon: 'map',      xp: 35  },
  ten_skills:           { nameKey: 'badgeTenSkills',           icon: 'compass',  xp: 70  },
  twenty_skills:        { nameKey: 'badgeTwentySkills',        icon: 'books',    xp: 150 },
  comeback:             { nameKey: 'badgeComeback',            icon: 'muscle',   xp: 25  },
  ten_in_a_row:         { nameKey: 'badgeTenInARow',           icon: 'bolt',     xp: 45  },
  twenty_five_in_a_row: { nameKey: 'badgeTwentyFiveInARow',    icon: 'bow',      xp: 100 },
  perfect_session:      { nameKey: 'badgePerfectSession',      icon: 'target',   xp: 55  },
  accuracy_master:      { nameKey: 'badgeAccuracyMaster',      icon: 'grad',     xp: 90  },
  accuracy_legend:      { nameKey: 'badgeAccuracyLegend',      icon: 'medal',    xp: 200 },
  mastery_skill:        { nameKey: 'badgeMasterySkill',        icon: 'star2',    xp: 80  },
  fast_answer:          { nameKey: 'badgeFastAnswer',          icon: 'wind',     xp: 35  },
  lightning:            { nameKey: 'badgeLightning',           icon: 'car',      xp: 65  },
  speed_demon:          { nameKey: 'badgeSpeedDemon',          icon: 'bolt',     xp: 130 },
  speed_session:        { nameKey: 'badgeSpeedSession',        icon: 'wind',     xp: 50  },
  streak_3:             { nameKey: 'badgeStreak3',             icon: 'fire',     xp: 20  },
  streak_7:             { nameKey: 'badgeStreak7',             icon: 'fire',     xp: 55  },
  streak_14:            { nameKey: 'badgeStreak14',            icon: 'calendar', xp: 120 },
  streak_30:            { nameKey: 'badgeStreak30',            icon: 'trophy',   xp: 280 },
  level_5:              { nameKey: 'badgeLevel5',              icon: 'star2',    xp: 40  },
  level_10:             { nameKey: 'badgeLevel10',             icon: 'crown',    xp: 120 },
  level_20:             { nameKey: 'badgeLevel20',             icon: 'gem',      xp: 300 },
  voice_first:          { nameKey: 'badgeVoiceFirst',          icon: 'mic',      xp: 15  },
  voice_10:             { nameKey: 'badgeVoice10',             icon: 'mic',      xp: 35  },
  voice_50:             { nameKey: 'badgeVoice50',             icon: 'mic',      xp: 90  },
  voice_100:            { nameKey: 'badgeVoice100',            icon: 'mic',      xp: 200 },
  voice_250:            { nameKey: 'badgeVoice250',            icon: 'mic',      xp: 450 },
  top10_leaderboard:    { nameKey: 'badgeTop10Leaderboard',    icon: 'medal',    xp: 70  },
  top3_leaderboard:     { nameKey: 'badgeTop3Leaderboard',     icon: 'trophy',   xp: 160 },
}

const queue = ref([])
const current = ref(null)
const visible = ref(false)
let timer = null

function showNext() {
  if (queue.value.length === 0) {
    current.value = null
    visible.value = false
    return
  }
  current.value = queue.value.shift()
  visible.value = true
  timer = setTimeout(() => {
    visible.value = false
    setTimeout(showNext, 350)
  }, 3500)
}

watch(
  () => gamStore.recentBadges,
  (keys) => {
    if (!keys || keys.length === 0) return
    for (const key of keys) {
      const meta = BADGE_META[key]
      if (meta) queue.value.push({ key, name: t(meta.nameKey), icon: meta.icon, xp: meta.xp })
    }
    if (!visible.value) showNext()
  },
  { deep: true }
)

function dismiss() {
  clearTimeout(timer)
  visible.value = false
  setTimeout(showNext, 300)
}
</script>

<template>
  <Transition name="badge-slide">
    <div
      v-if="visible && current"
      class="fixed bottom-6 right-4 z-[9999] max-w-[280px] w-full cursor-pointer select-none"
      @click="dismiss"
    >
      <div class="flex items-center gap-3 bg-secondary text-white
                  rounded-2xl shadow-2xl px-4 py-3 border-2 border-tertiary">
        <div class="text-4xl shrink-0 badge-icon">{{ ICON_MAP[current.icon] || '🏅' }}</div>
        <div class="min-w-0">
          <p class="text-[10px] font-bold uppercase tracking-widest text-tertiary leading-none mb-0.5">{{ t('newBadge') }}!</p>
          <p class="font-extrabold text-sm leading-tight truncate">{{ current.name }}</p>
          <p class="text-xs text-tertiary mt-0.5">+{{ current.xp }} {{ t('xp') }}</p>
        </div>
        <span class="text-yellow-300 text-xl shrink-0">🎉</span>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.badge-slide-enter-active {
  animation: slideInRight 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.badge-slide-leave-active {
  animation: slideOutRight 0.3s ease-in forwards;
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(110%); }
  to   { opacity: 1; transform: translateX(0); }
}

@keyframes slideOutRight {
  from { opacity: 1; transform: translateX(0); }
  to   { opacity: 0; transform: translateX(110%); }
}

.badge-icon {
  animation: iconBob 0.8s ease-in-out infinite alternate;
}

@keyframes iconBob {
  from { transform: scale(1) rotate(-5deg); }
  to   { transform: scale(1.15) rotate(5deg); }
}
</style>
