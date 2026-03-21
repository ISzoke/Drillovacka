<!--
================================================================================
 Component: LevelUpToast.vue
 Description:
        Non-blocking toast when the student reaches a new level.
        Plays a short chime via Web Audio API.
================================================================================
-->

<script setup>
import { watch, ref, onUnmounted } from 'vue'
import { useGamificationStore } from '@/stores/useGamificationStore'

const gamStore = useGamificationStore()
const visible = ref(false)
const newLevel = ref(0)
let hideTimer = null

function playChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const notes = [523.25, 659.25, 783.99, 1046.50] // C5 E5 G5 C6
    const lastEnd = notes.length * 0.12 + 0.5
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0.15, ctx.currentTime + i * 0.12)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.12 + 0.5)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(ctx.currentTime + i * 0.12)
      osc.stop(ctx.currentTime + i * 0.12 + 0.5)
    })
    setTimeout(() => ctx.close(), lastEnd * 1000 + 100)
  } catch (_) {}
}

watch(
  () => gamStore.leveledUp,
  (val) => {
    if (!val) return
    newLevel.value = gamStore.level
    visible.value = true
    playChime()
    clearTimeout(hideTimer)
    hideTimer = setTimeout(() => {
      visible.value = false
      gamStore.leveledUp = false
    }, 3500)
  }
)

onUnmounted(() => clearTimeout(hideTimer))
</script>

<template>
  <Transition name="level-up">
    <div
      v-if="visible"
      class="fixed top-6 left-1/2 -translate-x-1/2 z-[9998] pointer-events-none select-none"
    >
      <div class="flex items-center gap-3 bg-primary text-white
                  rounded-2xl shadow-2xl px-6 py-3 border-2 border-tertiary">
        <span class="text-4xl">🎉</span>
        <div>
          <p class="text-xs font-bold uppercase tracking-widest text-tertiary leading-none mb-0.5">Level Up!</p>
          <p class="font-black text-xl leading-tight">Level {{ newLevel }}</p>
        </div>
        <span class="text-3xl">⭐</span>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.level-up-enter-active { animation: levelPop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.level-up-leave-active { animation: levelFade 0.3s ease-in forwards; }

@keyframes levelPop {
  from { opacity: 0; transform: translateX(-50%) scale(0.4) translateY(30px); }
  to   { opacity: 1; transform: translateX(-50%) scale(1) translateY(0); }
}
@keyframes levelFade {
  to { opacity: 0; transform: translateX(-50%) translateY(-20px); }
}
</style>
