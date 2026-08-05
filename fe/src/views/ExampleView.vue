<!--
================================================================================
 Component: ProfileView.vue
 Description:
        Displays practicing view for selected topics, handles logic for displaying examples
        and user answers evaluation results.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { useI18n } from 'vue-i18n';
import Example from '@/components/Example.vue';
import ProgressBar from '@/components/Example/ProgressBar.vue';
import GeneratedExamplesSurvey from '@/components/GeneratedExamplesSurvey.vue';
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue';
import { useRoute } from 'vue-router';
import { getExamples, getTaskExamples, submitGeneratedBatchSurvey, getMyGeneratedBatches } from '@/api/apiClient';
import correctIcon from '@/assets/img/correct.png';
import wrongIcon from '@/assets/img/wrong.png'
import correctSoundSrc from '@/assets/audio/correct.mp3';
import wrongSoundSrc from '@/assets/audio/wrong.mp3';
import Spinner from '@/components/Spinner.vue';
import Summary from '@/components/Example/Summary.vue';
import { useRecorderStore } from '@/stores/useRecorderStore';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useGamificationStore } from '@/stores/useGamificationStore';
import { useAuthStore } from '@/stores/useAuthStore';
const examples = ref([]);
const practiceSessionKey = ref(crypto.randomUUID());

// Instance of the <Example> component
const exampleComponent = ref(null); 

// Index of the current example 
const curr_index = ref(0); 

const topics = ref([]);
const isCorrect = ref(false);
const showIcon = ref(false);
const images = ref({});
const loading = ref(true);

// Example was skipped
const isSkipped = ref(false);     

// Count of mistakes made in current example
const mistakes = ref(0);

// Count of examples which user skipped
const skipped = ref(0);

// Count of examples where user made 0, 1, 2 or 3 mistakes 
const noMistakes = ref(0);
const oneMistake = ref(0);
const twoMistakes = ref(0);
const threeMistakes = ref(0);

// Bools to determine what will be displayed next
const showSummary = ref(false);
const showAnswer = ref(false);

// Stores
const recorderStore = useRecorderStore();
const langStore = useLanguageStore();
const { t } = useI18n();
const gamStore = useGamificationStore();
const authStore = useAuthStore();
const route = useRoute();

// ── AI-generated batch survey (shown before Summary when batch_id in URL) ─────
const batchId = route.query.batch_id ? Number(route.query.batch_id) : null
const batchSurveyDone = ref(false)
const showBatchSurvey = computed(() => showSummary.value && !!batchId && !batchSurveyDone.value)

async function onBatchSurveyDone(answers) {
  try {
    await submitGeneratedBatchSurvey(batchId, { student_id: authStore.id, ...answers })
  } catch { /* best-effort */ }
  batchSurveyDone.value = true
}

// Fire streak — 3 fast correct answers in a row
const fireActive = ref(false)
let fastCorrectStreak = 0
let lastCorrectTime = 0
let fireTimer = null

function trackFastCorrect() {
  const now = Date.now()
  if (lastCorrectTime && (now - lastCorrectTime) < 6000) {
    fastCorrectStreak++
  } else {
    fastCorrectStreak = 1
  }
  lastCorrectTime = now
  if (fastCorrectStreak >= 3) {
    fireActive.value = true
    clearTimeout(fireTimer)
    fireTimer = setTimeout(() => { fireActive.value = false }, 4000)
  }
}

function resetFireStreak() {
  fastCorrectStreak = 0
  lastCorrectTime = 0
}

// XP toast
const xpToast = ref(null)
let xpToastTimer = null

function showXpToast(data) {
  if (!data || data.xp_awarded === undefined) return
  xpToast.value = data
  clearTimeout(xpToastTimer)
  xpToastTimer = setTimeout(() => { xpToast.value = null }, 2200)
}

function xpMultiplierLabel(comparison) {
  if (comparison === 'higher') return t('xpHigherGradeBonusLabel')
  if (comparison === 'lower')  return t('xpLowerGradePenaltyLabel')
  return null
}

// SFX when user answers correctly or incorrectly
const correctSound = new Audio(correctSoundSrc);
const wrongSound = new Audio(wrongSoundSrc);

// Determine how many exampless user practiced in session
const storedExamplesCounted = sessionStorage.getItem("examplesCounted");
const examplesCounted = ref(storedExamplesCounted ? parseInt(storedExamplesCounted, 10) : 0);

// Preload correct and wrong answer icons
const preloadMedia = () => {
  const correct = new Image();
  const wrong = new Image();

  correct.src = correctIcon;
  wrong.src = wrongIcon;

  images.value.correct = correct;
  images.value.wrong = wrong;
};

// Depending on how many mistakes user made in example add one to the corresponding counter
const evaluateMistakes = () => {

  if(isSkipped.value){
    skipped.value++;
  }else if(mistakes.value === 0){
    noMistakes.value++;
  }else if(mistakes.value === 1){
    oneMistake.value++;
  }else if(mistakes.value === 2){
    twoMistakes.value++;
  }else if(mistakes.value === 3){
    threeMistakes.value++;
    mistakes.value = 0;
    isSkipped.value = false;
    return true;
  }

  mistakes.value = 0;
  isSkipped.value = false;
  return false;
};

