<!--
================================================================================
 Component: GeneratedExamplesSurvey.vue
 Description:
        5-question post-generation survey for evaluating AI-generated examples.
        Steps through questions one at a time and emits @done with all answers.
        Emits: done({ q1_as_requested, q2_solvable_display, q3_difficulty, q4_has_errors, q5_satisfied })
================================================================================
-->

<script setup>
import { ref, computed } from 'vue'

const emit = defineEmits(['done'])

const answers = ref({
  q1_as_requested: null,
  q2_solvable_display: null,
  q3_difficulty: null,
  q4_has_errors: null,
  q5_satisfied: null,
})

const step = ref(0)  // 0–4

const questions = [
  {
    key: 'q1_as_requested',
    text: 'Boli príklady to, o čo si žiadal/a?',
    type: 'yesno',
  },
  {
    key: 'q2_solvable_display',
    text: 'Boli príklady počitateľné a zobrazili sa správne?',
    type: 'yesno',
  },
  {
    key: 'q3_difficulty',
    text: 'Ako ťažké boli príklady?',
    type: 'difficulty',
  },
  {
    key: 'q4_has_errors',
    text: 'Mali príklady v sebe chyby?',
    type: 'yesno',
  },
  {
    key: 'q5_satisfied',
    text: 'Si spokojný/á s príkladmi?',
    subtext: 'Ak áno, odošleme ich adminovi na schválenie.',
    type: 'yesno',
    isFinal: true,
  },
]

const current = computed(() => questions[step.value])

function answer(value) {
  answers.value[current.value.key] = value
  if (step.value < questions.length - 1) {
    step.value++
  } else {
    emit('done', { ...answers.value })
  }
}
</script>

<template>
  <div>
    <h2 class="text-xl font-black text-slate-800 dark:text-slate-100 mb-1">📋 Krátka anketa</h2>
    <p class="text-xs text-slate-400 dark:text-slate-500 mb-5">
      Otázka {{ step + 1 }} / {{ questions.length }}
    </p>

    <!-- Progress bar -->
    <div class="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full mb-6">
      <div
        class="h-full bg-violet-500 rounded-full transition-all duration-300"
        :style="{ width: `${((step) / questions.length) * 100}%` }"
      />
    </div>

    <!-- Question -->
    <p class="font-black text-lg text-slate-800 dark:text-slate-100 mb-1">{{ current.text }}</p>
    <p v-if="current.subtext" class="text-sm text-slate-400 dark:text-slate-500 mb-4">{{ current.subtext }}</p>
    <div v-else class="mb-4" />

    <!-- Yes / No -->
    <div v-if="current.type === 'yesno'" class="flex gap-3">
      <button
        @click="answer(true)"
        class="flex-1 py-3 rounded-2xl font-black text-sm text-white
               bg-emerald-500 border-[3px] border-emerald-600 border-b-[6px] border-b-emerald-700
               hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all"
      >
        {{ current.isFinal ? '✅ Áno, odošli adminovi' : '✅ Áno' }}
      </button>
      <button
        @click="answer(false)"
        class="flex-1 py-3 rounded-2xl font-black text-sm
               bg-slate-100 dark:bg-slate-700 border-[3px] border-slate-200 dark:border-slate-600
               text-slate-700 dark:text-slate-300
               hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all"
      >
        {{ current.isFinal ? '❌ Nie' : '❌ Nie' }}
      </button>
    </div>

    <!-- Difficulty (3 choices) -->
    <div v-else-if="current.type === 'difficulty'" class="flex gap-2">
      <button
        v-for="opt in [{ value: 'easy', label: '😌 Ľahké' }, { value: 'ok', label: '👍 Primerané' }, { value: 'hard', label: '🤯 Ťažké' }]"
        :key="opt.value"
        @click="answer(opt.value)"
        class="flex-1 py-3 rounded-2xl font-black text-sm
               bg-slate-100 dark:bg-slate-700 border-[3px] border-slate-200 dark:border-slate-600
               text-slate-700 dark:text-slate-300
               hover:bg-violet-50 dark:hover:bg-violet-900/20 hover:border-violet-300 dark:hover:border-violet-600
               hover:-translate-y-0.5 active:translate-y-1 transition-all"
      >
        {{ opt.label }}
      </button>
    </div>
  </div>
</template>
