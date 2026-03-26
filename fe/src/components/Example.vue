<!--
================================================================================
 Component: Example.vue
 Description:
        Displays interface for practicing example including input fields, timer
        and speech recorder, sends user answers to the server to be evaluated.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { ref, onMounted, onUnmounted, defineEmits, defineExpose, computed, watch, nextTick } from 'vue';
import InlineInput from '@/components/Input Fields/InlineInput.vue';
import FractionInput from './Input Fields/FractionInput.vue';
import VariableInput from './Input Fields/VariableInput.vue';
import Timer from '@/components/Example/Timer.vue';
import SpeechRecorder from '@/components/Example/SpeechRecorder.vue';
import Answer from '@/components/Example/Answer.vue';
import Tips from '@/components/Example/Tips.vue';
import { createRecord, skipExample, deleteRecord, checkAnswer, sendExampleReport } from '@/api/apiClient';
import { useAuthStore } from '@/stores/useAuthStore';
import { useRecorderStore } from '@/stores/useRecorderStore';
import { useLanguageStore } from '@/stores/useLanguageStore';
import { useGamificationStore } from '@/stores/useGamificationStore';
import { dictionary } from '@/utils/dictionary';
import { getSessionId } from '@/utils/sessionManager';

const props = defineProps({
  example: {
    type: Object,
  },
  answer: {
    type: String,
  },
  topics: {
    type: Array,
    default: () => []
  }
});

const emits = defineEmits(['answerSent', 'skipped', 'finished']);

// Rendered latex form of example text
const renderedExample = computed(() => `\\(${props.example.example}\\)`);

// Input values
const inlineInput = ref(null);
const fractionInput = ref(null);
const variableInput = ref(null);

// Component instances
const timer = ref(null);
const speechRecorder = ref(null);
const step = ref('');
const showReportForm = ref(false);
const shaking = ref(false);
const reportType = ref('wrong_answer');
const reportNote = ref('');
const reportSubmitting = ref(false);
const reportSubmitted = ref(false);
const reportError = ref('');

// Stores
const authStore = useAuthStore();
const recorderStore = useRecorderStore();
const langStore = useLanguageStore();
const gamStore = useGamificationStore();

// Record that user practiced example data
const student_id = authStore.id || 0;
const session_id = student_id === 0 ? getSessionId() : null;
console.log('[DEBUG Example.vue] student_id:', student_id, 'session_id:', session_id);
const record_date = ref('');


let isWordProblem = ref(false);
const showAnswer = ref(false);

const reportOptions = computed(() => ([
  { value: 'wrong_answer', label: dictionary[langStore.language].reportWrongAnswer },
  { value: 'wrong_grade', label: dictionary[langStore.language].reportWrongGrade },
  { value: 'unclear', label: dictionary[langStore.language].reportUnclear },
  { value: 'other', label: dictionary[langStore.language].reportOther },
]));

const triggerShake = () => {
  shaking.value = true;
  setTimeout(() => { shaking.value = false; }, 500);
};

// Sends answer to be evaluated for inline answers and emits evaluation result
const checkInline = async (answer) => {

  const result = await checkAnswer(student_id, props.example.id, record_date.value, timer.value.getTime(), answer, "inline");
  if (result.xp_awarded !== undefined) gamStore.handleXPUpdate(result);
  emits('answerSent', { isCorrect: result.isCorrect, nextExample: result.continue_with_next });

  if (!result.isCorrect) {
    triggerShake();
    clearInput();
  }
};

// Sends answer to be evaluated for fraction answers and emits evaluation result
const checkFraction = async (numerator, denominator) => {

  const answer = [numerator, denominator];
  const result = await checkAnswer(student_id, props.example.id, record_date.value, timer.value.getTime(), answer, "fraction");
  if (result.xp_awarded !== undefined) gamStore.handleXPUpdate(result);
  emits('answerSent', { isCorrect: result.isCorrect, nextExample: result.continue_with_next });

  if (!result.isCorrect) {
    triggerShake();
    clearInput();
  }
}