// Determine what to display depending on users answer
const displayNext = async (data) => {
  
  if (curr_index.value >= 0 && curr_index.value < examples.value.length) {
    
    // User skipped the example
    if (data.skipped) {
      isSkipped.value = true;
    
    // User answered correctly
    } else if (data.isCorrect) {
      correctSound.play();
      displayIcon(true);
      trackFastCorrect();
      if (authStore.id) showXpToast({ xp_awarded: gamStore.lastXpAwarded, xp_breakdown: gamStore.xpBreakdown });

    // User answered incorrectly for 3 times
    } else if (!data.isCorrect && data.nextExample) {
      wrongSound.play();
      displayIcon(false);
      exampleComponent.value.triggerShake();
      mistakes.value++;
      resetFireStreak();

    // User answered incorrectly once or twice
    } else {
      wrongSound.play();
      displayIcon(false);
      exampleComponent.value.triggerShake();
      mistakes.value++;
      resetFireStreak();
      exampleComponent.value.getStep(mistakes.value)
      return;
    }

    showAnswer.value = evaluateMistakes();

    // User made 3 mistakes in example - correct answer will be displayed
    if(showAnswer.value){
      exampleComponent.value.displayAnswer();

      setTimeout(() => {
        curr_index.value++;
        if (curr_index.value === examples.value.length) {
          recorderStore.stopRecording();  
          recorderStore.student_answer = '';
          showSummary.value = true;
        }
      }, 1500);
    
    // Display next example
    }else{
      curr_index.value++;
    }
    
    // Update counted examples
    examplesCounted.value++;
    sessionStorage.setItem("examplesCounted", examplesCounted.value.toString());

    await nextTick();

    // All examples were practiced
    if (curr_index.value === examples.value.length) {
      recorderStore.stopRecording();  
      recorderStore.student_answer = '';
      showSummary.value = true;
    }
    
  }else {
    console.error("index is out of bounds:", curr_index.value);
  }
};

// Fetch examples based on selected topics
const fetchExamples = async (topics) => {
  try {
    examples.value = await getExamples(topics);

  } catch (error) {
    console.error("Failed to fetch examples:", error);

  } finally {

    loading.value = false;
  }
};

// Display correct or incorrect icon
const displayIcon = async (correct) => {

  isCorrect.value = correct;
  await nextTick();

  const icon = correct
    ? images.value.correct.src
    : images.value.wrong.src;

  showIcon.value = true;

  setTimeout(() => {
    showIcon.value = false;
  }, 600);
};

// Display summary after practice ended
const displaySummary = () => {
  recorderStore.stopRecording();
  recorderStore.student_answer = '';
  showSummary.value = true;
};

onMounted(async () => {
  preloadMedia();

  // If this is a generated batch, check its status before starting —
  // skip survey if student already rated it
  if (batchId && authStore.id) {
    try {
      const batches = await getMyGeneratedBatches({ student_id: authStore.id })
      const batch = batches.find(b => b.id === batchId)
      if (batch && batch.status !== 'preview') {
        batchSurveyDone.value = true
      }
    } catch { /* non-critical */ }
  }

  if (route.query.task_id) {
      topics.value = [];
      fetchTaskExamples(Number(route.query.task_id));
      return;
  }

  if (route.query.topics) {
      topics.value = JSON.parse(route.query.topics);
      fetchExamples(topics.value);
  }
});

const fetchTaskExamples = async (taskId) => {
  try {
    examples.value = await getTaskExamples(taskId);
  } catch (error) {
    console.error("Failed to fetch task examples:", error);
  } finally {
    loading.value = false;
  }
};

onUnmounted(() => {
  clearTimeout(fireTimer);
  clearTimeout(xpToastTimer);
  recorderStore.stopRecording();
});

</script>

