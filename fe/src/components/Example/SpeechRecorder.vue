<!--
================================================================================
 Component: SpeechRecorder.vue
 Description:
        Allows user to record his speech and enter answers by voice.
 Author: Dominik Horut (xhorut01)
================================================================================
-->

<script setup>
import { useRecorderStore } from "@/stores/useRecorderStore";
import SpeechVisualizer from './SpeechVisualizer.vue';
import { ref } from "vue";
import { dictionary } from "@/utils/dictionary";
import { useLanguageStore } from "@/stores/useLanguageStore";

const langStore = useLanguageStore();
const t = (key) => dictionary[langStore.language]?.[key] ?? dictionary['sk'][key];

const recorderStore = useRecorderStore();

// Bool to show confirmation dialog
const showConfirmation = ref(false);

// Start or stop voice recording
const toggleRecording = () => {

  // Check if user already agreed to record his voice
  if (!recorderStore.allowedRecording && !recorderStore.isRecording) {
    showConfirmation.value = true;
    return;
  }

  if (recorderStore.isRecording) {
    recorderStore.stopRecording();
  } else {
    recorderStore.startRecording(false);
  }
};

// Allow recording and start recording
const confirmRecording = () => {
  recorderStore.allowRecording(); 
  showConfirmation.value = false;
  recorderStore.startRecording(false);
};

const closeDialog = () => {
  showConfirmation.value = false;
};

defineExpose({
  updateExampleData: recorderStore.updateExampleData,
});
</script>

<template>
  <div class="flex flex-col md:flex-row items-center justify-center">

    <!-- Recording Button -->
    <button @click="toggleRecording"
      :class="recorderStore.isRecording ? 'bg-red-500 hover:bg-red-600 border-red-600' : 'bg-green-500 hover:bg-green-600 border-green-600'"
      class="w-24 h-24 flex items-center justify-center rounded-full border-4 text-white text-2xl focus:outline-none transition hover:scale-110 shadow-md z-10"
      :title="recorderStore.isRecording ? 'Stop Recording' : 'Start Recording'">
      <i :class="recorderStore.isRecording ? 'fas fa-stop' : 'fas fa-microphone'" class="text-4xl"></i>
    </button>

    <!-- Speech visualizers -->
    <div class="mt-4 md:mt-0 md:ml-6 absolute md:relative z-0 flex gap-4 items-center">
      <!-- Horizontal visualizer (symmetric) -->
      <SpeechVisualizer
        :barColor="recorderStore.isRecording ? '#457b9d' : '#f1faee'" :width="300" :height="100" :barWidth="10"
        :barGap="8" :barCount="10" />
    </div>

    <!-- Agreement dialog that user agrees that his voice will be recorded -->
    <div v-if="showConfirmation" class="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-40">
      <div class="bg-white dark:bg-slate-800 p-6 md:p-12 rounded-3xl shadow-xl w-11/12 md:w-2/3 lg:w-1/2 text-center border-[3px] border-slate-200 dark:border-slate-700 border-b-[8px] border-b-slate-300 dark:border-b-slate-600">

        <p class="text-base md:text-lg font-semibold mb-6 md:mb-16 text-slate-700 dark:text-slate-200">
          {{ t('micConsentText') }}
        </p>

        <div class="flex flex-col md:flex-row justify-center gap-3">
          <button @click="confirmRecording"
            class="text-xl px-6 py-2 font-black text-white bg-emerald-500 border-[3px] border-emerald-600 border-b-[6px] border-b-emerald-700 rounded-2xl hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all">
            {{ t('micConsentAgree') }}
          </button>
          <button @click="closeDialog"
            class="text-xl px-6 py-2 font-black text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 border-[3px] border-slate-300 dark:border-slate-500 border-b-[6px] border-b-slate-400 dark:border-b-slate-600 rounded-2xl hover:-translate-y-0.5 active:translate-y-1 active:border-b-[3px] transition-all">
            {{ t('micConsentDisagree') }}
          </button>
        </div>

      </div>
    </div>
  </div>
</template>