// Sends answer to be evaluated for variable answers and emits evaluation result
const checkVariables = async (variables) => {

  const answers = variables.map(variable => variable.answer);
  const result = await checkAnswer(student_id, props.example.id, record_date.value, timer.value.getTime(), answers, "variable");
  if (result.xp_awarded !== undefined) gamStore.handleXPUpdate(result);
  emits('answerSent', { isCorrect: result.isCorrect, nextExample: result.continue_with_next });

  if (!result.isCorrect) {
    triggerShake();
    clearInput();
  }
}

// Record that user practiced example creation
const initRecord = async () => {
  const result = await createRecord(student_id, props.example.id, props.topics);
  record_date.value = result.date;
  if (speechRecorder.value) {
    speechRecorder.value.updateExampleData(student_id, props.example.id, props.example.input_type, record_date.value, session_id);
  }
}

// Skip current example
const skip = () => {
  skipExample(student_id, props.example.id, record_date.value);
  emits('skipped', { skipped: true });
}

// Finish practicing
const finish = () => {
  deleteRecord(student_id, props.example.id, record_date.value);
  emits('finished');
}

const toggleReportForm = () => {
  showReportForm.value = !showReportForm.value;
};

const submitReport = async () => {
  if (reportSubmitting.value || reportSubmitted.value) {
    return;
  }

  reportSubmitting.value = true;
  try {
    await sendExampleReport({
      student_id,
      session_id,
      example_id: props.example.id,
      report_type: reportType.value,
      note: reportNote.value.trim(),
      language: langStore.language,
    });
    reportSubmitted.value = true;
    showReportForm.value = true;
    reportError.value = '';
    reportNote.value = '';
  } catch (error) {
    reportError.value = error || dictionary[langStore.language].somethingWentWrong;
  } finally {
    reportSubmitting.value = false;
  }
};

// Watch changes in example text to re-render latex
watch(
  () => props.example,
  () => {
    renderMathJax();
    isWordProblem = props.example.input_type == 'WORD';
    showReportForm.value = false;
    reportType.value = 'wrong_answer';
    reportNote.value = '';
    reportSubmitting.value = false;
    reportSubmitted.value = false;
    reportError.value = '';
  },
  { immediate: true }
);

// Render latex form of example text
function renderMathJax() {
  if (window.MathJax) {
    window.MathJax.typesetPromise()
  }
}

// Handle Enter key and send answer
const handleEnter = (event) => {
  if (event.key === 'Enter' && !showAnswer.value) {
    getAnswer();
  }

};

// Get answer from currently used input field
const getAnswer = () => {

  if (inlineInput.value != null) {
    inlineInput.value.getAnswer();

  } else if (variableInput.value != null) {
    variableInput.value.getAnswer();

  } else if (fractionInput.value != null) {
    fractionInput.value.getAnswer();
  }
}

// Clear currently used input field
const clearInput = () => {

  if (inlineInput.value != null) {
    inlineInput.value.clearInput();

  } else if (variableInput.value != null) {
    variableInput.value.clearInput();

  } else if (fractionInput.value != null) {
    fractionInput.value.clearInput();
  }
}

// Set up event listeners to handle Enter key and render latex
onMounted(() => {
  initRecord()
  window.addEventListener('keydown', handleEnter);
  renderMathJax();
  timer.value.startTimer();

  recorderStore.setEmitFunction(emits);

});

// Clean up event listener for Enter key 
onUnmounted(() => {
  window.removeEventListener('keydown', handleEnter);
});

// Get example step text depending on number of mistakes
const getStep = (mistakes) => {
  if (props.example && props.example.steps) {
    step.value = props.example.steps[mistakes - 1]?.text ?? step.value;
  }
  return null;
};

// Display correct answer to user
const displayAnswer = () => {
  showAnswer.value = true;
  nextTick(() => {
    setTimeout(() => {

      showAnswer.value = false;
    }, 1500);
  });
}

