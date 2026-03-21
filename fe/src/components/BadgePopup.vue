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
import { useGamificationStore } from '@/stores/useGamificationStore'

const gamStore = useGamificationStore()

const ICON_MAP = {
  star: '🌟', ten: '🔢', hundred: '💯', rocket: '🚀', map: '🗺️', compass: '🧭',
  target: '🎯', bolt: '⚡', bow: '🏹', grad: '🎓', muscle: '💪',
  wind: '💨', car: '🏎️', fire: '🔥', trophy: '🏆', star2: '⭐', crown: '👑', medal: '🥇',
  gem: '💎', books: '📚', calendar: '📅',
}

const BADGE_META = {
  first_correct:        { name: 'Prvý gól',         icon: 'star',     xp: 15  },
  ten_correct:          { name: 'Rozbehnutý',        icon: 'ten',      xp: 30  },
  hundred_correct:      { name: 'Stovkár',           icon: 'hundred',  xp: 80  },
  three_hundred_correct:{ name: 'Výpočtový stroj',   icon: 'rocket',   xp: 180 },
  five_hundred_correct: { name: 'Päťstovkár',        icon: 'crown',    xp: 300 },
  thousand_correct:     { name: 'Tisícnik',           icon: 'gem',      xp: 600 },
  five_skills:          { name: 'Zvedavec',           icon: 'map',      xp: 35  },
  ten_skills:           { name: 'Všestranný',         icon: 'compass',  xp: 70  },
  twenty_skills:        { name: 'Encyklopédia',       icon: 'books',    xp: 150 },
  comeback:             { name: 'Tvrdohlavý',         icon: 'muscle',   xp: 25  },
  ten_in_a_row:         { name: 'Bez zakopnutia',     icon: 'bolt',     xp: 45  },
  twenty_five_in_a_row: { name: 'Neomylný',           icon: 'bow',      xp: 100 },
  perfect_session:      { name: 'Čistý štít',         icon: 'target',   xp: 55  },
  accuracy_master:      { name: 'Ostreľovač',         icon: 'grad',     xp: 90  },
  accuracy_legend:      { name: 'Snajper',            icon: 'medal',    xp: 200 },
  mastery_skill:        { name: 'Zvládnuté!',         icon: 'star2',    xp: 80  },
  fast_answer:          { name: 'Rýchlik',            icon: 'wind',     xp: 35  },
  lightning:            { name: 'Bleskovka',          icon: 'car',      xp: 65  },
  speed_demon:          { name: 'Šíp',                icon: 'bolt',     xp: 130 },
  speed_session:        { name: 'Na plné obrátky',    icon: 'wind',     xp: 50  },
  streak_3:             { name: 'Tri dni v rade',     icon: 'fire',     xp: 20  },
  streak_7:             { name: 'Celý týždeň',        icon: 'fire',     xp: 55  },
  streak_14:            { name: 'Dvojtýždenník',      icon: 'calendar', xp: 120 },
  streak_30:            { name: 'Mesiac v rade',      icon: 'trophy',   xp: 280 },
  level_5:              { name: 'Level 5',            icon: 'star2',    xp: 40  },
  level_10:             { name: 'Dvojciferný',        icon: 'crown',    xp: 120 },
  level_20:             { name: 'Veterán',            icon: 'gem',      xp: 300 },
  top10_leaderboard:    { name: 'Top 10',             icon: 'medal',    xp: 70  },
  top3_leaderboard:     { name: 'Stupne víťazov',     icon: 'trophy',   xp: 160 },
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
      if (meta) queue.value.push({ key, ...meta })
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
      <div class="flex items-center gap-3 bg-gradient-to-r from-violet-600 to-indigo-600 text-white
                  rounded-2xl shadow-2xl px-4 py-3 ring-2 ring-yellow-300">
        <div class="text-4xl shrink-0 badge-icon">{{ ICON_MAP[current.icon] || '🏅' }}</div>
        <div class="min-w-0">
          <p class="text-[10px] font-bold uppercase tracking-widest text-violet-200 leading-none mb-0.5">Nový odznak!</p>
          <p class="font-extrabold text-sm leading-tight truncate">{{ current.name }}</p>
          <p class="text-xs text-violet-200 mt-0.5">+{{ current.xp }} XP</p>
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
