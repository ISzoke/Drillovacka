<script setup>
import { ref } from 'vue';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { getSessionId } from '@/utils/sessionManager';
import { dictionary } from '@/utils/dictionary';
import { sendSurveyAnswer } from '@/api/apiClient';

const langStore = useLanguageStore();
const authStore = useAuthStore();
const t = () => dictionary[langStore.language];

const feedbackText = ref('');
const submitting = ref(false);
const submitted = ref(false);

const feedbackQuestion = {
  cs: 'Máš pro nás nějaký feedback?',
  en: 'Do you have any feedback for us?',
  sk: 'Máš pre nás nejaký feedback?',
};

async function submit() {
  const trimmed = feedbackText.value.trim();
  if (!trimmed) return;
  submitting.value = true;
  try {
    const studentId = authStore.id || null;
    const sessionId = studentId ? null : getSessionId();
    await sendSurveyAnswer(
      'final-feedback-text',
      feedbackQuestion[langStore.language],
      trimmed,
      [],
      studentId,
      sessionId,
      langStore.language,
    );
    submitted.value = true;
    feedbackText.value = '';
  } catch { /* best-effort */ }
  submitting.value = false;
}
</script>

<template>
  <div class="flex justify-center px-4 py-12">
    <div class="w-full max-w-lg space-y-4">

      <!-- Contact card -->
      <div class="bg-white dark:bg-slate-800
                  rounded-3xl border-[3px] border-b-[8px]
                  border-slate-200 dark:border-slate-700
                  border-b-slate-300 dark:border-b-slate-600
                  shadow-sm p-8 flex flex-col items-center text-center">

        <div class="w-16 h-16 rounded-2xl bg-violet-100 dark:bg-violet-900/40
                    flex items-center justify-center mb-5">
          <i class="fa-solid fa-envelope text-3xl text-violet-600 dark:text-violet-400"></i>
        </div>

        <h1 class="text-3xl font-black text-slate-800 dark:text-slate-100 mb-4">
          {{ t().contactTitle }}
        </h1>

        <p class="text-slate-500 dark:text-slate-400 leading-relaxed mb-8">
          {{ t().contactDesc }}
        </p>

        <a href="mailto:martin.it2442@gmail.com"
           class="w-full flex items-center gap-4 px-5 py-4
                  rounded-2xl border-[3px] border-violet-200 dark:border-violet-800
                  bg-violet-50 dark:bg-violet-900/20
                  hover:bg-violet-100 dark:hover:bg-violet-900/40
                  transition-colors group">
          <i class="fa-solid fa-paper-plane text-xl text-violet-500 dark:text-violet-400 group-hover:translate-x-0.5 transition-transform"></i>
          <span class="font-black text-violet-700 dark:text-violet-300 text-lg">
            martin.it2442@gmail.com
          </span>
        </a>
      </div>

      <!-- Feedback card -->
      <div class="bg-white dark:bg-slate-800
                  rounded-3xl border-[3px] border-b-[8px]
                  border-slate-200 dark:border-slate-700
                  border-b-slate-300 dark:border-b-slate-600
                  shadow-sm p-8">

        <h2 class="text-xl font-black text-slate-800 dark:text-slate-100 mb-1">
          {{ t().feedbackTitle || 'Spätná väzba' }}
        </h2>
        <p class="text-slate-500 dark:text-slate-400 text-sm mb-5">
          {{ t().feedbackDesc || 'Napíš, čo sa ti páčilo alebo čo by si zmenil/a...' }}
        </p>

        <!-- Thank you state -->
        <div v-if="submitted" class="flex items-center gap-3 text-green-600 dark:text-green-400 font-semibold">
          <i class="fa-solid fa-circle-check text-2xl"></i>
          <span>{{ t().feedbackSent || 'Ďakujeme za spätnú väzbu!' }}</span>
        </div>

        <!-- Input form -->
        <template v-else>
          <textarea
            v-model="feedbackText"
            rows="4"
            :placeholder="t().feedbackPlaceholder || 'Čo sa ti páčilo? Čo by si zmenil/a alebo pridal/a?'"
            :disabled="submitting"
            class="w-full border-[3px] border-slate-200 dark:border-slate-600 rounded-2xl px-4 py-3 text-sm
                   bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100
                   placeholder-slate-400 dark:placeholder-slate-500
                   resize-none focus:outline-none focus:border-secondary dark:focus:border-secondary transition"
          />

          <button
            @click="submit"
            :disabled="submitting || !feedbackText.trim()"
            class="mt-3 w-full py-3 bg-secondary text-white font-black rounded-2xl
                   border-b-4 border-blue-700
                   hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2
                   transition-all disabled:opacity-40 disabled:translate-y-0 disabled:border-b-4">
            {{ submitting ? (t().saving || 'Odosielam...') : (t().confirm || 'Odoslať') }}
          </button>
        </template>
      </div>

    </div>
  </div>
</template>