defineExpose({ getStep, displayAnswer, triggerShake });
</script>

<template>

  <div class="w-full flex flex-col items-center justify-center">

    <div class="absolute top-20 md:top-24 md:right-4 md:left-auto md:w-auto w-full z-0">

      <!-- Timer and terminate practice button -->
      <div class="flex justify-between items-center md:block md:w-auto">

        <Timer ref="timer" class="md:mb-4" />

        <div @click="finish" class="text-center text-lg md:text-xl font-black mr-2 md:mr-0 text-white
         bg-red-500 border-[3px] border-red-600 border-b-[6px] border-b-red-700
         p-2 md:p-3 rounded-2xl cursor-pointer transition-all
         hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px]"
          :class="showAnswer ? 'pointer-events-none' : ''">
          {{ dictionary[langStore.language].quit.toUpperCase() }}
        </div>

      </div>

    </div>

    <div class="flex items-center justify-center mt-10 md:mt-20">
      <div class="flex flex-col dark:bg-slate-800 dark:rounded-3xl dark:px-10 dark:py-8">

        <div :class="[
          isWordProblem ? 'text-xl md:text-3xl flex flex-col items-center' : 'text-4xl md:text-7xl flex flex-col',
          props.example.input_type == 'FRAC' ? 'text-5xl' : 'text-4xl']">

          <!-- Latex example text or plain text for word problem -->
          <div class="flex items-center justify-center" :class="isWordProblem ? 'w-full md:w-2/3' : 'w-full'">
            {{ isWordProblem ? example.example : renderedExample }}
          </div>

          <!-- Input components -->
          <div class="flex flex-col md:flex-row mt-10 items-center justify-center gap-6 md:gap-10">

            <div class="flex justify-start items-center" :class="{ 'shake-wrong': shaking }">

              <!-- Equal sign for inline and fraction examples -->
              <p v-if="props.example.input_type == 'INLINE' || props.example.input_type == 'FRAC'" class="mr-2">=</p>

              <VariableInput v-if="props.example.input_type == 'VAR'" ref="variableInput" :answer="props.answer"
                @answerSent="checkVariables">
              </VariableInput>

              <FractionInput v-else-if="props.example.input_type == 'FRAC'" ref="fractionInput"
                @answerSent="checkFraction">
              </FractionInput>

              <InlineInput v-else-if="props.example.input_type == 'INLINE'" ref="inlineInput" 
                @answerSent="checkInline">
              </InlineInput>

              <InlineInput v-else-if="props.example.input_type == 'WORD'" ref="inlineInput" 
                @answerSent="checkInline">
              </InlineInput>

            </div>

            <!-- Speech recorder to enter answers by voice -->
            <SpeechRecorder ref="speechRecorder" class="mt-6 md:ml-8 md:mt-0"
              :class="showAnswer ? 'pointer-events-none' : ''">
            </SpeechRecorder>

          </div>

          <!-- Example hint -->
          <div v-if="step" class="mt-8">
            <p class="text-xl md:text-4xl text-center text-slate-500 dark:text-slate-400">{{ dictionary[langStore.language].hint }}: <span class="font-semibold text-slate-800 dark:text-slate-100">{{ step }}</span></p>
          </div>

        </div>

      </div>

    </div>

    <div class="flex flex-col items-center justify-center w-full">
      <div class="flex items-center justify-around  w-full md:w-1/3 ">

        <!-- Placeholder used for centering -->
        <Tips class="invisible" />

        <!-- Button to send answer to be evaluated -->
        <div @click="getAnswer" class="text-center text-2xl md:text-4xl font-black text-white
             bg-emerald-500 border-[3px] border-emerald-600 border-b-[8px] border-b-emerald-700
             px-6 py-4 md:p-5 rounded-3xl cursor-pointer my-6 transition-all
             hover:-translate-y-1 active:translate-y-1 active:border-b-[3px]"
          :class="showAnswer ? 'pointer-events-none' : ''">
          {{ dictionary[langStore.language].done.toUpperCase() }}
        </div>

        <!-- Tips how to enter answers by voice -->
        <Tips :class="{
          'invisible': langStore.language === 'en',
          'pointer-events-none': showAnswer
        }" />
      </div>

      <!-- Skip example button -->
      <div @click="skip" class="text-center text-lg md:text-2xl font-black text-slate-600 dark:text-slate-300
           bg-slate-100 dark:bg-slate-700 border-[3px] border-slate-300 dark:border-slate-500 border-b-[6px] border-b-slate-400 dark:border-b-slate-600
           px-6 md:px-8 py-2 rounded-2xl cursor-pointer transition-all
           hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px]"
        :class="showAnswer ? 'pointer-events-none' : ''">
        {{ dictionary[langStore.language].skip.toUpperCase() }}
      </div>

      <div class="mt-4 w-full max-w-md px-4 flex flex-col items-center">
        <button
          @click="toggleReportForm"
          class="w-full text-center text-lg font-bold text-amber-800 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 border-2 border-amber-300 dark:border-amber-700 px-5 py-2 rounded-2xl transition hover:bg-amber-100 dark:hover:bg-amber-900/40"
          :class="showAnswer ? 'pointer-events-none opacity-60' : ''"
        >
          {{ dictionary[langStore.language].reportExample }}
        </button>

        <div v-if="showReportForm" class="mt-4 w-full bg-white dark:bg-slate-800 border-2 border-amber-200 dark:border-slate-700 rounded-2xl shadow-md p-4 text-left">
          <div class="mb-3">
            <label class="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
              {{ dictionary[langStore.language].reportReason }}
            </label>
            <select
              v-model="reportType"
              class="w-full border border-slate-300 dark:border-slate-600 rounded-xl px-3 py-2 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100"
              :disabled="reportSubmitting || reportSubmitted"
            >
              <option v-for="option in reportOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>

          <div class="mb-3">
            <label class="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
              {{ dictionary[langStore.language].reportNote }}
            </label>
            <textarea
              v-model="reportNote"
              rows="3"
              class="w-full border border-slate-300 dark:border-slate-600 rounded-xl px-3 py-2 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500"
              :placeholder="dictionary[langStore.language].reportPlaceholder"
              :disabled="reportSubmitting || reportSubmitted"
            />
          </div>

          <div class="flex items-center justify-between gap-4">
            <button
              @click="submitReport"
              class="text-white bg-amber-500 hover:bg-amber-600 border-2 border-amber-600 rounded-xl px-4 py-2 font-semibold transition disabled:bg-gray-400 disabled:border-gray-400"
              :disabled="reportSubmitting || reportSubmitted"
            >
              {{ reportSubmitting ? dictionary[langStore.language].saving : dictionary[langStore.language].reportSubmit }}
            </button>

            <p v-if="reportSubmitted" class="text-sm font-semibold text-green-700">
              {{ dictionary[langStore.language].reportSent }}
            </p>
          </div>

          <p v-if="reportError" class="mt-3 text-sm font-semibold text-red-600">
            {{ reportError }}
          </p>
        </div>
      </div>

    </div>

  </div>

  <!-- Correct answer -->
  <Answer v-if="showAnswer" class="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50"
    :answer="props.example.answers[0].answer">
  </Answer>

</template>

<style scoped>
@keyframes shakeWrong {
  0%, 100% { transform: translateX(0); }
  15%       { transform: translateX(-10px) rotate(-2deg); }
  30%       { transform: translateX(10px) rotate(2deg); }
  45%       { transform: translateX(-8px); }
  60%       { transform: translateX(8px); }
  75%       { transform: translateX(-4px); }
  90%       { transform: translateX(4px); }
}

.shake-wrong {
  animation: shakeWrong 0.5s ease-in-out;
}
</style>