<template>
  
    <Spinner v-if="loading" class="pt-48"/>

    <!-- Fallback if no examples were fetched -->
    <div v-if="examples.length === 0 && !loading" class="flex flex-col justify-center items-center">
      <h1 class="text-xl md:text-3xl font-bold text-center pt-20 text-slate-700 dark:text-slate-200 mb-8">{{ t('noExamplesForCombinationText') }}</h1>

      <RouterLink to="/"
                class="text-center text-xl md:text-2xl font-black text-white bg-violet-500 border-[3px] border-violet-600 border-b-[8px] border-b-violet-700 rounded-2xl px-6 py-3 hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all">
                {{ t('backtoMainMenu') }}
      </RouterLink>
    </div>

    <!-- Generated batch banner -->
    <div v-if="batchId && examples.length > curr_index && !showSummary"
         class="max-w-xl mx-auto px-4 pt-3">
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-700 text-xs text-violet-600 dark:text-violet-400 font-semibold">
        {{ t('aiGeneratedBatchBannerText') }}
      </div>
    </div>

    <!-- Progress bar -->
    <div v-if="examples.length > curr_index && !showSummary" class="flex-col items-center justify-center">
      <ProgressBar :totalExamples="examples.length" :finishedExamples="curr_index"></ProgressBar>
    </div>

    <!-- Fire animation — 3 fast correct answers in a row -->
    <Transition name="fire-bg">
      <div v-if="fireActive && !showSummary" class="fixed inset-0 pointer-events-none z-5 fire-overlay" />
    </Transition>

    <!-- Red screen overlay — intensifies with each wrong attempt -->
    <div
      v-if="!showSummary && mistakes > 0"
      class="fixed inset-0 bg-red-500 pointer-events-none z-10 transition-all duration-500"
      :style="{ opacity: mistakes * 0.07 }"
    />

    <div class="flex items-center justify-center">

      <!-- Example component -->
      <Example ref="exampleComponent" v-if="examples.length > curr_index && !showSummary" :example="examples[curr_index]" :topics="topics" :practiceSessionKey="practiceSessionKey" @answerSent="displayNext" @skipped="displayNext" @finished="displaySummary" :key="curr_index"></Example>

      <!-- Correct or incorrect icon -->
      <Transition name="answer-flash">
        <img
          v-if="showIcon && examples.length > curr_index"
          :src="isCorrect ? images.correct.src : images.wrong.src"
          class="w-28 h-28 md:w-48 md:h-48 absolute top-40 md:top-64 z-50 pointer-events-none"
        >
      </Transition>

      <!-- AI-generated batch survey — shown before Summary when batch_id is in URL -->
      <div v-if="showBatchSurvey" class="w-full max-w-lg mx-auto px-4 py-8">
        <div class="mb-6 text-center">
          <p class="text-xs text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wide mb-1">{{ t('generatedExamplesRatingLabel') }}</p>
          <h2 class="text-2xl font-black text-slate-800 dark:text-slate-100">{{ t('howDidYouLikeExamplesQuestion') }}</h2>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">{{ t('fiveQuickQuestionsText') }}</p>
        </div>
        <GeneratedExamplesSurvey @done="onBatchSurveyDone" />
      </div>

      <!-- Practice summary-->
      <Summary v-if="showSummary && !showBatchSurvey" :skipped="skipped" :noMistakes="noMistakes" :oneMistake="oneMistake" :twoMistakes="twoMistakes" :threeMistakes="threeMistakes" :topics="topics" :taskId="route.query.task_id ? Number(route.query.task_id) : null" :practiceSessionKey="practiceSessionKey"></Summary>

    </div>

    <!-- XP breakdown toast -->
    <Transition name="xp-toast">
      <div
        v-if="xpToast && authStore.id"
        class="fixed top-20 md:top-24 left-1/2 -translate-x-1/2 z-50 pointer-events-none select-none"
      >
        <div class="flex flex-col items-center bg-violet-600 text-white rounded-2xl shadow-xl px-5 py-3 min-w-[160px]">
          <span class="text-2xl font-black tracking-tight">+{{ xpToast.xp_awarded }} XP</span>
          <div v-if="xpToast.xp_breakdown" class="text-xs text-violet-200 mt-1 text-center space-y-0.5">
            <div v-if="xpMultiplierLabel(xpToast.xp_breakdown.grade_comparison)">
              {{ xpMultiplierLabel(xpToast.xp_breakdown.grade_comparison) }}
            </div>
            <div v-if="xpToast.xp_breakdown.voice_bonus > 0">🎤 +{{ xpToast.xp_breakdown.voice_bonus }} {{ t('voiceBonusSuffix') }}</div>
          </div>
        </div>
      </div>
    </Transition>

</template>

<style scoped>
.xp-toast-enter-active { animation: xpPop 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.xp-toast-leave-active { animation: xpFade 0.3s ease-in forwards; }
@keyframes xpPop  { from { opacity:0; transform: translateX(-50%) scale(0.5) translateY(20px); } to { opacity:1; transform: translateX(-50%) scale(1) translateY(0); } }
@keyframes xpFade { to   { opacity:0; transform: translateX(-50%) translateY(-20px); } }

.answer-flash-enter-active {
  animation: answerPop 0.35s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.answer-flash-leave-active {
  animation: answerFade 0.2s ease-in forwards;
}

@keyframes answerPop {
  0%   { opacity: 0; transform: scale(0.3); }
  60%  { transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

@keyframes answerFade {
  to { opacity: 0; transform: scale(1.3); }
}

/* Fire overlay */
.fire-overlay {
  background: linear-gradient(
    to top,
    rgba(255, 80, 0, 0.25) 0%,
    rgba(255, 160, 0, 0.12) 30%,
    rgba(255, 200, 0, 0.05) 60%,
    transparent 100%
  );
  animation: fireFlicker 0.8s ease-in-out infinite alternate;
}

@keyframes fireFlicker {
  from { opacity: 0.7; }
  to   { opacity: 1; }
}

.fire-bg-enter-active { animation: fireIn 0.4s ease-out; }
.fire-bg-leave-active { animation: fireOut 0.6s ease-in forwards; }
@keyframes fireIn  { from { opacity: 0; } to { opacity: 1; } }
@keyframes fireOut { to   { opacity: 0; } }
</style>
