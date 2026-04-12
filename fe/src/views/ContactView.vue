<script setup>
import { ref } from 'vue';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { dictionary } from '@/utils/dictionary';
import Survey from '@/components/Example/Survey.vue';

const langStore = useLanguageStore();
const t = () => dictionary[langStore.language];

const TOTAL_QUESTIONS = 9;

const showSurvey = ref(false);
const surveyDone = ref(false);
const answered = ref(0);

const openSurvey = () => {
  sessionStorage.removeItem('surveyIndex');
  answered.value = 0;
  surveyDone.value = false;
  showSurvey.value = true;
};

const onHideSurvey = () => {
  answered.value++;
  if (answered.value >= TOTAL_QUESTIONS) {
    showSurvey.value = false;
    surveyDone.value = true;
  }
};
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

      <!-- Survey card -->
      <div class="bg-white dark:bg-slate-800
                  rounded-3xl border-[3px] border-b-[8px]
                  border-slate-200 dark:border-slate-700
                  border-b-slate-300 dark:border-b-slate-600
                  shadow-sm p-8 flex flex-col items-center text-center">

        <div class="w-16 h-16 rounded-2xl bg-sky-100 dark:bg-sky-900/40
                    flex items-center justify-center mb-5">
          <i class="fa-solid fa-clipboard-list text-3xl text-sky-600 dark:text-sky-400"></i>
        </div>

        <h2 class="text-2xl font-black text-slate-800 dark:text-slate-100 mb-2">
          {{ t().surveyTitle || 'Anketa' }}
        </h2>
        <p class="text-slate-500 dark:text-slate-400 text-sm leading-relaxed mb-6">
          {{ t().surveyDesc || 'Pomôž nám zlepšiť aplikáciu — vyplnenie je dobrovoľné a trvá pár minút.' }}
        </p>

        <!-- Thank you -->
        <div v-if="surveyDone"
             class="flex flex-col items-center gap-3 text-green-600 dark:text-green-400">
          <i class="fa-solid fa-circle-check text-4xl"></i>
          <p class="font-bold text-lg">{{ t().surveyThanks || 'Ďakujeme za spätnú väzbu!' }}</p>
        </div>

        <!-- Open button -->
        <button v-else-if="!showSurvey" @click="openSurvey"
                class="px-8 py-3 bg-secondary text-white font-bold rounded-2xl
                       border-b-4 border-blue-700
                       hover:-translate-y-0.5 active:translate-y-0.5 active:border-b-2
                       transition-all text-lg">
          {{ t().startSurvey || 'Vyplniť anketu' }}
        </button>

        <!-- Progress while open -->
        <p v-if="showSurvey" class="text-xs text-slate-400 dark:text-slate-500 mb-4">
          {{ answered + 1 }} / {{ TOTAL_QUESTIONS }}
        </p>
      </div>

      <!-- Survey questions (rendered below cards) -->
      <div v-if="showSurvey"
           class="bg-white dark:bg-slate-800
                  rounded-3xl border-[3px] border-b-[8px]
                  border-slate-200 dark:border-slate-700
                  border-b-slate-300 dark:border-b-slate-600
                  shadow-sm overflow-hidden">
        <Survey :topics="[]" @hideSurvey="onHideSurvey" />
      </div>

    </div>
  </div>
</template>
